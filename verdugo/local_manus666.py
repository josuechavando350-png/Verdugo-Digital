"""Original OpenManus PlanningTool, limited to fixed synthetic stage tracking."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile

from .common import VerdugoError, fields
from .local_planning666 import STAGES

SPECS = {'openmanus': ('stages.track', 'openmanus', '0.1.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-manus666.json'
STATUSES = ('not_started', 'in_progress', 'completed', 'blocked')
# Upstream validates these settings when importing any tool. Empty values are
# inert, never provider options; neither an LLM nor Daytona client is created.
EMPTY_CONFIG = ('[llm]\nmodel=""\nbase_url=""\napi_key=""\n'
                'api_type=""\napi_version=""\n[daytona]\n'
                'daytona_api_key=""\ndaytona_server_url=""\n')


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed stage-tracking operation')
    fields(p, ('dataset', 'statuses'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic demo data is supported')
    if (not isinstance(p['statuses'], list) or len(p['statuses']) != len(STAGES) or
            any(not isinstance(s, str) or s not in STATUSES for s in p['statuses'])):
        raise VerdugoError('Exactly five fixed synthetic statuses are required')


def source_archive():
    # This worker executes under the administrator's interpreter. No source
    # location is accepted from payloads or read from the caller's environment.
    path = Path(sys.prefix) / 'share/verdugo-openmanus/source.tar.gz'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise VerdugoError('Missing or unsafe pinned OpenManus source archive')
    raw = path.read_bytes()
    record = json.loads(CONTRACT.read_text())
    if hashlib.sha256(raw).hexdigest() != record['archive_sha256']:
        raise VerdugoError('OpenManus source archive differs from reviewed commit')
    return raw, record


def extract_original(raw, record, destination):
    """Copy verified app bytes only; never extract links or archive paths blindly."""
    expected = {f['path']: f for f in record['source_files'] if f['path'].startswith('app/')}
    copied = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for member in archive.getmembers():
            parts = PurePosixPath(member.name).parts[1:]
            path = '/'.join(parts)
            if not path.startswith('app/') or member.isdir():
                continue
            if (not member.isfile() or path not in expected or path in copied or
                    any(p in ('..', '.', '') for p in parts) or member.size > 1024 * 1024):
                raise VerdugoError('Unexpected OpenManus source member')
            data = archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != expected[path]['sha256']:
                raise VerdugoError('OpenManus module differs from original source')
            dest = destination.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            copied.add(path)
    if copied != set(expected):
        raise VerdugoError('Incomplete OpenManus source archive')
    return len(copied)


def run(service, p):
    # Functional acceptance did not establish dependency-license compatibility.
    # Original setup.py requires html2text GPL-3.0; do not import this SDK.
    raise VerdugoError('OpenManus is pending: required html2text GPL-3.0 is outside project policy')
