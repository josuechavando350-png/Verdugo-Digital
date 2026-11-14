"""Optional administrator-selected Ragas and analytics venvs; never supplied in a tool payload.

Dependency isolation is not a hostile-code sandbox. The operator must trust the
interpreter, its venv, this checkout and all installed packages.
"""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile

from .common import VerdugoError
from . import local_analytics

PROBE = Path(__file__).with_name('_runtime_probe.py')
PROFILE_ENV = {'ragas': 'VERDUGO_RAGAS_PYTHON'}
# v0.17: the analytics recipes share one separate administrator environment.
PROFILE_ENV.update({service: 'VERDUGO_ANALYTICS_PYTHON' for service in local_analytics.SPECS})


def interpreter(service):
    key = PROFILE_ENV.get(service)
    value = os.environ.get(key) if key else None
    if value is None:
        return sys.executable
    if (not value or '\x00' in value or '\n' in value or not Path(value).is_absolute()
            or '..' in Path(value).parts
            or not re.fullmatch(r'python(?:3(?:\.\d+)?)?', Path(value).name)):
        raise VerdugoError('The administrator runtime profile requires an absolute Python executable')
    try:
        info = Path(value).stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.getuid())
                or info.st_mode & 0o022 or not os.access(value, os.X_OK)):
            raise VerdugoError('Unsafe administrator runtime executable')
        config = Path(value).parent.parent / 'pyvenv.cfg'
        ci = config.stat()
        if (not stat.S_ISREG(ci.st_mode) or ci.st_uid not in (0, os.getuid())
                or ci.st_mode & 0o022 or ci.st_size > 16384):
            raise VerdugoError('Unsafe or missing administrator venv configuration')
    except OSError as exc:
        raise VerdugoError('Administrator runtime profile is unavailable') from exc
    return value


def binding(service):
    path = interpreter(service)
    h = hashlib.sha256(path.encode())
    if path != sys.executable:
        p = Path(path)
        with p.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        h.update((p.parent.parent / 'pyvenv.cfg').read_bytes())
    return h.hexdigest()


def versions(service, distributions):
    path = interpreter(service)
    if path == sys.executable:
        result = {}
        for dist in distributions:
            try:
                result[dist] = metadata.version(dist)
            except metadata.PackageNotFoundError:
                result[dist] = None
        return result
    if (not 1 <= len(distributions) <= 10 or any(
            not isinstance(d, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', d)
            for d in distributions)):
        raise VerdugoError('Invalid runtime metadata request')
    with tempfile.TemporaryDirectory(prefix='verdugo-profile-') as work:
        env = {'PATH': os.defpath, 'HOME': work, 'TMPDIR': work, 'LANG': 'C.UTF-8'}
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            proc = subprocess.Popen([path, '-I', str(PROBE), *distributions],
                stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                cwd=work, env=env, start_new_session=True, close_fds=True)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired as exc:
                raise VerdugoError('Runtime metadata probe timed out') from exc
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            out.seek(0)
            raw = out.read(8193)
            if proc.returncode or len(raw) > 8192:
                raise VerdugoError('Runtime metadata probe failed')
    try:
        result = json.loads(raw)
        if (not isinstance(result, dict) or set(result) != set(distributions)
                or any(v is not None and (not isinstance(v, str) or len(v) > 100)
                       for v in result.values())):
            raise ValueError('Invalid metadata')
    except (ValueError, UnicodeError) as exc:
        raise VerdugoError('Invalid runtime metadata response') from exc
    return result
