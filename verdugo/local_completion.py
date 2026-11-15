"""Bounded native transformations for the remaining v0.21 library profiles.

Every operation runs the original distribution. No model calls, browser
navigation, external database connections or retrieval are performed here.
"""
import re

from .common import VerdugoError, fields, identifier, integer

SPECS = {
    'vanna': ('campaigns.query', 'vanna', '2.0.2'),
    'trendspyg': ('traffic.normalize', 'trendspyg', '1.9.0'),
    'youtube-comment-downloader': ('comments.inspect', 'youtube-comment-downloader', '0.1.84'),
    'comtradeapicall': ('groups.expand', 'comtradeapicall', '1.4.0'),
    'browser-use': ('domains.evaluate', 'browser-use', '1.0.4'),
    'storm': ('citations.inspect', 'knowledge-storm', '1.1.1'),
    'dbt': ('campaigns.materialize', 'dbt-core', '1.12.7'),
    'c2pa': ('manifest.inspect', 'c2pa-python', '0.39.0'),
    'a2a': ('tasks.snapshot', 'a2a-sdk', '1.3.0'),
    'gpt-researcher': ('passages.rank', 'gpt-researcher', '0.17.0'),
    'meridian': ('media.transform', 'google-meridian', '2.2.0'),
    'tfcausalimpact': ('impact.estimate', 'tfcausalimpact', '0.0.19'),
}
PROFILES = {sid: 'UTILITY021' for sid in SPECS}
PROFILES.update({'browser-use': 'BROWSER021', 'storm': 'STORM021'})
PROFILES['dbt'] = 'DBT021'
PROFILES['a2a'] = 'A2A021'
PROFILES['gpt-researcher'] = 'RESEARCH021'
PROFILES['meridian'] = 'MERIDIAN021'
PROFILES['tfcausalimpact'] = 'CAUSAL021'
EXTRA = {'dbt': {'dbt-duckdb': '1.11.1', 'duckdb': '2.0.0'}}
EXTRA['tfcausalimpact'] = {'tensorflow': '2.18.0', 'tensorflow-probability': '0.25.0', 'tf-keras': '2.18.0'}


def _items(value, maximum=100):
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise VerdugoError('A bounded nonempty list is required')
    return value


