"""Finite synthetic graph paths through the pinned original Oxigraph implementation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .common import VerdugoError, fields, integer
from .local_native import checked

SPECS = {'oxigraph': ('paths.check', 'native:oxigraph', '0.6.0-dev')}
ENV = 'VERDUGO_OXIGRAPH666_ROOT'
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-oxigraph666.json'
RECEIPT = 'share/verdugo-oxigraph/build.json'
BINARY = 'bin/verdugo-oxigraph666-driver'


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts
            or any(c in value for c in ('\0', '\n', '\r'))):
        raise VerdugoError('Absolute administrator Oxigraph runtime required')
    return checked(Path(value), directory=True)


def verify_build(home, record):
    raw = checked(home/RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.oxigraph666.operator-build.v1'
            or receipt.get('contract_sha256') != hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
            or any(receipt.get(k) != record[k] for k in ('commit', 'archive_sha256', 'rust_toolchain', 'driver_files', 'resolved_graph'))
            or set(receipt.get('artifacts', {})) != {BINARY, 'share/verdugo-oxigraph/licenses.json'}):
        raise VerdugoError('Oxigraph original build receipt mismatch')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for path, wanted in receipt['artifacts'].items():
        actual = hashlib.sha256(checked(home/path, budget=16*1024*1024).read_bytes()).hexdigest()
        if actual != wanted:
            raise VerdugoError('Oxigraph native artifact or license notices changed')
        digest.update(bytes.fromhex(actual))
    if not os.access(home/BINARY, os.X_OK):
        raise VerdugoError('Oxigraph native driver is not executable')
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
        raise VerdugoError('Unknown finite graph operation')
    try:
        fields(p, ('dataset', 'edges', 'remove'))
    except ValueError as exc:
        raise VerdugoError('Finite JSON graph values required') from exc
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic integer graph fixtures are supported')
    for name, maximum in (('edges', 32), ('remove', 8)):
        pairs = p[name]
        if not isinstance(pairs, list) or len(pairs) > maximum:
            raise VerdugoError('Bounded edge lists required')
        for pair in pairs:
            if not isinstance(pair, list) or len(pair) != 2:
                raise VerdugoError('Pairs of integer node identifiers required')
            for node in pair: integer(node, 0, 7)


def reachability(edges):
    """Independent finite reachability with positive-length path semantics."""
    adjacency = [set() for _ in range(8)]
    for a, b in edges: adjacency[a].add(b)
    bits = []
    for source in range(8):
        seen, todo = set(), list(adjacency[source])
        while todo:
            node = todo.pop()
            if node in seen: continue
            seen.add(node); todo.extend(adjacency[node]-seen)
        bits.extend(str(int(node in seen)) for node in range(8))
    return ''.join(bits)


def reference(p):
    before = set(map(tuple, p['edges']))
    after = before-set(map(tuple, p['remove']))
    return len(before), len(after), reachability(before), reachability(after)


def wire_input(p):
    return ' '.join(map(str, [len(p['edges']), *[v for pair in p['edges'] for v in pair],
                             len(p['remove']), *[v for pair in p['remove'] for v in pair]])).encode('ascii')


def verify_result(p, raw):
    before_count, after_count, before, after = reference(p)
    try:
        actual = raw.decode('ascii').split()
    except (UnicodeError, AttributeError) as exc:
        raise VerdugoError('Invalid native graph response') from exc
    if actual != [str(before_count), str(after_count), before, after]:
        raise VerdugoError('Original graph query disagrees with finite reference')
    return {'input_edge_records': len(p['edges']), 'removal_records': len(p['remove']),
            'unique_edges_before': before_count, 'unique_edges_after': after_count,
            'removed_edges': before_count-after_count, 'reachable_pairs_before': before.count('1'),
            'reachable_pairs_after': after.count('1'),
            'lost_reachability_pairs': sum(a == '1' and b == '0' for a, b in zip(before, after)),
            'pairwise_checks': 128, 'native_queries': 2}


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original Oxigraph build is unavailable')
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run([str(root()/BINARY)], input=wire_input(p), stdout=out, stderr=err,
                              timeout=10, close_fds=True, env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
        out.seek(0); raw = out.read(4097)
        if proc.returncode or len(raw) > 4096:
            raise VerdugoError('Original bounded Oxigraph driver failed')
    return verify_result(p, raw) | {
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': json.loads(CONTRACT.read_text())['commit'], 'dataset': 'demo',
        'scope': 'fixed_synthetic_in_memory_sparql_paths', 'finite_reference_verified': True,
        'raw_graph_retained': False, 'input_queries_accepted': False,
        'http_client_compiled': False, 'rocksdb_compiled': False, 'persistent_store_created': False,
        'real_world_claim_verified': False, 'llm_calls': 0, 'model_weights_loaded': False,
        'autonomous_agent': False, 'dry_run': True, 'external_calls_made': False,
        'external_execution_authorized': False, 'operator_approval_required': True,
        'approvals_granted': 0, 'business_outcome_proven': False, 'live_verified': False}
