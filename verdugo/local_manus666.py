"""Original OpenManus PlanningTool, limited to fixed synthetic stage tracking."""
import asyncio
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile

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
    validate(service, SPECS[service][0], p)
    raw, record = source_archive()
    with tempfile.TemporaryDirectory(prefix='manus-original-') as tmp:
        root = Path(tmp)
        verified = extract_original(raw, record, root)
        (root / 'config').mkdir()
        (root / 'config/config.toml').write_text(EMPTY_CONFIG)
        # The installed upstream wheel omits app.sandbox.core. Import the exact
        # full original source instead, with config/logs inside this private job.
        if 'app' in sys.modules:
            raise VerdugoError('OpenManus source namespace was already loaded')
        sys.path.insert(0, str(root))
        try:
            from app.tool.planning import PlanningTool
            from app.sandbox.client import SANDBOX_CLIENT

            async def track():
                tool = PlanningTool()
                created = await tool.execute(command='create', plan_id='synthetic',
                    title='Fixed synthetic business process', steps=list(STAGES))
                if created.error:
                    raise ValueError('Original planning tool rejected fixed stages')
                for index, status in enumerate(p['statuses']):
                    marked = await tool.execute(command='mark_step', plan_id='synthetic',
                                                step_index=index, step_status=status)
                    if marked.error:
                        raise ValueError('Original planning tool rejected fixed status')
                plan = tool.plans['synthetic']
                if plan['steps'] != list(STAGES) or plan['step_statuses'] != p['statuses']:
                    raise ValueError('Original planning state was not retained')
                # No sandbox is initialized by importing its lazy client.
                if SANDBOX_CLIENT.sandbox is not None:
                    raise ValueError('Unexpected sandbox initialization')
                states = list(plan['step_statuses'])
                deleted = await tool.execute(command='delete', plan_id='synthetic')
                if deleted.error or tool.plans:
                    raise ValueError('Original planning state was not cleared')
                return states

            states = asyncio.run(track())
        finally:
            sys.path.remove(str(root))
        counts = {s: states.count(s) for s in STATUSES}
        # This consistency diagnostic is our rule, not an upstream planner or
        # an Engine authorization. Reported completion cannot grant approval.
        completed_prefix = 0
        for status in states:
            if status != 'completed':
                break
            completed_prefix += 1
        return {'stage_count': len(STAGES), 'status_counts': counts,
                'synthetic_completed_prefix': completed_prefix,
                'reported_out_of_order_completion': counts['completed'] > completed_prefix,
                'synthetic_plan_complete': counts['completed'] == len(STAGES),
                'first_incomplete_stage': STAGES[completed_prefix] if completed_prefix < len(STAGES) else None,
                'original_sdk': service, 'sdk_version': SPECS[service][2],
                'source_commit': record['commit'], 'original_source_files_verified': verified,
                'dataset': 'demo', 'dry_run': True, 'llm_calls': 0,
                'autonomous_agent': False, 'external_calls_made': False,
                'external_execution_authorized': False, 'operator_approval_required': True,
                'operator_approval_verified': False, 'approvals_granted': 0,
                'sdk_plan_deleted': True, 'sdk_session_persistence': False,
                'business_outcome_proven': False}