def validate(service, operation, p):
    from .local_runtime import string, validate as base
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported completion operation')
    if service in ('vanna', 'dbt'):
        return base('duckdb', 'campaigns.aggregate', p)
    required = {'trendspyg': ('traffic',), 'youtube-comment-downloader': ('threads',),
                'comtradeapicall': ('groups', 'selection'), 'browser-use': ('allowed', 'hosts'),
                'storm': ('text', 'reference_count'), 'c2pa': ('secret_text',),
                'a2a': ('tasks',), 'gpt-researcher': ('query', 'passages'),
                'meridian': ('media', 'alpha', 'max_lag', 'half_saturation', 'slope'),
                'tfcausalimpact': ('outcome', 'control', 'intervention_index', 'assumptions_reviewed')}[service]
    try:
        fields(p, ('dataset', *required))
    except (ValueError, TypeError) as exc:
        raise VerdugoError('Finite JSON values are required') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')
    if service == 'tfcausalimpact':
        import math
        if p['assumptions_reviewed'] is not True:
            raise VerdugoError('Explicit review of causal assumptions is required')
        y, x = _items(p['outcome'], 100), _items(p['control'], 100)
        if len(y) != len(x) or len(y) < 30:
            raise VerdugoError('30..100 paired observations required')
        integer(p['intervention_index'], 20, len(y) - 5)
        for series in (y, x):
            for value in series:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e9:
                    raise VerdugoError('Finite bounded observations required')
            if len(set(series[:p['intervention_index']])) < 3:
                raise VerdugoError('Pre-period variation is required')
    elif service == 'meridian':
        import math
        for value, lower, upper in [(x, 0, 1e9) for x in _items(p['media'], 100)] + [
                (p['alpha'], 0, 1), (p['half_saturation'], 0.001, 1e9), (p['slope'], 0.01, 10)]:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
                raise VerdugoError('Finite bounded media and transformation parameters required')
        integer(p['max_lag'], 0, min(20, len(p['media']) - 1))
    elif service == 'gpt-researcher':
        string(p['query'], 500)
        for passage in _items(p['passages'], 20):
            string(passage, 1000)
    elif service == 'c2pa':
        import base64
        import binascii
        string(p['secret_text'], 28000)
        try:
            raw = base64.b64decode(p['secret_text'], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise VerdugoError('A bounded base64 PNG is required') from exc
        if not 33 <= len(raw) <= 20000 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise VerdugoError('Only supplied PNG bytes up to 20000 bytes are supported')
        width, height = int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')
        if not 1 <= width <= 4096 or not 1 <= height <= 4096:
            raise VerdugoError('PNG dimensions exceed the inspection budget')
    elif service == 'a2a':
        seen = set()
        for row in _items(p['tasks'], 50):
            fields(row, ('id', 'state'))
            identifier(row['id'])
            if row['id'] in seen or row['state'] not in ('submitted', 'working', 'completed', 'failed', 'canceled', 'input_required', 'rejected', 'auth_required'):
                raise VerdugoError('Distinct tasks with supported A2A states are required')
            seen.add(row['id'])
    elif service == 'trendspyg':
        for value in _items(p['traffic']):
            if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3}){0,3}(?:\.[0-9]{1,3})?[KMB]?\+?|[0-9]{1,12}(?:\.[0-9]{1,3})?[KMB]?\+?', value):
                raise VerdugoError('Supported nonnegative traffic notation required')
    elif service == 'storm':
        string(p['text'], 16000)
        integer(p['reference_count'], 0, 1000)
        if any(len(x) > 6 for x in re.findall(r'\[(\d+)\]', p['text'])):
            raise VerdugoError('Citation index is too long')
    elif service == 'comtradeapicall':
        names = []
        for row in _items(p['groups'], 20):
            fields(row, ('id', 'countries'))
            name = row['id']
            if not isinstance(name, str) or not re.fullmatch('[A-Z]{2,12}', name):
                raise VerdugoError('Uppercase group identifiers required')
            names.append(name)
            for code in _items(row['countries'], 50):
                integer(code, 1, 999)
            if len(set(row['countries'])) != len(row['countries']):
                raise VerdugoError('Duplicate country in group')
        if len(set(names)) != len(names):
            raise VerdugoError('Duplicate group identifier')
        selection = _items(p['selection'], 20)
        if any(name not in names for name in selection) or len(set(selection)) != len(selection):
            raise VerdugoError('Choose distinct supplied groups')
    elif service == 'browser-use':
        for key in ('allowed', 'hosts'):
            for host in _items(p[key], 50):
                if not isinstance(host, str) or len(host) > 253 or not re.fullmatch(r'(?:\*\.)?[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}', host):
                    raise VerdugoError('Plain lowercase domain patterns required')
                if key == 'hosts' and '*' in host:
                    raise VerdugoError('Candidate hosts cannot be patterns')
    else:
        ids = set()
        for thread in _items(p['threads'], 50):
            fields(thread, ('id', 'likes', 'replies'))
            key = identifier(thread['id'])
            if key in ids:
                raise VerdugoError('Duplicate comment identifier')
            ids.add(key)
            integer(thread['likes'], 0, 10**9)
            integer(thread['replies'], 0, 10**6)


