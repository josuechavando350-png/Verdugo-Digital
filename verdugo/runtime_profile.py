"""Optional administrator-selected Ragas venv; never supplied in a tool payload.

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

PROBE = Path(__file__).with_name('_runtime_probe.py')
PROFILE_ENV = {'ragas': 'VERDUGO_RAGAS_PYTHON'}
PROFILE_ENV['semantic-kernel'] = 'VERDUGO_KERNEL666_PYTHON'
PROFILE_ENV['playwright-python'] = 'VERDUGO_BROWSERSTATE666_PYTHON'
PROFILE_ENV['monty'] = 'VERDUGO_MONTY666_PYTHON'
PROFILE_ENV['hatchet'] = 'VERDUGO_HATCHET666_PYTHON'
PROFILE_ENV['invariant'] = 'VERDUGO_INVARIANT666_PYTHON'
PROFILE_ENV['pyrit'] = 'VERDUGO_PYRIT666_PYTHON'
PROFILE_ENV['transformerlens'] = 'VERDUGO_LENS666_PYTHON'
PROFILE_ENV['interpret'] = 'VERDUGO_INTERPRET666_PYTHON'
PROFILE_ENV['granite-guardian'] = 'VERDUGO_GUARDIAN666_PYTHON'
PROFILE_ENV['llama-cpp'] = 'VERDUGO_GUARDIAN666_PYTHON'
PROFILE_ENV['agno'] = 'VERDUGO_AGNO666_PYTHON'
PROFILE_ENV['ag2'] = 'VERDUGO_AG2666_PYTHON'
PROFILE_ENV['langroid'] = 'VERDUGO_LANGROID666_PYTHON'
PROFILE_ENV['griptape'] = 'VERDUGO_GRIPTAPE666_PYTHON'
PROFILE_ENV['beeai-framework'] = 'VERDUGO_BEE666_PYTHON'
PROFILE_ENV['harness-sdk'] = 'VERDUGO_STRANDS666_PYTHON'
PROFILE_ENV['unified-planning'] = 'VERDUGO_PLANNING666_PYTHON'
from .local_analytics import SPECS as ANALYTICS
PROFILE_ENV.update({sid: 'VERDUGO_ANALYTICS_PYTHON' for sid in ANALYTICS})
from .local_research import SPECS as RESEARCH, LANGUAGE, PROTOCOL
PROFILE_ENV.update({sid: ('VERDUGO_LANGUAGE_PYTHON' if sid in LANGUAGE else
                         'VERDUGO_PROTOCOL_PYTHON' if sid in PROTOCOL else 'VERDUGO_RESEARCH_PYTHON')
                    for sid in RESEARCH})
from .local_interop import PROFILES
PROFILE_ENV.update({sid: 'VERDUGO_'+profile+'_PYTHON' for sid, profile in PROFILES.items()})
from .local_knowledge import PROFILES as KNOWLEDGE_PROFILES
PROFILE_ENV.update({sid: 'VERDUGO_'+profile+'_PYTHON' for sid, profile in KNOWLEDGE_PROFILES.items()})

from .local_content import PROFILES as CONTENT_PROFILES
PROFILE_ENV.update({sid: 'VERDUGO_'+profile+'_PYTHON' for sid,profile in CONTENT_PROFILES.items()})

from .local_pycli import SPECS as PYCLI
PROFILE_ENV.update({sid:'VERDUGO_PYCLI021_PYTHON' for sid in PYCLI})

from .local_planning import PROFILES as PLANNING
PROFILE_ENV.update({sid:'VERDUGO_'+profile+'_PYTHON' for sid,profile in PLANNING.items()})

from .local_completion import PROFILES as COMPLETION
PROFILE_ENV.update({sid: "VERDUGO_"+profile+"_PYTHON" for sid, profile in COMPLETION.items()})

PROFILE_ENV['autogeo'] = 'VERDUGO_UTILITY021_PYTHON'
PROFILE_ENV['sherlock'] = 'VERDUGO_SHERLOCK021_PYTHON'
PROFILE_ENV['tinytroupe'] = 'VERDUGO_SOURCE021_PYTHON'
PROFILE_ENV['kingfisher-collect'] = 'VERDUGO_FINALPY021_PYTHON'

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
