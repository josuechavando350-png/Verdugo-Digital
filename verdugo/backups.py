"""Consistent local SQLite snapshots with private permissions; no cloud upload.

The snapshots are NOT encrypted and do NOT certify safe restore of in-flight
external actions. Restore is intentionally offline/manual.
"""
import hashlib
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from .common import VerdugoError


def _private_dir(path):
    p = Path(path).resolve()
    info = p.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise VerdugoError('Backups require an owner-only directory')
    return p


def _inspect(path):
    path = Path(path)
    if path.is_symlink(): raise VerdugoError('Backup path must not be a symlink')
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
            info.st_mode & 0o077 or info.st_nlink != 1):
        raise VerdugoError('Backup must be a private regular single-link file')
    _private_dir(path.parent)
    return path.resolve()


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while block := f.read(65536): h.update(block)
    return h.hexdigest()


def verify(path):
    path = _inspect(path)
    try:
        uri = path.as_uri() + '?mode=ro&immutable=1'
        with closing(sqlite3.connect(uri, uri=True)) as db:
            ok = db.execute('PRAGMA integrity_check').fetchone()
            tables = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if ok != ('ok',) or not {'plans','runs','records','commercial_events','jobs','run_guards'} <= tables:
                raise VerdugoError('Invalid or incomplete Verdugo backup')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise VerdugoError('Backup contains foreign key violations')
    except sqlite3.DatabaseError as exc:
        raise VerdugoError('Invalid SQLite backup') from exc
    return {'state': 'verified_local_copy', 'sha256': _digest(path), 'bytes': path.stat().st_size,
            'encrypted': False, 'bank_reconciled': False,
            'restoration_tested': False, 'remote_execution_resumed': False}


def create(engine, destination):
    if engine.role != 'operator': raise VerdugoError('Operator role required to create backup')
    if engine.state_path == ':memory:': raise VerdugoError('Persistent SQLite state required')
    if not isinstance(destination, str) or not destination:
        raise VerdugoError('Explicit backup destination required')
    dst = Path(destination)
    if not dst.name.endswith('.sqlite3') or not dst.name or len(dst.name) > 160:
        raise VerdugoError('Explicit .sqlite3 destination required')
    directory = _private_dir(dst.parent)
    dst = directory / dst.name
    if dst == Path(engine.state_path).resolve(): raise VerdugoError('Cannot overwrite live state')
    if dst.exists() or dst.is_symlink(): raise VerdugoError('Backup destination already exists')
    if engine.db.in_transaction:
        raise VerdugoError('Cannot snapshot inside an open application transaction')
    fd, tmpname = tempfile.mkstemp(prefix='.verdugo-snapshot-', suffix='.sqlite3', dir=directory)
    os.close(fd)
    tmp = Path(tmpname)
    try:
        with closing(sqlite3.connect(tmp)) as target:
            engine.db.backup(target, pages=100, sleep=0.05)
        os.chmod(tmp, 0o600)
        report = verify(tmp)
        # Exclusive hard-link fails atomically if another creator used the target.
        os.link(tmp, dst, follow_symlinks=False)
        return report | {'state': 'created_and_verified_local_copy',
                         'saved_filename': dst.name,
                         'contains_personal_data': True, 'encryption_required_before_remote_storage': True}
    except FileExistsError as exc:
        raise VerdugoError('Backup destination was created concurrently') from exc
    finally:
        tmp.unlink(missing_ok=True)
