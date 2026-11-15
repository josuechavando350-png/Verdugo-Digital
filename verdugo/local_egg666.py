"""Finite synthetic congruence through the pinned original Egg implementation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .common import VerdugoError, fields, integer
from .local_native import checked

SPECS = {'egg': ('congruence.check', 'native:egg', '0.11.0')}
ENV = 'VERDUGO_EGG666_ROOT'
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-egg666.json'
RECEIPT = 'share/verdugo-egg/build.json'
BINARY = 'bin/verdugo-egg666-driver'


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts
            or any(c in value for c in ('\0', '\n', '\r'))):
        raise VerdugoError('Absolute administrator Egg runtime required')
    return checked(Path(value), directory=True)


def verify_build(home, record):
    raw = checked(home/RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.egg666.operator-build.v1'
            or receipt.get('contract_sha256') != hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
            or any(receipt.get(k) != record[k] for k in ('commit', 'archive_sha256', 'rust_toolchain', 'driver_files', 'resolved_graph'))
            or set(receipt.get('artifacts', {})) != {BINARY, 'share/verdugo-egg/licenses.json'}):
        raise VerdugoError('Egg original build receipt mismatch')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for path, wanted in receipt['artifacts'].items():
        actual = hashlib.sha256(checked(home/path, budget=16*1024*1024).read_bytes()).hexdigest()
        if actual != wanted:
            raise VerdugoError('Egg native artifact or license notices changed')
        digest.update(bytes.fromhex(actual))
    if not os.access(home/BINARY, os.X_OK):
        raise VerdugoError('Egg native driver is not executable')
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        home = root()
        artifacts = verify_build(home, json.loads(CONTRACT.read_text()))
        binding = hashlib.sha256(str(home).encode() + artifacts.encode()).hexdigest()
        present = True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'distribution_kind': 'native', 'expected': version,
            'installed': version if present else None, 'version_matches': present,
            'extra_distributions': {}, 'operation': operation, 'execution_verified': False,
            'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown finite congruence operation')
    try:
        fields(p, ('dataset', 'nodes', 'equalities'))
    except ValueError as exc:
        raise VerdugoError('Finite JSON congruence values required') from exc
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic integer expression graphs are supported')
    nodes = p['nodes']
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 16:
        raise VerdugoError('One to sixteen bounded nodes required')
    for i, node in enumerate(nodes):
        fields(node, ('op', 'children'))
        integer(node['op'], 0, 7)
        children = node['children']
        if not isinstance(children, list) or len(children) > 2:
            raise VerdugoError('At most two earlier child nodes supported')
        for child in children: integer(child, 0, i-1)
    if not isinstance(p['equalities'], list) or len(p['equalities']) > 16:
        raise VerdugoError('At most sixteen synthetic equalities supported')
    for pair in p['equalities']:
        if not isinstance(pair, list) or len(pair) != 2:
            raise VerdugoError('Pairs of node indices required')
        for index in pair: integer(index, 0, len(nodes)-1)


def reference(p):
    """Independent finite partition refinement, without Egg's e-graph machinery."""
    classes = list(range(len(p['nodes'])))

    def merge(a, b):
        old, new = classes[b], classes[a]
        if old == new: return False
        classes[:] = [new if x == old else x for x in classes]
        return True

    for a, b in p['equalities']: merge(a, b)
    while True:
        changed = False
        for i, a in enumerate(p['nodes']):
            for j, b in enumerate(p['nodes'][:i]):
                if (a['op'] == b['op'] and [classes[v] for v in a['children']]
                        == [classes[v] for v in b['children']]):
                    changed = merge(i, j) or changed
        if not changed: return classes


def wire_input(p):
    words = [len(p['nodes'])]
    for node in p['nodes']:
        words.extend([node['op'], len(node['children']), *node['children']])
    words.extend([len(p['equalities']), *[i for pair in p['equalities'] for i in pair]])
    return ' '.join(map(str, words)).encode('ascii')


def verify_result(p, raw):
    classes = reference(p)
    expected = [str(len(classes)), str(len(set(classes))),
                ''.join(str(int(a == b)) for a in classes for b in classes)]
    try:
        actual = raw.decode('ascii').split()
    except (UnicodeError, AttributeError) as exc:
        raise VerdugoError('Invalid native congruence response') from exc
    if actual != expected:
        raise VerdugoError('Native congruence disagrees with finite reference')
    return {'input_nodes': len(classes), 'equivalence_classes': len(set(classes)),
            'equivalent_pairs': sum(a == b for i, a in enumerate(classes) for b in classes[:i]),
            'supplied_equalities': len(p['equalities']), 'pairwise_checks': len(classes)**2}


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original Egg build is unavailable')
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run([str(root()/BINARY)], input=wire_input(p), stdout=out, stderr=err,
                              timeout=10, close_fds=True,
                              env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
        out.seek(0); raw = out.read(4097)
        if proc.returncode or len(raw) > 4096:
            raise VerdugoError('Original bounded Egg driver failed')
    return verify_result(p, raw) | {
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': json.loads(CONTRACT.read_text())['commit'], 'dataset': 'demo',
        'scope': 'fixed_synthetic_finite_congruence', 'finite_reference_verified': True,
        'raw_expressions_retained': False, 'input_programs_accepted': False,
        'rewrite_rules_accepted': False, 'real_world_claim_verified': False,
        'llm_calls': 0, 'model_weights_loaded': False, 'autonomous_agent': False,
        'dry_run': True, 'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False, 'live_verified': False}
