"""Bounded original lexical retrieval; only aggregate synthetic counts escape."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'bm25s': ('retrieval.check', 'bm25s', '0.0.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-bm25s666.json'
PACKAGE = 'lib/python3.12/site-packages'
RECEIPT = 'share/verdugo-bm25s/build.json'


def package_files(site):
    for name in ('bm25s', 'numpy'):
        checked(site/name, directory=True)
        if any(p.is_symlink() for p in (site/name).rglob('*')):
            raise VerdugoError('Symlink in BM25S profile')
    return {str(p.relative_to(site)) for name in ('bm25s', 'numpy')
            for p in (site/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def verify_build(root, record):
    raw = checked(root/RECEIPT, budget=1024*1024).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.bm25s666.operator-build.v1'
            or any(receipt.get(k) != record[k] for k in ('commit', 'archive_sha256', 'build_tools', 'numpy_build_options'))
            or receipt.get('numpy_archive_sha256') != record['numpy']['archive_sha256']):
        raise VerdugoError('BM25S original build receipt mismatch')
    site = root/PACKAGE
    expected = set(record['artifact_paths'])
    if set(receipt.get('artifacts', {})) != expected or package_files(site) != expected:
        raise VerdugoError('Unexpected file in bounded BM25S profile')
    installed = {p.name.removesuffix('.dist-info').rsplit('-', 1)[0] for p in site.glob('*.dist-info')}
    if (installed != {'pip', 'numpy', 'bm25s'}
            or any(p.name not in {'pip', 'numpy', 'bm25s', '__pycache__'}
                   and not p.name.endswith('.dist-info') for p in site.iterdir())):
        raise VerdugoError('Unexpected dependency or import hook in BM25S profile')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for path in sorted(expected):
        actual = hashlib.sha256(checked(site/path, budget=64*1024*1024).read_bytes()).hexdigest()
        if actual != receipt['artifacts'][path]:
            raise VerdugoError('BM25S or NumPy installed artifact changed')
        digest.update(bytes.fromhex(actual))
    for entry in record['files']:
        if entry['installed_path']:
            actual = hashlib.sha256(checked(site/entry['installed_path']).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('BM25S installed source differs from original commit')
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = checked(Path(runtime_profile.interpreter(service)).parent.parent, directory=True)
        record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        if runtime_profile.versions(service, ['bm25s', 'numpy']) != {'bm25s':version, 'numpy':'1.26.4'}:
            raise VerdugoError('BM25S profile version differs')
        digest = hashlib.sha256(str(root).encode() + artifacts.encode())
        digest.update(checked(root/'bin/python', budget=64*1024*1024).read_bytes())
        digest.update(checked(root/'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution':distribution, 'expected':version, 'installed':version if present else None,
            'version_matches':present, 'extra_distributions':{}, 'operation':operation,
            'execution_verified':False, 'runtime_binding':binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown bounded lexical retrieval operation')
    try:
        fields(p, ('dataset', 'documents', 'query', 'k'))
    except ValueError as exc:
        raise VerdugoError('Finite JSON retrieval values required') from exc
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic integer token fixtures are supported')
    if not isinstance(p['documents'], list) or not 1 <= len(p['documents']) <= 8:
        raise VerdugoError('One to eight synthetic documents required')
    for doc in p['documents']:
        if not isinstance(doc, list) or not 1 <= len(doc) <= 16:
            raise VerdugoError('One to sixteen synthetic document tokens required')
        for token in doc: integer(token, 0, 7)
    if not isinstance(p['query'], list) or not 1 <= len(p['query']) <= 8:
        raise VerdugoError('One to eight synthetic query tokens required')
    for token in p['query']: integer(token, 0, 15)
    integer(p['k'], 1, len(p['documents']))


def reference(p):
    documents, query = p['documents'], p['query']
    n = len(documents); average = sum(map(len, documents))/n
    frequencies = Counter(token for doc in documents for token in set(doc))
    result = []
    for document in documents:
        counts = Counter(document); total = 0.0
        for token in query:
            count = counts[token]
            if count:
                df = frequencies[token]
                # Fixed BM25S Lucene variant, without the (k1+1) factor.
                total += math.log1p((n-df+0.5)/(df+0.5))*count/(count+1.5*(0.25+0.75*len(document)/average))
        result.append(total)
    return result


def verify_results(p, actual, indices, scores):
    expected = reference(p)
    close = lambda a,b: type(a) in (int,float) and math.isfinite(a) and math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-8)
    if (len(actual) != len(expected) or not all(close(x,y) for x,y in zip(actual,expected))
            or len(indices) != p['k'] or len(scores) != p['k']
            or any(type(i) is not int or not 0<=i<len(expected) for i in indices)
            or len(set(indices)) != p['k']
            or not all(close(s,expected[i]) for i,s in zip(indices,scores))
            or not all(close(s,t) for s,t in zip(scores,sorted(expected,reverse=True)[:p['k']]))):
        raise VerdugoError('Original lexical retrieval disagrees with scalar reference')
    return {'documents_scored':len(actual), 'retrieved_count':len(indices),
            'matching_documents':sum(x>0 for x in actual), 'zero_score_documents':sum(x==0 for x in actual),
            'query_token_count':len(p['query']), 'distinct_query_terms':len(set(p['query'])),
            'vocabulary_terms':len({x for doc in p['documents'] for x in doc})}


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original bounded BM25S profile is unavailable')
    import bm25s
    retriever = bm25s.BM25(k1=1.5,b=0.75,method='lucene',idf_method='lucene',dtype='float64',
                           backend='numpy',csc_backend='numpy',auto_compile=False)
    documents = [['synthetic_term_'+str(i) for i in doc] for doc in p['documents']]
    query = ['synthetic_term_'+str(i) for i in p['query']]
    retriever.index(documents,show_progress=False)
    actual = retriever.get_scores(query).tolist()
    result = retriever.retrieve([query],k=p['k'],backend_selection='numpy',n_threads=0,show_progress=False)
    counts = verify_results(p, actual, result.documents[0].tolist(), result.scores[0].tolist())
    return counts | {'original_sdk':service, 'sdk_version':SPECS[service][2], 'dataset':'demo',
            'source_commit':json.loads(CONTRACT.read_text())['commit'],
            'scope':'synthetic_fixed_lucene_bm25_counts', 'independent_scores_verified':True,
            'independent_top_k_verified':True, 'raw_text_retained':False, 'semantic_relevance_verified':False,
            'model_weights_loaded':False, 'llm_calls':0, 'autonomous_agent':False,
            'dry_run':True, 'external_calls_made':False, 'external_execution_authorized':False,
            'operator_approval_required':True, 'approvals_granted':0,
            'business_outcome_proven':False, 'live_verified':False}
