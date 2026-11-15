"""Original SDK ordering of supplied synthetic scores; no model computes relevance."""
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'rerankers': ('results.rank', 'rerankers', '0.10.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-ranking666.json'
PACKAGE = 'lib/python3.12/site-packages'


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
                    raise VerdugoError('Rerankers runtime source changed')
                digest.update(bytes.fromhex(actual))
        if runtime_profile.versions(service, [distribution]) != {distribution: version}:
            raise VerdugoError('Rerankers runtime version differs')
        # Parent and worker must hash the same artifacts. A profile-relative
        # binding changes when its interpreter becomes sys.executable.
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
        raise VerdugoError('Unknown fixed result ranking operation')
    try:
        fields(p, ('dataset', 'mode', 'values', 'limit'))
    except ValueError as exc:
        raise VerdugoError('Finite JSON result values required') from exc
    if p['dataset'] != 'demo' or p['mode'] not in ('score', 'rank'):
        raise VerdugoError('Only synthetic numeric score/rank ordering supported')
    if not isinstance(p['values'], list) or not 1 <= len(p['values']) <= 16:
        raise VerdugoError('One to sixteen synthetic values required')
    for value in p['values']:
        if value is not None:
            integer(value, -1000 if p['mode'] == 'score' else 1, 1000)
    integer(p['limit'], 1, len(p['values']))


def verify_source():
    record = json.loads(CONTRACT.read_text())
    dist = metadata.distribution('rerankers')
    if dist.version != SPECS['rerankers'][2]:
        raise VerdugoError('Rerankers distribution version mismatch')
    count = 0
    for entry in record['files']:
        if entry['installed_path']:
            data = checked(Path(dist.locate_file(entry['installed_path'])), budget=8*1024*1024).read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise VerdugoError('Installed Rerankers differs from original source')
            count += 1
    if count != record['installed_source_count']:
        raise VerdugoError('Incomplete Rerankers source evidence')
    return {'source_commit': record['commit'], 'original_source_files_verified': count}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    from rerankers.documents import Document
    from rerankers.results import Result, RankedResults

    scored = p['mode'] == 'score'
    results = []
    for i, value in enumerate(p['values']):
        # The other field makes an absent score/rank an upstream-valid Result.
        results.append(Result(Document(text='synthetic_candidate_'+str(i), doc_id=i),
                              score=value if scored else 0, rank=i+1 if scored else value))
    ranked = RankedResults(results, query='synthetic_result_ordering', has_scores=scored)
    chosen = ranked.top_k(p['limit'])
    actual = [r.document.doc_id for r in chosen]
    values = p['values']
    reference = sorted(range(len(values)), key=lambda i:
                       (values[i] is None, (-values[i] if scored else values[i]) if values[i] is not None else 0))
    if actual != reference[:p['limit']] or ranked.results_count() != len(values):
        raise VerdugoError('SDK result ordering differs from numeric reference')
    for i, row in enumerate(results):
        if ranked.get_result_by_docid(i) is not row or ranked.get_score_by_docid(i) != row.score:
            raise VerdugoError('SDK result lookup differs from supplied data')
    if ranked.get_result_by_docid(100) is not None or ranked.get_score_by_docid(100) is not None:
        raise VerdugoError('SDK missing-result lookup differs')
    return evidence | {'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'mode': p['mode'], 'result_count': len(values), 'selected_count': len(actual),
        'selected_indices': actual, 'missing_value_count': sum(v is None for v in values),
        'independent_numeric_order_verified': True, 'lookup_checks': len(values)+1,
        'scores_computed_by_model': False, 'semantic_relevance_verified': False,
        'raw_document_text_retained': False, 'model_backends_initialized': 0,
        'model_weights_loaded': False, 'llm_calls': 0, 'autonomous_agent': False,
        'dry_run': True, 'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False, 'live_verified': False}
