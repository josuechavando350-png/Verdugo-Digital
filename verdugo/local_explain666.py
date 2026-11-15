"""Original InterpretML fit/predict/term decomposition on bounded demo rows."""
import hashlib
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'interpret': ('prediction.explain', 'interpret-core', '0.7.8')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-explain666.json'
RECEIPT = 'share/verdugo-interpret/build.json'
PACKAGE = 'lib/python3.12/site-packages/interpret'
BUILD_FILES = ('root/bld/lib/libebm_linux_x64.so', 'root/bld/lib/interpret-inline.js',
               'root/bld/lib/interpret-inline.js.LICENSE.txt')
SETTINGS = {'feature_names': ['contacts', 'spend_minor'],
    'feature_types': ['continuous', 'continuous'], 'max_bins': 8, 'interactions': 0,
    'outer_bags': 1, 'inner_bags': 0, 'validation_size': 0, 'max_rounds': 16,
    'early_stopping_rounds': 0, 'smoothing_rounds': 0, 'interaction_smoothing_rounds': 0,
    'greedy_ratio': 0, 'cyclic_progress': 1, 'min_samples_leaf': 2,
    'n_jobs': 1, 'random_state': 666}


def home():
    return checked(Path(runtime_profile.interpreter('interpret')).parent.parent, directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.interpret666.operator-build.v1' or
            receipt.get('commit') != record['commit'] or
            receipt.get('archive_sha256') != record['archive_sha256'] or
            receipt.get('build_arguments') != ['-release_64'] or
            receipt.get('npm_lock_sha256') != record['npm_lock_sha256'] or
            set(receipt.get('artifacts', {})) != set(BUILD_FILES)):
        raise VerdugoError('Interpret source build receipt mismatch')
    lib = checked(root / PACKAGE / 'root/bld/lib', directory=True)
    if {p.name for p in lib.iterdir()} != {Path(p).name for p in BUILD_FILES}:
        raise VerdugoError('Unexpected alternate Interpret native library')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for name in BUILD_FILES:
        actual = hashlib.sha256(checked(root / PACKAGE / name, budget=64*1024*1024).read_bytes()).hexdigest()
        if actual != receipt['artifacts'][name]:
            raise VerdugoError('Compiled Interpret artifact changed')
        digest.update(bytes.fromhex(actual))
    for entry in record['files']:
        if entry['installed_path']:
            path = root / 'lib/python3.12/site-packages' / entry['installed_path']
            actual = hashlib.sha256(checked(path).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed Interpret Python differs from original source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    binding, present = None, False
    try:
        root = home(); record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        versions = runtime_profile.versions(service, ['interpret-core', 'numpy', 'joblib', 'cloudpickle'])
        if versions != record['runtime_versions']:
            raise VerdugoError('Interpret dependency version mismatch')
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
        raise VerdugoError('Unknown fixed explanation operation')
    fields(p, ('dataset', 'training', 'queries'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic demonstration rows supported')
    for key, low, high in [('training', 8, 32), ('queries', 1, 4)]:
        if not isinstance(p[key], list) or not low <= len(p[key]) <= high:
            raise VerdugoError('Bounded synthetic training/query rows required')
        for row in p[key]:
            fields(row, ('contacts', 'spend_minor', 'observed_clients') if key == 'training'
                   else ('contacts', 'spend_minor'))
            integer(row['contacts'], 0, 1000)
            integer(row['spend_minor'], 0, 10**6)
            if key == 'training': integer(row['observed_clients'], 0, row['contacts'])


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed original Interpret build unavailable')
    import numpy as np
    from interpret.glassbox import ExplainableBoostingRegressor
    from interpret.utils._native import Native

    # Reject an alternate dynamic-library lookup even if its filename is valid.
    wanted = (home() / PACKAGE / BUILD_FILES[0]).resolve()
    if Path(Native._get_ebm_lib_path()).resolve() != wanted:
        raise VerdugoError('Unexpected original native library resolution')
    train = np.array([[r['contacts'], r['spend_minor']] for r in p['training']], dtype=np.float64)
    targets = np.array([r['observed_clients'] for r in p['training']], dtype=np.float64)
    queries = np.array([[r['contacts'], r['spend_minor']] for r in p['queries']], dtype=np.float64)
    model = ExplainableBoostingRegressor(**SETTINGS)
    model.fit(train, targets)
    predicted = model.predict(queries)
    terms = model.eval_terms(queries)
    if (terms.shape != (len(queries), 2) or predicted.shape != (len(queries),) or
            model.link_ != 'identity' or not np.isfinite(predicted).all() or
            not np.isfinite(terms).all() or not np.isfinite(model.intercept_)):
        raise VerdugoError('Unexpected original additive model result')
    reconstructed = terms.sum(axis=1) + model.intercept_
    error = float(np.max(np.abs(predicted - reconstructed)))
    consistent = bool(np.allclose(predicted, reconstructed, rtol=1e-12, atol=1e-12))
    return {'training_row_count': len(train), 'query_row_count': len(queries),
        'feature_count': 2, 'term_count': len(model.term_features_),
        'max_additive_reconstruction_error': error, 'additive_reconstruction_verified': consistent,
        'mean_absolute_contribution': dict(zip(SETTINGS['feature_names'],
            np.mean(np.abs(terms), axis=0).tolist())),
        'model_trained_locally': True, 'model_persisted': False,
        'held_out_accuracy_measured': False, 'causal_explanation_proven': False,
        'quality_calibrated': False, 'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': json.loads(CONTRACT.read_text())['commit'],
        'native_artifact_receipt_verified': True, 'reproducible_binary_build_proven': False,
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0, 'business_outcome_proven': False}
