"""Optional local library adapters, dispatched by Engine (never a shell plugin).

Only bounded JSON inputs are accepted. No runtime installs, user scripts, paths,
SQL, model/pickle loading, credentials, remote URLs or automatic fallback.
The worker is a resource-limited trusted process, NOT a hostile-code sandbox.
"""
from importlib import metadata
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from .common import VerdugoError, fields, identifier, integer, encode
from . import local_extended, runtime_profile

# Primary published distribution versions; upstream source pins are a separate
# provenance inventory and must not be confused with installed Python wheels.
SPECS = {
    'trafilatura': ('html.extract', 'trafilatura', '2.3.1'),
    'scrapy': ('html.inspect', 'Scrapy', '2.20.0'),
    'duckdb': ('campaigns.aggregate', 'duckdb', '1.5.6'),
    'or-tools': ('selection.solve', 'ortools', '9.14.6206'),
    'optuna': ('threshold.optimize', 'optuna', '4.8.0'),
    'scikit-learn': ('classifier.score', 'scikit-learn', '1.8.0'),
    'catboost': ('classifier.score', 'catboost', '1.2.8'),
    'haystack': ('documents.search', 'haystack-ai', '3.5.0'),
    'great-expectations': ('data.validate', 'great-expectations', '1.24.1'),
    'evidently': ('drift.report', 'evidently', '0.7.23'),
    'presidio': ('text.redact', 'presidio-analyzer', '2.2.366'),
    'playwright': ('html.audit', 'playwright', '1.57.0'),
}
EXTRA = {'presidio': {'presidio-anonymizer': '2.2.366'},
         'catboost': {'scikit-learn': '1.8.0'}}
SPECS.update(local_extended.SPECS)
EXTRA.update(local_extended.EXTRA)
MAX_OUTPUT = 1024 * 1024
WORKER = Path(__file__).with_name('_local_worker.py')
RECIPES = Path(__file__).with_name('local_recipes.py')


def supports(service, operation):
    return service in SPECS and operation == SPECS[service][0]


def installed(service):
    operation, distribution, expected = SPECS[service]
    wanted = EXTRA.get(service, {})
    versions = runtime_profile.versions(service, [distribution, *wanted])
    version = versions[distribution]
    extras = {dist: {'installed': versions[dist], 'expected': expected}
              for dist, expected in wanted.items()}
    return {'distribution': distribution, 'expected': expected, 'installed': version,
            'version_matches': version == expected and all(
                x['installed'] == x['expected'] for x in extras.values()),
            'extra_distributions': extras, 'operation': operation,
            'execution_verified': False, 'runtime_binding': runtime_profile.binding(service)}


def inventory():
    rows = {sid: installed(sid) for sid in SPECS}
    count = sum(row['version_matches'] for row in rows.values())
    return {'state': 'available' if count == len(rows) else 'incomplete',
            'implemented': len(rows), 'matching_installations': count,
            'not_matching_or_missing': len(rows) - count, 'services': rows,
            'external_calls_made': False, 'production_certified': False,
            'note': 'Package metadata is not an execution or production certificate.'}


def finite(value, low=-1e9, high=1e9):
    if type(value) not in (float, int) or not low <= value <= high or not math.isfinite(value):
        raise VerdugoError('A finite bounded number is required')
    return value


def string(value, limit=20000):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > limit:
        raise VerdugoError('Nonempty bounded UTF-8 text required')
    if '\x00' in value:
        raise VerdugoError('NUL characters are not supported')
    return value


def matrix(value, minimum=1, nullable=False):
    if not isinstance(value, list) or not minimum <= len(value) <= 500:
        raise VerdugoError('Matrix row count is outside 1..500')
    if not isinstance(value[0], list) or not 1 <= len(value[0]) <= 20:
        raise VerdugoError('Matrix width is outside 1..20')
    width = len(value[0])
    for row in value:
        if not isinstance(row, list) or len(row) != width:
            raise VerdugoError('Ragged matrix is not supported')
        for v in row:
            if v is None and nullable:
                continue
            finite(v)
    return width


def labels(values, count, minimum_per_class=1):
    if (not isinstance(values, list) or len(values) != count or
            any(type(y) is not int or y not in (0, 1) for y in values) or
            any(values.count(c) < minimum_per_class for c in (0, 1))):
        raise VerdugoError('Binary integer labels with both classes are required')


