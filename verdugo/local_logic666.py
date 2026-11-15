"""Fixed finite integer feasibility with the original source-built Z3 solver."""
import hashlib
from itertools import product
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'z3': ('constraints.check', 'z3-solver', '5.4.2.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-logic666.json'
PACKAGE = 'lib/python3.12/site-packages'
RECEIPT = 'share/verdugo-z3/build.json'
COSTS = (3, 5, 7)
YIELDS = (2, 4, 5)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.z3666.operator-build.v1'
            or any(receipt.get(k) != record[k] for k in
                   ('commit', 'archive_sha256', 'build_tools', 'cmake_options'))):
        raise VerdugoError('Z3 original source build receipt mismatch')
    expected = set(record['native_artifacts'] + record['generated_python'])
    if set(receipt.get('artifacts', {})) != expected:
        raise VerdugoError('Z3 receipt artifact set mismatch')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for path, wanted in receipt['artifacts'].items():
        actual = hashlib.sha256(checked(root / PACKAGE / path, budget=128*1024*1024).read_bytes()).hexdigest()
        if actual != wanted:
            raise VerdugoError('Z3 generated or native artifact changed')
        digest.update(bytes.fromhex(actual))
    for entry in record['files']:
        if entry['installed_path']:
            actual = hashlib.sha256(checked(root / PACKAGE / entry['installed_path'], budget=8*1024*1024).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed Z3 interface differs from original source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = checked(Path(runtime_profile.interpreter(service)).parent.parent, directory=True)
        record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        if runtime_profile.versions(service, [distribution]) != {distribution: version}:
            raise VerdugoError('Z3 distribution version differs')
        digest = hashlib.sha256(str(root).encode() + artifacts.encode())
        digest.update(checked(root / 'bin/python', budget=64*1024*1024).read_bytes())
        digest.update(checked(root / 'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed finite constraint operation')
    try:
        fields(p, ('dataset', 'spend_limit', 'unit_limit', 'minimum_yield'))
    except ValueError as exc:
        raise VerdugoError('Finite JSON constraint values required') from exc
    if p['dataset'] != 'demo':
        raise VerdugoError('Only the fixed synthetic integer portfolio is supported')
    integer(p['spend_limit'], 0, 45)
    integer(p['unit_limit'], 0, 9)
    integer(p['minimum_yield'], 0, 33)


def scalar_candidates(p):
    return [xs for xs in product(range(4), repeat=3)
            if sum(x*c for x,c in zip(xs, COSTS)) <= p['spend_limit']
            and sum(xs) <= p['unit_limit']
            and sum(x*y for x,y in zip(xs, YIELDS)) >= p['minimum_yield']]


def verify_verdict(p, verdict, witness):
    expected = scalar_candidates(p)
    if verdict not in ('sat', 'unsat') or (verdict == 'sat') != bool(expected):
        raise VerdugoError('Native feasibility disagrees with exhaustive reference')
    if verdict == 'sat':
        if (not isinstance(witness, tuple) or len(witness) != 3
                or any(type(v) is not int for v in witness) or witness not in expected):
            raise VerdugoError('Native witness violates the finite reference')
    elif witness is not None:
        raise VerdugoError('Infeasible case returned a witness')
    return len(expected)


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original Z3 build is unavailable')
    import z3
    if z3.get_version() != (5, 4, 2, 0):
        raise VerdugoError('Native Z3 version differs')
    context = z3.Context()
    solver = z3.Solver(ctx=context)
    solver.set(timeout=1000, rlimit=200000, random_seed=666)
    xs = [z3.Int('synthetic_units_'+str(i), ctx=context) for i in range(3)]
    for x in xs:
        solver.add(x >= 0, x <= 3)
    solver.add(z3.Sum([x*c for x,c in zip(xs, COSTS)]) <= p['spend_limit'],
               z3.Sum(xs) <= p['unit_limit'],
               z3.Sum([x*y for x,y in zip(xs, YIELDS)]) >= p['minimum_yield'])
    verdict = solver.check()
    if verdict not in (z3.sat, z3.unsat):
        raise VerdugoError('Native solver did not establish a bounded verdict')
    status, witness = ('sat', None) if verdict == z3.sat else ('unsat', None)
    if status == 'sat':
        model = solver.model()
        witness = tuple(model.eval(x, model_completion=True).as_long() for x in xs)
    count = verify_verdict(p, status, witness)
    return {'original_sdk': service, 'sdk_version': SPECS[service][2],
            'source_commit': json.loads(CONTRACT.read_text())['commit'], 'dataset': 'demo',
            'verdict': status, 'assignments_examined_independently': 64,
            'feasible_assignments': count, 'native_solver_checks': 1,
            'native_witness_units': list(witness) if witness is not None else None,
            'finite_reference_verified': True, 'business_constraints': 3, 'integer_variables': 3,
            'scope': 'fixed_synthetic_finite_integer_feasibility', 'optimality_proven': False,
            'real_world_claim_verified': False, 'input_programs_accepted': False,
            'llm_calls': 0, 'model_weights_loaded': False, 'autonomous_agent': False,
            'dry_run': True, 'external_calls_made': False, 'external_execution_authorized': False,
            'operator_approval_required': True, 'approvals_granted': 0,
            'business_outcome_proven': False, 'live_verified': False}
