"""Original Monty subprocess interpreter; only a fixed synthetic allocation check."""
import hashlib
import json
import os
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'monty': ('budget.evaluate', 'pydantic-monty-client', '1.6.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-monty666.json'
RECEIPT = 'share/verdugo-monty/build.json'
NATIVE = ('bin/monty', 'lib/python3.12/site-packages/pydantic_monty/_monty.cpython-312-x86_64-linux-gnu.so')
PROGRAM = '''cost = 0
contacts = 0
for row in allocations:
    contacts += row[0]
    cost += row[0] * row[1]
{"planned_cost_minor": cost, "planned_contacts": contacts, "within_budget": cost <= budget, "within_capacity": contacts <= capacity}
'''
LIMITS = {'max_feed_duration_secs': 1.0, 'max_turn_duration_secs': 2.0,
          'max_memory': 16 * 1024 * 1024, 'max_recursion_depth': 32,
          'max_suspensions': 1, 'max_total_sleep_secs': 0.0}


def home():
    return checked(Path(runtime_profile.interpreter('monty')).parent.parent, directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.monty666.operator-build.v1' or
            receipt.get('commit') != record['commit'] or
            receipt.get('archive_sha256') != record['archive_sha256'] or
            receipt.get('rust_version') != record['rust_version'] or
            receipt.get('maturin_version') != record['maturin_version'] or
            receipt.get('build_environment') != record['build_environment'] or
            set(receipt.get('native_artifacts', {})) != set(NATIVE)):
        raise VerdugoError('Missing or inconsistent operator-built Monty receipt')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for name in NATIVE:
        path = checked(root / name, budget=256 * 1024 * 1024)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != receipt['native_artifacts'][name]:
            raise VerdugoError('Native Monty artifact changed since explicit preparation')
        digest.update(bytes.fromhex(actual))
    if not os.access(root / 'bin/monty', os.X_OK):
        raise VerdugoError('Monty worker is not executable')
    for source in record['files']:
        if source['installed_path']:
            actual = hashlib.sha256(checked(root / source['installed_path']).read_bytes()).hexdigest()
            if actual != source['sha256']:
                raise VerdugoError('Installed Python interface differs from original Monty source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        record = json.loads(CONTRACT.read_text())
        root = home()
        artifact_binding = verify_build(root, record)
        versions = runtime_profile.versions(service, [distribution, 'pydantic-monty-runtime'])
        if any(value != version for value in versions.values()):
            raise VerdugoError('Native Monty distribution version mismatch')
        digest = hashlib.sha256(str(root).encode() + artifact_binding.encode())
        digest.update(checked(root / 'bin/python', budget=64 * 1024 * 1024).read_bytes())
        digest.update(checked(root / 'pyvenv.cfg', budget=16384).read_bytes())
        binding = digest.hexdigest()
        present = True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed Monty operation')
    fields(p, ('dataset', 'budget_minor', 'capacity_contacts', 'actions'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic demo allocations supported')
    integer(p['budget_minor'], 0, 10**9)
    integer(p['capacity_contacts'], 0, 20000)
    if not isinstance(p['actions'], list) or not 1 <= len(p['actions']) <= 4:
        raise VerdugoError('One to four fixed allocation rows required')
    for row in p['actions']:
        fields(row, ('contacts', 'cost_per_contact_minor'))
        integer(row['contacts'], 0, 20000)
        integer(row['cost_per_contact_minor'], 0, 10**7)


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed Monty source build unavailable')
    from pydantic_monty import Monty

    # No payload code, imports, callbacks, mounts, paths or network destinations.
    # Resource limits bound this fixed program; this is not a hostile-code API.
    with Monty(binary_path=str(home() / 'bin/monty'), min_processes=1, max_processes=1,
               checkout_timeout=5, request_timeout=5, max_checkouts_per_worker=1) as pool:
        with pool.checkout(limits=LIMITS, type_check=True,
                type_check_stubs='allocations: list[list[int]]\nbudget: int\ncapacity: int\n') as session:
            result = session.feed_run(PROGRAM, inputs={
                'allocations': [[a['contacts'], a['cost_per_contact_minor']] for a in p['actions']],
                'budget': p['budget_minor'], 'capacity': p['capacity_contacts']})
    if (not isinstance(result, dict) or set(result) != {
            'planned_cost_minor', 'planned_contacts', 'within_budget', 'within_capacity'} or
            any(type(result[k]) is not int for k in ('planned_cost_minor', 'planned_contacts')) or
            any(type(result[k]) is not bool for k in ('within_budget', 'within_capacity'))):
        raise VerdugoError('Unexpected original Monty result')
    record = json.loads(CONTRACT.read_text())
    return result | {'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': record['commit'], 'original_python_files_verified':
            sum(bool(f['installed_path']) for f in record['files']),
        'fixed_program_sha256': hashlib.sha256(PROGRAM.encode()).hexdigest(),
        'native_artifact_receipt_verified': True, 'reproducible_binary_build_proven': False,
        'native_worker_processes': 1, 'type_check_enabled': True,
        'resource_limits': LIMITS, 'arbitrary_code_accepted': False,
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}
