"""Cooperative single-host action locks. Never evidence that a remote POST failed."""
from contextlib import contextmanager
from pathlib import Path
import errno
import os
import stat
import threading
import time
try:
    import fcntl
except ImportError:  # Persistent execution fails closed on unsupported platforms.
    fcntl = None
from .common import VerdugoError, digest, identifier

SCHEMA = '''
CREATE TABLE IF NOT EXISTS run_guards (
 tenant TEXT NOT NULL, key TEXT NOT NULL, scheme TEXT NOT NULL,
 scope TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(tenant,key));
'''
SCHEME = 'local-flock-v1'


class GuardBusy(VerdugoError):
    pass


class StateGuards:
    def __init__(self, state):
        self.path = None if str(state) == ':memory:' else Path(state).resolve()
        self.memory = {}
        if self.path is None:
            self.scope = 'memory-only'
            self.root = None
        else:
            info = self.path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise VerdugoError('State must be a regular single-link local file')
            self.scope = digest([str(self.path), info.st_dev, info.st_ino])
            self.root = self.path.with_name(self.path.name + '.locks')

    @property
    def scheme(self):
        return SCHEME if self.path is not None else 'memory-only'

    def record(self, engine, key):
        engine.db.execute('INSERT INTO run_guards VALUES(?,?,?,?,?)',
                          (engine.tenant, key, self.scheme, self.scope, time.time()))

    def require_record(self, engine, key):
        row = engine.db.execute('SELECT scheme,scope FROM run_guards WHERE tenant=? AND key=?',
                                (engine.tenant, key)).fetchone()
        if self.path is None or not row or row['scheme'] != SCHEME or row['scope'] != self.scope:
            raise VerdugoError('No compatible persistent execution guard; legacy/restored runs need offline review')

    @contextmanager
    def hold(self, tenant, key):
        identifier(tenant); identifier(key)
        if self.path is None:
            lock = self.memory.setdefault((tenant, key), threading.Lock())
            if not lock.acquire(blocking=False): raise GuardBusy('Action is active in this process')
            try: yield
            finally: lock.release()
            return
        if fcntl is None: raise VerdugoError('Persistent execution requires local POSIX flock support')
        # Locks are never unlinked: deleting a held lock file could create two owners.
        self.root.mkdir(mode=0o700, exist_ok=True)
        root_info = self.root.lstat()
        if (self.root.is_symlink() or not self.root.is_dir()
                or root_info.st_uid != os.getuid() or root_info.st_mode & 0o077):
            raise VerdugoError('Invalid local lock directory')
        filename = self.root / (digest([tenant, key]) + '.lock')
        flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW
        fd = os.open(filename, flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise VerdugoError('Invalid action lock file')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    raise GuardBusy('Action lock held by a cooperating process') from exc
                raise
            try: yield
            finally: fcntl.flock(fd, fcntl.LOCK_UN)
        finally: os.close(fd)