def validate(service, operation, params):
    if not supports(service, operation):
        raise VerdugoError('Local adapter/action not implemented')
    if service in local_extended.SPECS:
        return local_extended.validate(service, operation, params)
    required = {
        'html.extract': ('dataset', 'html'),
        'html.inspect': ('dataset', 'html'),
        'html.audit': ('dataset', 'html'),
        'campaigns.aggregate': ('dataset', 'currency', 'rows'),
        'selection.solve': ('dataset', 'currency', 'budget_minor', 'items'),
        'threshold.optimize': ('dataset', 'scores', 'labels'),
        'classifier.score': ('dataset', 'train_x', 'train_y', 'score_x'),
        'documents.search': ('dataset', 'documents', 'query'),
        'data.validate': ('dataset', 'rows', 'minimum', 'maximum'),
        'drift.report': ('dataset', 'reference', 'current'),
        'text.redact': ('dataset', 'text'),
    }
    optional = {'selection.solve': ('max_items',), 'documents.search': ('top_k',)}
    fields(params, required[operation], optional.get(operation, ()))
    if params['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit demo or real dataset is required')
    if operation.startswith('html.'):
        html = string(params['html'])
        if '<!entity' in html.lower() or '<!doctype' in html.lower() and '[<' in html:
            raise VerdugoError('XML entity declarations are not supported')
    elif operation == 'campaigns.aggregate':
        if params['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('Supported currency must be explicit: MXN, USD or EUR')
        rows = params['rows']
        if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
            raise VerdugoError('Provide 1..200 campaign rows')
        for row in rows:
            fields(row, ('channel', 'spend_minor', 'revenue_minor', 'leads', 'conversions'))
            identifier(row['channel'])
            for name in ('spend_minor', 'revenue_minor'):
                integer(row[name], 0, 10**12)
            integer(row['leads'], 0, 10**6)
            integer(row['conversions'], 0, row['leads'])
    elif operation == 'selection.solve':
        if params['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('Supported currency must be explicit: MXN, USD or EUR')
        integer(params['budget_minor'], 0, 10**12)
        items = params['items']
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise VerdugoError('Provide 1..100 selection items')
        ids = set()
        for item in items:
            fields(item, ('id', 'cost_minor', 'value'))
            key = identifier(item['id'])
            if key in ids:
                raise VerdugoError('Duplicate selection item ID')
            ids.add(key)
            integer(item['cost_minor'], 1, 10**9)
            integer(item['value'], 0, 10**6)
        integer(params.get('max_items', len(items)), 0, len(items))
    elif operation == 'threshold.optimize':
        scores = params['scores']
        if not isinstance(scores, list) or not 10 <= len(scores) <= 500:
            raise VerdugoError('Provide 10..500 threshold-selection scores')
        for score in scores:
            finite(score, 0, 1)
        labels(params['labels'], len(scores))
    elif operation == 'classifier.score':
        width = matrix(params['train_x'], 20)
        if matrix(params['score_x']) != width:
            raise VerdugoError('Training and scoring widths do not match')
        labels(params['train_y'], len(params['train_x']), minimum_per_class=5)
    elif operation == 'documents.search':
        documents = params['documents']
        if not isinstance(documents, list) or not 1 <= len(documents) <= 50:
            raise VerdugoError('Provide 1..50 documents')
        ids = set()
        for doc in documents:
            fields(doc, ('id', 'content'))
            key = identifier(doc['id'])
            if key in ids:
                raise VerdugoError('Duplicate document ID')
            ids.add(key)
            string(doc['content'], 4000)
        string(params['query'], 500)
        integer(params.get('top_k', 5), 1, 10)
    elif operation == 'data.validate':
        matrix(params['rows'], nullable=True)
        finite(params['minimum'])
        finite(params['maximum'])
        if params['minimum'] > params['maximum']:
            raise VerdugoError('Validation minimum exceeds maximum')
    elif operation == 'drift.report':
        if matrix(params['reference'], 30) != matrix(params['current'], 30):
            raise VerdugoError('Drift dataset widths do not match')
    elif operation == 'text.redact':
        string(params['text'], 16000)


def preflight(service, operation, cfg):
    if not supports(service, operation):
        raise VerdugoError('Unsupported local operation')
    expected = SPECS[service][2]
    if cfg.get('version') != expected:
        raise VerdugoError('Local adapter requires explicit tested distribution version: ' + expected)
    if cfg.get('runtime_reviewed') is not True:
        raise VerdugoError('Local resource and privacy review required: ' + service)
    integer(cfg.get('timeout_seconds', 45), 5, 120)
    if service == 'playwright':
        browser_dir = cfg.get('browser_path')
        if not isinstance(browser_dir, str) or not Path(browser_dir).is_absolute():
            raise VerdugoError('An explicit administrator-owned browser_path is required')
    state = installed(service)
    if not state['version_matches']:
        raise VerdugoError('Missing or mismatched local distribution: ' + state['distribution'])
    return state


def implementation_digest():
    h = hashlib.sha256()
    for path in (Path(__file__), WORKER, RECIPES, Path(local_extended.__file__),
                 Path(runtime_profile.__file__), runtime_profile.PROBE):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def build(service, operation, params, cfg):
    validate(service, operation, params)
    state = preflight(service, operation, cfg)
    public = {'service': service, 'operation': operation, 'params': params,
              'transport': 'local-library', 'distribution': state['distribution'],
              'version': state['installed'], 'runtime_binding': state['runtime_binding'],
              'extra_distributions': state['extra_distributions'],
              'implementation_sha256': implementation_digest(),
              'timeout_seconds': cfg.get('timeout_seconds', 45),
              'browser_binding': hashlib.sha256(str(cfg.get('browser_path', '')).encode()).hexdigest(),
              'network_policy': 'no provider calls; Python socket audit guard',
              'boundary': 'trusted local worker, not hostile-code isolation'}
    return {'public': public, 'mutates': False, 'secret_values': []}


def execute(request, cfg):
    """Run only the fixed first-party worker, with no shell or inherited secrets."""
    public = request['public']
    current = build(public['service'], public['operation'], public['params'], cfg)
    if current['public'] != public:
        raise VerdugoError('Local implementation/configuration changed after planning')
    if os.name != 'posix':
        raise VerdugoError('Local worker requires the tested POSIX process controls')
    payload = encode(public).encode('utf-8')
    with tempfile.TemporaryDirectory(prefix='verdugo-local-') as work:
        env = {'PATH': os.defpath, 'HOME': work, 'TMPDIR': work, 'LANG': 'C.UTF-8',
               'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
               'NUMEXPR_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1',
               'MALLOC_ARENA_MAX': '2', 'DO_NOT_TRACK': '1',
               'HAYSTACK_TELEMETRY_ENABLED': 'False', 'OTEL_SDK_DISABLED': 'true',
               'GX_ANALYTICS_ENABLED': 'False', 'GE_USAGE_STATS': 'False',
               'ANONYMIZED_TELEMETRY': 'False',
               'RUNTIME__DLTHUB_TELEMETRY': 'false', 'RUNTIME__ENABLE_RUNTIME_TRACE': 'false',
               'RAGAS_DO_NOT_TRACK': 'true', 'LANGSMITH_TRACING': 'false',
               'LANGCHAIN_TRACING_V2': 'false', 'MLFLOW_ENABLE_ASYNC_LOGGING': 'false'}
        if public['service'] == 'playwright':
            browser_dir = cfg.get('browser_path')
            if not isinstance(browser_dir, str) or not Path(browser_dir).is_absolute():
                raise VerdugoError('An explicit administrator-owned browser_path is required')
            env['PLAYWRIGHT_BROWSERS_PATH'] = browser_dir
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            proc = subprocess.Popen([runtime_profile.interpreter(public['service']), '-I', str(WORKER)],
                stdin=subprocess.PIPE, stdout=out, stderr=err,
                cwd=work, env=env, start_new_session=True, close_fds=True)
            try:
                proc.communicate(payload, timeout=public['timeout_seconds'])
            except subprocess.TimeoutExpired as exc:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                raise VerdugoError('Local operation exceeded its time budget') from exc
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            out.seek(0)
            raw = out.read(MAX_OUTPUT + 1)
            if len(raw) > MAX_OUTPUT:
                raise VerdugoError('Local result exceeded the output budget')
            if proc.returncode:
                err.seek(0)
                error_type = err.read(128).decode('ascii', errors='ignore').strip()
                detail = error_type if error_type.isalpha() and len(error_type) <= 60 else 'WorkerError'
                raise VerdugoError('Local library operation failed (' + detail + '); no external effect was requested')
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise VerdugoError('Local worker returned an invalid result') from exc
            if not isinstance(value, dict) or value.get('ok') is not True:
                raise VerdugoError('Local worker did not return a successful result')
            if value.get('service') != public['service'] or value.get('version') != public['version']:
                raise VerdugoError('Local result provenance mismatch')
            return value
