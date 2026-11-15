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
from . import local_pilot666, local_executive666, local_reasoning666, local_flow666, local_planning666, local_volt666, local_manus666, local_memory666, local_monty666, local_browserstate666, local_dispatch666, local_trace666, local_toolaudit666, objectives
from . import local_extended, local_analytics, local_research, local_interop, local_knowledge, local_data, local_native, local_cli, local_content, local_pycli, local_planning, local_completion, local_source, local_r, local_database, local_native_tools, local_media, local_images, local_lastnode, local_owned_http, runtime_profile

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
SPECS.update(local_analytics.SPECS)
EXTRA.update(local_analytics.EXTRA)
SPECS.update(local_research.SPECS)
EXTRA.update(local_research.EXTRA)
SPECS.update(local_interop.SPECS)
EXTRA.update(local_interop.EXTRA)
SPECS.update(local_knowledge.SPECS)
EXTRA.update(local_knowledge.EXTRA)
SPECS.update(local_data.SPECS)
SPECS.update(local_native.SPECS)
SPECS.update(local_cli.SPECS)
SPECS.update(local_content.SPECS)
SPECS.update(local_pycli.SPECS)
SPECS.update(local_planning.SPECS)
SPECS.update(local_source.SPECS)
SPECS.update(local_r.SPECS)
SPECS.update(local_database.SPECS)
SPECS.update(local_native_tools.SPECS)
SPECS.update(local_media.SPECS)
SPECS.update(local_images.SPECS)
SPECS.update(local_lastnode.SPECS)
SPECS.update(local_owned_http.SPECS)
SPECS.update(local_completion.SPECS)
SPECS.update(local_pilot666.SPECS)
SPECS.update(local_executive666.SPECS)
SPECS.update(local_reasoning666.SPECS)
SPECS.update(local_flow666.SPECS)
SPECS.update(local_planning666.SPECS)
SPECS.update(local_volt666.SPECS)
SPECS.update(local_manus666.SPECS)
SPECS.update(local_memory666.SPECS)
SPECS.update(local_monty666.SPECS)
SPECS.update(local_browserstate666.SPECS)
SPECS.update(local_dispatch666.SPECS)
SPECS.update(local_trace666.SPECS)
SPECS.update(local_toolaudit666.SPECS)
EXTRA.update(local_completion.EXTRA)
EXTRA.update(local_planning.EXTRA)
EXTRA.update(local_content.EXTRA)
MAX_OUTPUT = 1024 * 1024
WORKER = Path(__file__).with_name('_local_worker.py')
RECIPES = Path(__file__).with_name('local_recipes.py')


def supports(service, operation):
    return service in SPECS and operation == SPECS[service][0]