def run(service, p):
    if service == 'meridian':
        from meridian import backend
        from meridian.model.adstock_hill import AdstockTransformer, HillTransformer
        import numpy as np
        media = backend.to_tensor([[[x] for x in p['media']]])
        adstock = AdstockTransformer(backend.to_tensor([p['alpha']]), p['max_lag'], len(p['media'])).forward(media)
        hill = HillTransformer(backend.to_tensor([p['half_saturation']]), backend.to_tensor([p['slope']])).forward(adstock)
        return {'adstock': np.asarray(adstock).reshape(-1).tolist(), 'saturation': np.asarray(hill).reshape(-1).tolist(),
                'parameters_fitted': False, 'causality_established': False, 'scope': 'original normalized geometric adstock followed by Hill; supplied parameters'}
    if service == 'tfcausalimpact':
        import numpy as np
        import tensorflow as tf
        from causalimpact import CausalImpact
        np.random.seed(7); tf.random.set_seed(7)
        n, split = len(p['outcome']), p['intervention_index']
        fit = CausalImpact(np.column_stack([p['outcome'], p['control']]), [0, split - 1], [split, n - 1],
                          model_args={'fit_method': 'vi'})
        keys = ('actual', 'predicted', 'predicted_lower', 'predicted_upper', 'abs_effect', 'abs_effect_lower', 'abs_effect_upper')
        summary = {period: {key: float(fit.summary_data.loc[key, period]) for key in keys}
                   for period in ('average', 'cumulative')}
        if not all(np.isfinite(v) for r in summary.values() for v in r.values()):
            raise ValueError('Non-finite model estimate')
        return {'summary': summary, 'pre_observations': split, 'post_observations': n - split,
                'method': 'original variational inference, 200 optimization steps, 100 posterior draws',
                'assumptions_reviewed': True, 'causality_established': False, 'convergence_certified': False,
                'scope': 'conditional statistical estimate; control must be unaffected by intervention; no automatic business attribution'}
    if service == 'gpt-researcher':
        from gpt_researcher.context.lexical import bm25_scores
        scores = bm25_scores(p['query'], p['passages'])
        return {'scores': scores, 'ranking': sorted(range(len(scores)), key=lambda i: (-scores[i], i)),
                'retrieved_sources': 0, 'llm_calls': 0, 'scope': 'local BM25 lexical relevance of supplied passages; not factual verification'}
    if service == 'c2pa':
        import base64
        import io
        import json
        import c2pa
        # Remote assets and OCSP are disabled; the operation neither signs nor
        # grants trust to a supplied signer. Native diagnostics are counts only.
        with c2pa.Context.from_dict({'verify': {'remote_manifest_fetch': False, 'ocsp_fetch': False},
                                     'core': {'allowed_network_hosts': []}}) as context:
            reader = c2pa.Reader.try_create('image/png', io.BytesIO(base64.b64decode(p['secret_text'])), context=context)
            if reader is None:
                return {'embedded_manifest_found': False, 'manifests': 0, 'native_sdk_version': c2pa.sdk_version(),
                        'authenticity_certified': False, 'remote_manifest_fetch': False, 'ocsp_fetch': False}
            with reader:
                data = json.loads(reader.json())
            manifests = data.get('manifests')
            if not isinstance(manifests, dict) or len(manifests) > 100:
                raise ValueError('Unexpected manifest structure')
            diagnostics = data.get('validation_results', {}).get('activeManifest', {})
            return {'embedded_manifest_found': True, 'manifests': len(manifests),
                    'active_manifest_diagnostics': {k: len(diagnostics.get(k, [])) for k in ('success', 'failure', 'informational')},
                    'native_validation_state': data.get('validation_state'), 'native_sdk_version': c2pa.sdk_version(),
                    'authenticity_certified': False, 'remote_manifest_fetch': False, 'ocsp_fetch': False}
    if service == 'a2a':
        import asyncio
        from collections import Counter
        from a2a.types import a2a_pb2
        from a2a.server.context import ServerCallContext
        from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
        async def snapshot():
            store = InMemoryTaskStore()
            context = ServerCallContext(tenant='verdugo-local')
            for row in p['tasks']:
                task = a2a_pb2.Task(id=row['id'], context_id='local-snapshot', status=a2a_pb2.TaskStatus(
                    state=a2a_pb2.TaskState.Value('TASK_STATE_' + row['state'].upper())))
                await store.save(task, context)
            tasks = [await store.get(row['id'], context) for row in p['tasks']]
            if any(task is None for task in tasks):
                raise ValueError('Native task store did not preserve the snapshot')
            counts = Counter(a2a_pb2.TaskState.Name(task.status.state).removeprefix('TASK_STATE_').lower() for task in tasks)
            return {'tasks': len(tasks), 'states': dict(sorted(counts.items())),
                    'agent_invoked': False, 'scope': 'supplied task states in ephemeral original SDK store'}
        return asyncio.run(snapshot())
    if service == 'dbt':
        import csv
        import json
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        import duckdb
        Path('seeds').mkdir(); Path('models').mkdir()
        with Path('seeds/campaigns.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['channel', 'spend_minor', 'revenue_minor', 'leads', 'conversions'])
            writer.writeheader(); writer.writerows(p['rows'])
        Path('dbt_project.yml').write_text('name: verdugo_analysis\nversion: "1.0"\nconfig-version: 2\nprofile: verdugo_analysis\nmodel-paths: [models]\nseed-paths: [seeds]\nmodels:\n  verdugo_analysis:\n    +materialized: table\n')
        Path('profiles.yml').write_text('config:\n  send_anonymous_usage_stats: false\nverdugo_analysis:\n  target: local\n  outputs:\n    local:\n      type: duckdb\n      path: analysis.duckdb\n      threads: 1\n')
        Path('models/totals.sql').write_text("SELECT channel, SUM(spend_minor) AS spend_minor, SUM(revenue_minor) AS revenue_minor, SUM(leads) AS leads, SUM(conversions) AS conversions FROM {{ ref('campaigns') }} GROUP BY channel")
        # No caller-selected paths, SQL, Jinja, plugins or command flags.
        with tempfile.TemporaryFile() as output:
            result = subprocess.run([sys.executable, '-m', 'dbt.cli.main', 'build', '--profiles-dir', '.',
                                     '--project-dir', '.', '--no-use-colors', '--no-send-anonymous-usage-stats',
                                     '--no-partial-parse'], stdout=output, stderr=output, timeout=90, check=False)
            if result.returncode:
                raise ValueError('Fixed dbt build failed')
        results = json.loads(Path('target/run_results.json').read_text())['results']
        if len(results) != 2 or any(r['status'] != 'success' for r in results):
            raise ValueError('dbt did not build the seed and model')
        with duckdb.connect('analysis.duckdb', read_only=True) as db:
            rows = db.execute('SELECT channel, spend_minor, revenue_minor, leads, conversions FROM totals ORDER BY channel').fetchall()
        return {'rows': [dict(zip(['channel', 'spend_minor', 'revenue_minor', 'leads', 'conversions'], row)) for row in rows],
                'currency': p['currency'], 'dbt_nodes_succeeded': len(results),
                'database_scope': 'temporary_supplied_rows', 'external_warehouse_modified': False}
    if service == 'vanna':
        import asyncio
        import sqlite3
        from vanna.integrations.sqlite.sql_runner import SqliteRunner
        from vanna.capabilities.sql_runner import RunSqlToolArgs
        # Fixed ephemeral schema and SQL. Caller strings are bound values only.
        with sqlite3.connect('analysis.sqlite') as db:
            db.execute('CREATE TABLE campaigns(channel TEXT, spend_minor INTEGER, revenue_minor INTEGER, leads INTEGER, conversions INTEGER)')
            db.executemany('INSERT INTO campaigns VALUES (?,?,?,?,?)',
                           [(r['channel'], r['spend_minor'], r['revenue_minor'], r['leads'], r['conversions']) for r in p['rows']])
        query = ('SELECT channel, SUM(spend_minor) AS spend_minor, SUM(revenue_minor) AS revenue_minor, '
                 'SUM(leads) AS leads, SUM(conversions) AS conversions FROM campaigns GROUP BY channel ORDER BY channel')
        result = asyncio.run(SqliteRunner('analysis.sqlite').run_sql(RunSqlToolArgs(sql=query), None))
        return {'rows': result.to_dict(orient='records'), 'currency': p['currency'],
                'llm_calls': 0, 'sql_generated': False, 'database_scope': 'temporary_supplied_rows'}
    if service == 'trendspyg':
        from trendspyg.utils import _parse_traffic_to_min
        values = [_parse_traffic_to_min(value) for value in p['traffic']]
        return {'minimum_volumes': values, 'count': len(values), 'feed_fetched': False,
                'scope': 'lower bounds parsed from supplied volume labels; not measured search volume'}
    if service == 'comtradeapicall':
        from comtradeapicall.GroupCalc import build_group_to_country_lookup, parse_input
        raw = {'results': [{'GroupID': r['id'], 'GroupDefinition': r['countries']} for r in p['groups']]}
        lookup = build_group_to_country_lookup(raw)
        groups = parse_input(','.join(p['selection']), lookup)
        return {'groups': [{'label': name, 'countries': [int(code) for code in codes]} for name, codes in groups],
                'trade_data_fetched': False, 'classification_source': 'operator_supplied'}
    if service == 'youtube-comment-downloader':
        from youtube_comment_downloader import YoutubeCommentDownloader
        # Supply the native nested renderer shape, containing only bounded counts.
        payload = {'contents': [{'commentThreadRenderer': {'comment': {'commentRenderer': {
            'commentId': row['id'], 'likeCount': row['likes'], 'replyCount': row['replies']}}}} for row in p['threads']]}
        rows = list(YoutubeCommentDownloader.search_dict(payload, 'commentRenderer'))
        return {'comments_in_input': len(rows), 'likes_in_input': sum(r['likeCount'] for r in rows),
                'replies_in_input': sum(r['replyCount'] for r in rows), 'video_fetched': False,
                'scope': 'supplied comment metadata only; no comment text retained'}
    if service == 'browser-use':
        from browser_use.domains import DomainRules
        rules = DomainRules.of(allowed=p['allowed'], block_ips=True)
        decisions = [rules.blocked('https://' + host + '/') is None for host in p['hosts']]
        return {'allowed_by_native_rules': decisions, 'allowed_count': sum(decisions),
                'browser_launched': False, 'navigation_performed': False, 'security_boundary_certified': False}
    if service == 'storm':
        from knowledge_storm.utils import ArticleTextProcessing
        indices = ArticleTextProcessing.parse_citation_indices(p['text'])
        return {'citation_indices': indices, 'out_of_range': sorted({i for i in indices if not 1 <= i <= p['reference_count']}),
                'text_without_citations': ArticleTextProcessing.remove_citations(p['text']),
                'sources_retrieved': False, 'citations_fact_checked': False, 'llm_calls': 0,
                'scope': 'native numeric citation parsing; grouped citations are removed but not indexed upstream'}
    raise ValueError('Unsupported completion recipe')
