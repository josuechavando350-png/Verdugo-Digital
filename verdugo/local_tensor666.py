"""Original Candle CPU matrix scoring; caller-supplied coefficients are not learned."""
import hashlib
import json
import math
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

CANDIDATE_SPECS = {'candle': ('scores.normalize', 'candle-nn', '0.11.1')}
SPECS = {}  # Quarantined: dependency license outside the configured allowlist.
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-tensor666.json'
RECEIPT = 'share/verdugo-candle/build.json'
PACKAGE = 'lib/python3.13/site-packages'
NATIVE = PACKAGE + '/candle/candle.abi3.so'


def home():
    return checked(Path(runtime_profile.interpreter('candle')).parent.parent, directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.candle666.operator-build.v1' or
            any(receipt.get(key) != record[key] for key in
                ('commit', 'archive_sha256', 'cargo_lock_sha256', 'rust_version',
                 'maturin_version', 'build_environment'))):
        raise VerdugoError('Candle source build receipt mismatch')
    package = checked(root / PACKAGE / 'candle', directory=True)
    if {p.name for p in package.glob('*.so')} != {'candle.abi3.so'}:
        raise VerdugoError('Unexpected alternate Candle extension')
    native = checked(root / NATIVE, budget=64*1024*1024).read_bytes()
    actual = hashlib.sha256(native).hexdigest()
    if actual != receipt.get('native_sha256'):
        raise VerdugoError('Compiled Candle artifact changed')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes() + bytes.fromhex(actual))
    for entry in record['files']:
        if entry['installed_path']:
            actual = hashlib.sha256(checked(root / PACKAGE / entry['installed_path']).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed Candle interface differs from original source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = home(); record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        if runtime_profile.versions(service, [distribution]) != {distribution: version}:
            raise VerdugoError('Candle distribution version mismatch')
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
    if service not in CANDIDATE_SPECS or operation != CANDIDATE_SPECS[service][0]:
        raise VerdugoError('Unknown fixed tensor scoring operation')
    fields(p, ('dataset', 'features', 'coefficients'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic numeric features supported')
    if not isinstance(p['coefficients'], list) or not 2 <= len(p['coefficients']) <= 4:
        raise VerdugoError('Two to four integer coefficients required')
    if not isinstance(p['features'], list) or not 2 <= len(p['features']) <= 8:
        raise VerdugoError('Two to eight feature rows required')
    for value in p['coefficients']:
        integer(value, -100, 100)
    for row in p['features']:
        if not isinstance(row, list) or len(row) != len(p['coefficients']):
            raise VerdugoError('Rectangular feature matrix required')
        for value in row:
            integer(value, -100, 100)


def run(service, p):
    raise VerdugoError('Candle dependency license review unresolved; candidate disabled')


def _historical_unregistered_recipe(service, p):
    raise VerdugoError('Quarantined historical candidate')
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed original Candle build unavailable')
    import candle
    from candle.functional import softmax

    if Path(candle.candle.__file__).resolve() != (home() / NATIVE).resolve():
        raise VerdugoError('Unexpected Candle native extension resolution')
    features = candle.tensor([[float(x) for x in row] for row in p['features']])
    weights = candle.tensor([[float(x)] for x in p['coefficients']])
    scores = features.matmul(weights)
    normalized = softmax(scores, 0)
    values = scores.values(); shares = normalized.values()
    rows = len(p['features'])
    if (scores.shape != (rows, 1) or normalized.shape != (rows, 1) or
            scores.device != 'cpu' or str(scores.dtype) != 'F32' or
            len(values) != rows or len(shares) != rows or
            any(len(row) != 1 or not math.isfinite(row[0]) for row in values + shares)):
        raise VerdugoError('Unexpected original tensor result')
    # Independent bounded scalar reference checks the native multiplication.
    reference = [sum(x*w for x, w in zip(row, p['coefficients'])) for row in p['features']]
    error = max(abs(row[0] - expected) for row, expected in zip(values, reference))
    total = float(normalized.sum_all().values())
    if error != 0 or abs(total - 1) > 1e-6 or any(not 0 <= row[0] <= 1 for row in shares):
        raise VerdugoError('Original matrix or normalization check failed')
    best = max(row[0] for row in values)
    entropy = -sum(row[0] * math.log(row[0]) for row in shares if row[0] > 0)
    return {'row_count': rows, 'feature_count': len(p['coefficients']),
        'coefficient_count': len(p['coefficients']), 'top_row_indices':
            [i for i, row in enumerate(values) if row[0] == best],
        'maximum_score': best, 'maximum_normalized_share': max(row[0] for row in shares),
        'normalized_sum': total, 'entropy_nats': entropy,
        'matrix_reference_max_error': error, 'native_matmul_verified': True,
        'cpu_only': True, 'coefficients_supplied_not_learned': True,
        'normalized_shares_are_outcome_probabilities': False,
        'model_weights_loaded': False, 'quality_calibrated': False,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': json.loads(CONTRACT.read_text())['commit'],
        'native_artifact_receipt_verified': True, 'reproducible_binary_build_proven': False,
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}
