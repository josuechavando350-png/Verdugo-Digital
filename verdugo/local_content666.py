"""Bounded txtai content-store reconciliation using the original minimal build."""
import hashlib
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'txtai': ('content.reconcile', 'txtai_minimal', '9.15.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-content666.json'
PACKAGE = 'lib/python3.12/site-packages'
QUERY = ('SELECT segment, SUM(amount) AS total, COUNT(*) AS records '
         'FROM txtai GROUP BY segment ORDER BY segment')


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = checked(Path(runtime_profile.interpreter(service)).parent.parent, directory=True)
        record = json.loads(CONTRACT.read_text())
        digest = hashlib.sha256(CONTRACT.read_bytes() + str(root).encode())
        for entry in record['files']:
            if entry['installed_path']:
                data = checked(root / PACKAGE / entry['installed_path'], budget=8*1024*1024).read_bytes()
                actual = hashlib.sha256(data).hexdigest()
                if actual != entry['sha256']:
                    raise VerdugoError('txtai original source changed')
                digest.update(bytes.fromhex(actual))
        # Optional model/provider extras are outside this profile. Reject extra
        # installed distributions as well as injected source modules.
        site = root / PACKAGE
        allowed = {'pip', 'txtai_minimal'}
        installed = {p.name.removesuffix('.dist-info').rsplit('-', 1)[0] for p in site.glob('*.dist-info')}
        if installed != allowed:
            raise VerdugoError('Unexpected dependency in minimal txtai profile')
        expected_paths = {e['installed_path'] for e in record['files'] if e['installed_path'] and e['installed_path'].endswith('.py')}
        if {str(p.relative_to(site)) for p in (site/'txtai').rglob('*.py')} != expected_paths:
            raise VerdugoError('Unexpected module in minimal txtai profile')
        if runtime_profile.versions(service, [distribution]) != {distribution: version}:
            raise VerdugoError('txtai minimal version mismatch')
        digest.update(checked(root/'bin/python', budget=64*1024*1024).read_bytes())
        digest.update(checked(root/'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed content reconciliation operation')
    try:
        fields(p, ('dataset', 'rows', 'remove'))
    except ValueError as exc:
        raise VerdugoError('Finite JSON content values required') from exc
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic numeric content is supported')
    if not isinstance(p['rows'], list) or not 1 <= len(p['rows']) <= 32:
        raise VerdugoError('One to thirty-two numeric records required')
    for row in p['rows']:
        if not isinstance(row, list) or len(row) != 2:
            raise VerdugoError('Each row contains a segment and integer amount')
        integer(row[0], 0, 7)
        integer(row[1], -1000000, 1000000)
    if not isinstance(p['remove'], list) or len(p['remove']) > len(p['rows']):
        raise VerdugoError('Bounded deletion indices required')
    for index in p['remove']:
        integer(index, 0, len(p['rows'])-1)
    if len(set(p['remove'])) != len(p['remove']):
        raise VerdugoError('Deletion indices must be distinct')


def reference(rows, removed=()):
    groups = {}
    for i, (segment, amount) in enumerate(rows):
        if i not in removed:
            group = groups.setdefault(segment, {'segment': segment, 'total': 0, 'records': 0})
            group['total'] += amount
            group['records'] += 1
    return [groups[k] for k in sorted(groups)]


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original minimal txtai runtime is unavailable')
    from txtai.database import SQLite

    database = SQLite({'content': True})
    try:
        database.insert([('fixed_content_'+str(i), {'text': 'fixed_synthetic_content',
                          'segment': segment, 'amount': amount}, None)
                         for i, (segment, amount) in enumerate(p['rows'])])
        before = database.search(QUERY)
        if before != reference(p['rows']) or database.count() != len(p['rows']):
            raise VerdugoError('Original content store disagrees with numeric reference')
        ids = ['fixed_content_'+str(i) for i in p['remove']]
        database.delete(ids)
        after = database.search(QUERY)
        if after != reference(p['rows'], p['remove']) or database.count() != len(p['rows'])-len(ids):
            raise VerdugoError('Original content removal disagrees with numeric reference')
        database.delete(ids)
        if database.search(QUERY) != after or database.count() != len(p['rows'])-len(ids):
            raise VerdugoError('Repeated deletion changed original content store')
    finally:
        database.close()
    return {'original_sdk': service, 'sdk_version': SPECS[service][2], 'dataset': 'demo',
            'profile': 'upstream_MINIMAL', 'input_count': len(p['rows']), 'removed_count': len(p['remove']),
            'remaining_count': len(p['rows'])-len(p['remove']), 'before_groups': before, 'after_groups': after,
            'independent_aggregates_verified': True, 'repeated_deletion_verified': True,
            'ephemeral_content_store_closed': True, 'persistent_content_store': False,
            'raw_text_retained': False, 'semantic_search_verified': False,
            'model_weights_loaded': False, 'llm_calls': 0, 'autonomous_agent': False,
            'dry_run': True, 'external_calls_made': False, 'external_execution_authorized': False,
            'operator_approval_required': True, 'approvals_granted': 0,
            'business_outcome_proven': False, 'live_verified': False}
