"""Original CPU proximity graph checked on two fixed synthetic datasets."""
from array import array
import hashlib
import json
import math
from pathlib import Path

from .common import VerdugoError, fields
from .local_native import checked
from . import runtime_profile

SPECS = {'usearch': ('neighbors.check', 'usearch', '3.0.0rc1')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-usearch666.json'
RECEIPT = 'share/verdugo-usearch/build.json'
PACKAGE = 'lib/python3.12/site-packages'
NATIVE = PACKAGE + '/usearch/lib.cpython-312-x86_64-linux-gnu.so'


def home():
    return checked(Path(runtime_profile.interpreter('usearch')).parent.parent, directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    source_bindings = {r['id']: r['archive_sha256'] for r in record['sources']}
    if (receipt.get('schema') != 'verdugo.usearch666.operator-build.v1'
            or receipt.get('source_archives') != source_bindings
            or any(receipt.get(k) != record[k] for k in
                   ('commit', 'build_tools', 'build_environment', 'cmake_options'))):
        raise VerdugoError('USearch original source build receipt mismatch')
    package = checked(root / PACKAGE / 'usearch', directory=True)
    if {p.name for p in package.glob('*.so')} != {Path(NATIVE).name}:
        raise VerdugoError('Unexpected alternate USearch extension')
    actual = hashlib.sha256(checked(root / NATIVE, budget=32*1024*1024).read_bytes()).hexdigest()
    if actual != receipt.get('native_sha256'):
        raise VerdugoError('USearch native artifact changed')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes() + bytes.fromhex(actual))
    for entry in record['sources'][0]['files']:
        if entry['installed_path']:
            actual = hashlib.sha256(checked(root / PACKAGE / entry['installed_path'],
                                           budget=8*1024*1024).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed USearch interface differs from original source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = home(); record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        if runtime_profile.versions(service, [distribution]) != {distribution: version}:
            raise VerdugoError('USearch distribution version mismatch')
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
        raise VerdugoError('Unknown fixed USearch operation')
    fields(p, ('dataset', 'case'))
    if p['dataset'] != 'demo' or p['case'] not in ('plane', 'line'):
        raise VerdugoError('Only fixed synthetic neighbor cases supported')


def _tensor(rows):
    return memoryview(array('f', (v for row in rows for v in row))).cast('B').cast(
        'f', shape=[len(rows), len(rows[0])])


def verify_neighbors(rows, queries, answers, wanted=3):
    """Independent scalar oracle; equal-distance neighbors may exchange order."""
    if len(answers) != len(queries):
        raise VerdugoError('USearch query count differs')
    max_error = 0.0
    for query, matches in zip(queries, answers):
        reference = {i: math.dist(query, row) for i, row in enumerate(rows)}
        threshold = sorted(reference.values())[wanted - 1]
        if len(matches) != wanted or len({key for key, _ in matches}) != wanted:
            raise VerdugoError('USearch neighbor cardinality differs')
        distances = []
        for key, distance in matches:
            if (type(key) is not int or key not in reference or not math.isfinite(distance)
                    or reference[key] > threshold + 1e-6):
                raise VerdugoError('USearch selected neighbor differs from scalar reference')
            error = abs(distance - reference[key])
            if error > 1e-4:
                raise VerdugoError('USearch distance differs from scalar reference')
            max_error = max(max_error, error)
            distances.append(distance)
        if any(a > b + 1e-4 for a, b in zip(distances, distances[1:])):
            raise VerdugoError('USearch neighbors are not distance ordered')
    return max_error


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed original USearch build unavailable')
    import usearch
    from usearch import Arena, DenseIndex, DenseMetric, Scalar, Traversal

    record = json.loads(CONTRACT.read_text())
    if usearch.__version__ != record['native_reported_version']:
        raise VerdugoError('USearch native version differs')
    if p['case'] == 'plane':
        rows = [[0, 0], [2, 0], [0, 3], [4, 4], [8, 1]]
        queries = [[1, 0], [1, 2], [6, 2]]
    else:
        rows = [[i, 2*i, 3*i] for i in range(8)]
        queries = [[i, 2*i, 3*i] for i in (.25, 3.25, 6.75)]
    index = DenseIndex.init_ram(len(rows[0]), DenseMetric.EUCLIDEAN, Scalar.BF16, connectivity=8)
    index.insert(list(range(len(rows))), _tensor(rows), expansion_factor=16)
    description = index.describe()
    if description.size != len(rows) or description.gpu_class is not None:
        raise VerdugoError('Unexpected USearch CPU graph geometry')
    errors = {}
    for name, traversal in (('walk', Traversal.WALK), ('scan', Traversal.SCAN)):
        arena = Arena()
        matches = index.search(_tensor(queries), 3, arena, traversal=traversal, expansion_factor=16)
        answers = [[(int(m.key), float(m.distance)) for m in matches[i]] for i in range(len(queries))]
        errors[name] = verify_neighbors(rows, queries, answers)
    health = index.health()
    if health.audited != len(rows) or health.reachable != len(rows):
        raise VerdugoError('Synthetic USearch graph is not fully reachable')
    return {'original_sdk': service, 'sdk_version': SPECS[service][2], 'source_commit': record['commit'],
            'native_reported_version': usearch.__version__, 'native_cpu_path_used': True,
            'native_artifact_receipt_verified': True, 'reproducible_binary_build_proven': False,
            'dataset': 'demo', 'case': p['case'], 'vectors_indexed': len(rows),
            'dimensions': len(rows[0]), 'query_count': len(queries), 'neighbors_per_query': 3,
            'stored_dtype': 'bf16', 'walk_matches_checked': 9, 'scan_matches_checked': 9,
            'walk_distance_max_error': errors['walk'], 'scan_distance_max_error': errors['scan'],
            'independent_scalar_reference_verified': True, 'graph_entries_reachable': health.reachable,
            'raw_vectors_retained': False, 'corpus_recall_measured': False, 'speed_benchmarked': False,
            'models_used': 0, 'llm_calls': 0, 'autonomous_agent': False, 'dry_run': True,
            'external_calls_made': False, 'external_execution_authorized': False,
            'operator_approval_required': True, 'approvals_granted': 0,
            'business_outcome_proven': False, 'live_verified': False}