def installed(service):
    operation, distribution, expected = SPECS[service]
    if service in local_browserstate666.SPECS:
        return local_browserstate666.runtime_state(service)
    if service in local_monty666.SPECS:
        return local_monty666.runtime_state(service)
    if service in local_memory666.SPECS:
        return local_memory666.runtime_state(service)
    if service in local_volt666.SPECS:
        return local_volt666.runtime_state(service)
    if service in local_owned_http.SPECS:
        return local_owned_http.runtime_state(service)
    if service in local_lastnode.SPECS:
        return local_lastnode.runtime_state(service)
    if service in local_images.SPECS:
        return local_images.runtime_state(service)
    if service in local_media.SPECS:
        return local_media.runtime_state(service)
    if service in local_native_tools.SPECS:
        return local_native_tools.runtime_state(service)
    if service in local_database.SPECS:
        return local_database.runtime_state(service)
    if service in local_r.SPECS:
        return local_r.runtime_state(service)
    if service in local_source.SPECS:
        return local_source.runtime_state(service)
    if service in local_cli.SPECS:
        return local_cli.runtime_state(service)
    if service in local_native.SPECS:
        return local_native.runtime_state(service)
    if service in local_data.SPECS:
        try:
            local_data.source_bytes(service)
            present = True
        except (OSError, ValueError):
            present = False
        return {'distribution': distribution, 'distribution_kind': 'bundled-public-data',
                'expected': expected, 'installed': expected if present else None,
                'version_matches': present, 'extra_distributions': {}, 'operation': operation,
                'execution_verified': False, 'runtime_binding': runtime_profile.binding(service)}
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
    if service in local_toolaudit666.SPECS:
        return local_toolaudit666.validate(service, operation, params)
    if service in local_trace666.SPECS:
        return local_trace666.validate(service, operation, params)
    if service in local_dispatch666.SPECS:
        return local_dispatch666.validate(service, operation, params)
    if not supports(service, operation):
        raise VerdugoError('Local adapter/action not implemented')
    if service in local_pilot666.SPECS:
        return local_pilot666.validate(service, operation, params)
    if service in local_executive666.SPECS:
        return local_executive666.validate(service, operation, params)
    if service in local_reasoning666.SPECS:
        return local_reasoning666.validate(service, operation, params)
    if service in local_volt666.SPECS:
        return local_volt666.validate(service, operation, params)
    if service in local_browserstate666.SPECS:
        return local_browserstate666.validate(service, operation, params)
    if service in local_monty666.SPECS:
        return local_monty666.validate(service, operation, params)
    if service in local_memory666.SPECS:
        return local_memory666.validate(service, operation, params)
    if service in local_manus666.SPECS:
        return local_manus666.validate(service, operation, params)
    if service in local_planning666.SPECS:
        return local_planning666.validate(service, operation, params)
    if service in local_flow666.SPECS:
        return local_flow666.validate(service, operation, params)
    if service in local_owned_http.SPECS:
        return local_owned_http.validate(service, operation, params)
    if service in local_lastnode.SPECS:
        return local_lastnode.validate(service, operation, params)
    if service in local_images.SPECS:
        return local_images.validate(service, operation, params)
    if service in local_media.SPECS:
        return local_media.validate(service, operation, params)
    if service in local_native_tools.SPECS:
        return local_native_tools.validate(service, operation, params)
    if service in local_database.SPECS:
        return local_database.validate(service, operation, params)
    if service in local_r.SPECS:
        return local_r.validate(service, operation, params)
    if service in local_source.SPECS:
        return local_source.validate(service, operation, params)
    if service in local_completion.SPECS:
        return local_completion.validate(service, operation, params)
    if service in local_planning.SPECS:
        return local_planning.validate(service, operation, params)
    if service in local_pycli.SPECS:
        return local_pycli.validate(service, operation, params)
    if service in local_content.SPECS:
        return local_content.validate(service, operation, params)
    if service in local_cli.SPECS:
        return local_cli.validate(service, operation, params)
    if service in local_native.SPECS:
        return local_native.validate(service, operation, params)
    if service in local_extended.SPECS:
        return local_extended.validate(service, operation, params)
    if service in local_analytics.SPECS:
        return local_analytics.validate(service, operation, params)
    if service in local_research.SPECS:
        return local_research.validate(service, operation, params)
    if service in local_interop.SPECS:
        return local_interop.validate(service, operation, params)
    if service in local_knowledge.SPECS:
        return local_knowledge.validate(service, operation, params)
    if service in local_data.SPECS:
        return local_data.validate(service, operation, params)
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
    for path in (Path(local_pilot666.__file__), local_pilot666.CONTRACT, Path(objectives.__file__),
                 Path(local_executive666.__file__), local_executive666.CONTRACT,
                 Path(local_reasoning666.__file__), local_reasoning666.CONTRACT,
                 Path(local_flow666.__file__), local_flow666.CONTRACT,
                 Path(local_planning666.__file__), local_planning666.CONTRACT,
                 Path(local_volt666.__file__), local_volt666.CONTRACT, local_volt666.WORKER,
                 Path(local_manus666.__file__), local_manus666.CONTRACT,
                 Path(local_monty666.__file__), local_monty666.CONTRACT,
                 Path(local_dispatch666.__file__), local_dispatch666.CONTRACT,
                 Path(local_trace666.__file__), local_trace666.CONTRACT,
                 Path(local_toolaudit666.__file__), local_toolaudit666.CONTRACT,
                 Path(local_browserstate666.__file__), local_browserstate666.CONTRACT, local_browserstate666.GUARD,
                 Path(local_memory666.__file__), local_memory666.CONTRACT, local_memory666.WORKER):
        h.update(path.read_bytes())
    for path in (Path(__file__), WORKER, RECIPES, Path(local_extended.__file__), Path(local_analytics.__file__), Path(local_research.__file__), Path(local_interop.__file__), Path(local_knowledge.__file__), Path(local_data.__file__), Path(local_native.__file__), local_native.WORKER, Path(local_cli.__file__), Path(local_content.__file__), Path(local_pycli.__file__), Path(local_planning.__file__), Path(local_completion.__file__), Path(local_source.__file__), Path(local_r.__file__), local_r.WORKER, local_r.CONTRACT, Path(local_database.__file__), Path(local_native_tools.__file__), local_native_tools.CONTRACT, Path(local_media.__file__), local_media.CONTRACT, Path(local_images.__file__), Path(local_lastnode.__file__), local_lastnode.CONTRACT, local_lastnode.GUARD, local_lastnode.MCP_WORKER, Path(local_owned_http.__file__), local_owned_http.WORKER, local_owned_http.PY_WORKER,
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
               'TF_NUM_INTRAOP_THREADS': '1', 'TF_NUM_INTEROP_THREADS': '1', 'CUDA_VISIBLE_DEVICES': '-1',
               'MALLOC_ARENA_MAX': '2', 'DO_NOT_TRACK': '1',
               'HAYSTACK_TELEMETRY_ENABLED': 'False', 'OTEL_SDK_DISABLED': 'true',
               'GX_ANALYTICS_ENABLED': 'False', 'GE_USAGE_STATS': 'False',
               'ANONYMIZED_TELEMETRY': 'False',
               'RUNTIME__DLTHUB_TELEMETRY': 'false', 'RUNTIME__ENABLE_RUNTIME_TRACE': 'false',
               'RAGAS_DO_NOT_TRACK': 'true', 'LANGSMITH_TRACING': 'false',
               'LANGCHAIN_TRACING_V2': 'false', 'MLFLOW_ENABLE_ASYNC_LOGGING': 'false'}
        env.update(FEAST_USAGE='False', PYWIKIBOT_NO_USER_CONFIG='2',
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
        if public['service'] in local_browserstate666.SPECS:
            env['NODE_OPTIONS'] = '--require ' + str(local_browserstate666.GUARD)
        if public['service'] == 'langroid':
            env['TIKTOKEN_CACHE_DIR'] = str(local_reasoning666.tokenizer_directory())
        if public['service'] in local_memory666.SPECS:
            env[local_memory666.ENV] = str(local_memory666.root())
        if public['service'] in local_volt666.SPECS:
            env[local_volt666.ENV] = str(local_volt666.root())
        if public['service'] in local_owned_http.SPECS:
            env[local_owned_http.ENV] = str(local_owned_http.root())
        if public['service'] in local_lastnode.SPECS:
            env[local_lastnode.ENV] = str(local_lastnode.root())
        if public['service'] in local_images.SPECS:
            env[local_images.ENV] = str(local_images.root())
        if public['service'] in local_media.SPECS:
            env[local_media.ENV] = str(local_media.root())
        if public['service'] in local_native_tools.SPECS:
            env[local_native_tools.ENV] = str(local_native_tools.root())
        if public['service'] in local_database.SPECS:
            env[local_database.ENV] = str(local_database.root())
            env[local_database.LOOPBACK_ENV] = '1' if local_database.loopback() else '0'
        if public['service'] in local_r.SPECS:
            env[local_r.ENV] = str(local_r.root())
        if public['service'] in local_cli.SPECS:
            env[local_cli.ENV] = str(local_cli.root())
        if public['service'] in local_native.SPECS:
            env[local_native.ENV] = str(local_native.root())
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
