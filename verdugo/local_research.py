"""Further bounded data, language and interoperability operations.

Original libraries run inside the existing private worker, never a second
orchestrator. Temporary catalogs and feature stores disappear after each call.
"""
import math

SPECS = {
    'advertools': ('links.summarize', 'advertools', '0.18.0'),
    'pywikibot': ('wiki.clean', 'pywikibot', '11.10.0'),
    'splink': ('records.link', 'splink', '5.0.0'),
    'iceberg': ('table.snapshot', 'pyiceberg', '0.12.0'),
    'feast': ('features.materialize', 'feast', '0.68.0'),
    'openlineage': ('lineage.serialize', 'openlineage-python', '1.55.0'),
    'causalml': ('effect.estimate', 'causalml', '0.18.0'),
    'ydata-profiling': ('data.profile', 'ydata-profiling', '4.18.4'),
    'opendp': ('privacy.calibrate', 'opendp', '0.16.0'),
    'flaml': ('regression.search', 'flaml', '2.8.0'),
    'recommenders': ('ranking.evaluate', 'recommenders', '1.2.1'),
    'vowpal': ('regression.online', 'vowpalwabbit', '9.11.9'),
    'py-ecomplexity': ('trade.structure', 'ecomplexity', '0.5.3'),
    'osmnx': ('routes.shortest', 'osmnx', '2.1.1'),
    'mesa': ('capacity.simulate', 'mesa', '3.5.2'),
    'langchain': ('text.chunk', 'langchain-text-splitters', '1.1.3'),
    'pydantic-ai': ('messages.inspect', 'pydantic-ai-slim', '2.68.0'),
    'dspy': ('answers.evaluate', 'dspy', '3.5.0'),
    'docling': ('html.document', 'docling', '2.150.1'),
    'pipecat': ('audio.mix', 'pipecat-ai', '1.16.0'),
    'whisper': ('audio.features', 'openai-whisper', '20250625'),
    'financetoolkit': ('liquidity.calculate', 'financetoolkit', '2.3.4'),
    'a2a-python': ('artifact.serialize', 'a2a-sdk', '1.3.0'),
    'mcp-python-sdk': ('result.serialize', 'mcp', '2.3.0'),
}
LANGUAGE = {'pydantic-ai', 'dspy', 'docling', 'pipecat', 'whisper', 'financetoolkit'}
PROTOCOL = {'a2a-python', 'mcp-python-sdk'}
EXTRA = {'ydata-profiling': {'setuptools': '80.9.0'}, 'mcp-python-sdk': {'mcp-types': '2.3.0'}}


def validate(service, operation, p):
    from .common import VerdugoError, fields, identifier, integer
    from .local_runtime import string, finite, matrix, validate as base
    from .local_analytics import validate as analytical
    from .local_extended import validate as extended
    if service not in SPECS or SPECS[service][0] != operation:
        raise VerdugoError('Unsupported research operation')
    required = {
        'advertools': ('texts',), 'pywikibot': ('text',), 'splink': ('records',),
        'iceberg': ('currency', 'rows'), 'feast': ('rows',),
        'openlineage': ('job', 'inputs', 'outputs'),
        'causalml': ('covariates', 'treatment', 'outcome', 'assumptions_acknowledged'),
        'ydata-profiling': ('rows',), 'opendp': ('sensitivity', 'scale'),
        'flaml': ('train_x', 'train_y', 'score_x'), 'vowpal': ('train_x', 'train_y', 'score_x'),
        'recommenders': ('relevant', 'ranked', 'k'), 'py-ecomplexity': ('rows',),
        'osmnx': ('nodes', 'edges', 'origin', 'destination'),
        'mesa': ('workers', 'jobs', 'steps'), 'langchain': ('text',),
        'pydantic-ai': ('messages',), 'dspy': ('pairs',), 'docling': ('html',),
        'pipecat': ('left', 'right'), 'whisper': ('samples',),
        'financetoolkit': ('currency', 'current_assets', 'current_liabilities', 'cash', 'securities', 'receivables'),
        'a2a-python': ('artifact_id', 'text'), 'mcp-python-sdk': ('text', 'is_error'),
    }
    try:
        fields(p, ('dataset', *required[service]))
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerdugoError('Input must be bounded finite JSON') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')

    def items(values, minimum=1, maximum=100):
        if not isinstance(values, list) or not minimum <= len(values) <= maximum:
            raise VerdugoError('Invalid bounded list size')
        return values

    if service == 'advertools':
        for v in items(p['texts'], maximum=50): string(v, 2000)
    elif service in ('pywikibot', 'langchain'):
        string(p['text'], 16000)
    elif service == 'splink':
        seen = set()
        for r in items(p['records'], minimum=2, maximum=80):
            fields(r, ('id', 'label')); identifier(r['id']); string(r['label'], 200)
            if r['id'] in seen: raise VerdugoError('Duplicate record ID')
            seen.add(r['id'])
    elif service == 'iceberg':
        base('duckdb', 'campaigns.aggregate', p)
    elif service == 'feast':
        seen = set()
        for r in items(p['rows']):
            fields(r, ('entity_id', 'value')); integer(r['entity_id'], 1, 10**9); finite(r['value'])
            if r['entity_id'] in seen: raise VerdugoError('Duplicate feature entity')
            seen.add(r['entity_id'])
    elif service == 'openlineage':
        identifier(p['job'])
        for k in ('inputs', 'outputs'):
            for name in items(p[k], maximum=20): identifier(name)
            if len(set(p[k])) != len(p[k]): raise VerdugoError('Duplicate lineage dataset')
    elif service == 'causalml':
        extended('dowhy', 'effect.estimate', p)
    elif service == 'ydata-profiling':
        if matrix(p['rows'], minimum=2, nullable=True) > 8:
            raise VerdugoError('Profiling supports at most eight columns')
    elif service == 'opendp':
        integer(p['sensitivity'], 1, 1000); finite(p['scale'], 0.001, 1e6)
    elif service in ('flaml', 'vowpal'):
        analytical('statsmodels', 'regression.fit', p)
    elif service == 'recommenders':
        for key in ('relevant', 'ranked'):
            for v in items(p[key]): identifier(v)
            if len(set(p[key])) != len(p[key]): raise VerdugoError('Duplicate ranked/relevant ID')
        integer(p['k'], 1, min(20, len(p['ranked'])))
    elif service == 'py-ecomplexity':
        seen = set(); locations = set(); products = set()
        for r in items(p['rows'], minimum=9, maximum=200):
            fields(r, ('location', 'product', 'value')); identifier(r['location']); identifier(r['product']); finite(r['value'], 0, 1e12)
            key = (r['location'], r['product'])
            if key in seen: raise VerdugoError('Duplicate trade cell')
            seen.add(key); locations.add(key[0]); products.add(key[1])
        if not 3 <= len(locations) <= 20 or not 3 <= len(products) <= 20:
            raise VerdugoError('Trade data requires 3..20 locations and products')
        if len(seen) != len(locations)*len(products):
            raise VerdugoError('Provide the full trade matrix, including zero cells')
        for field, values in (('location', locations), ('product', products)):
            if any(sum(r['value'] for r in p['rows'] if r[field] == value) <= 0 for value in values):
                raise VerdugoError('Zero trade margins do not support comparison')
    elif service == 'osmnx':
        for n in items(p['nodes']): identifier(n)
        if len(set(p['nodes'])) != len(p['nodes']): raise VerdugoError('Duplicate route node')
        for r in items(p['edges'], maximum=300):
            fields(r, ('from', 'to', 'length')); finite(r['length'], 0.001, 1e7)
            if r['from'] not in p['nodes'] or r['to'] not in p['nodes']: raise VerdugoError('Unknown route node')
        if p['origin'] not in p['nodes'] or p['destination'] not in p['nodes']: raise VerdugoError('Unknown route endpoint')
    elif service == 'mesa':
        integer(p['workers'], 1, 50); integer(p['jobs'], 0, 10000); integer(p['steps'], 1, 100)
    elif service == 'pydantic-ai':
        for m in items(p['messages'], maximum=40):
            fields(m, ('role', 'text')); string(m['text'], 2000)
            if m['role'] not in ('user', 'assistant'): raise VerdugoError('Only user and assistant text messages are supported')
    elif service == 'dspy':
        for r in items(p['pairs'], maximum=50):
            fields(r, ('reference', 'answer')); string(r['reference'], 1000); string(r['answer'], 1000)
    elif service == 'docling':
        base('trafilatura', 'html.extract', p)
    elif service in ('pipecat', 'whisper'):
        for key in (('left', 'right') if service == 'pipecat' else ('samples',)):
            for v in items(p[key], minimum=400 if service == 'whisper' else 1, maximum=3000): integer(v, -32768, 32767)
    elif service == 'financetoolkit':
        if p['currency'] not in ('MXN', 'USD', 'EUR'): raise VerdugoError('Explicit supported currency required')
        for key in ('current_assets', 'cash', 'securities', 'receivables'): finite(p[key], 0, 1e12)
        finite(p['current_liabilities'], 0.001, 1e12)
        if p['cash']+p['securities']+p['receivables'] > p['current_assets']:
            raise VerdugoError('Quick assets exceed current assets')
    elif service == 'a2a-python':
        identifier(p['artifact_id']); string(p['text'], 16000)
    elif service == 'mcp-python-sdk':
        string(p['text'], 16000)
        if type(p['is_error']) is not bool: raise VerdugoError('Error indicator must be boolean')


def run(service, p):
    return HANDLERS[service](p)


def links(p):
    import advertools as adv
    r = adv.extract_urls(p['texts'])
    return {'documents': len(p['texts']), 'counts': r['url_counts'],
            'total_links': sum(r['url_counts']), 'distinct_links': len(set(r['urls_flat'])),
            'links_followed': 0, 'urls_returned': False}


def wiki(p):
    from pywikibot.textlib import removeDisabledParts
    text = removeDisabledParts(p['text'], tags=['comment', 'nowiki', 'pre', 'includeonly', 'syntaxhighlight'])
    return {'text': text, 'removed_characters': len(p['text'])-len(text),
            'wiki_fetched': False, 'content_is_untrusted_data': True}


def link_records(p):
    import duckdb
    import pandas as pd
    from splink import DuckDBAPI, Linker, SettingsCreator, block_on
    con = duckdb.connect(':memory:', config={'enable_external_access': False, 'threads': 1})
    try:
        api = DuckDBAPI(connection=con)
        frame = pd.DataFrame([{'unique_id': r['id'], 'label': r['label'].casefold().strip()} for r in p['records']])
        table = api.register(frame)
        settings = SettingsCreator(link_type='dedupe_only', comparisons=[],
                                   blocking_rules_to_generate_predictions=[block_on('label')])
        linker = Linker(table, settings)
        result = linker.inference.deterministic_link().as_pandas_dataframe()
        pairs = sorted([sorted([str(r.unique_id_l), str(r.unique_id_r)]) for r in result.itertuples()])
        return {'candidate_pairs': pairs, 'pair_count': len(pairs),
                'rule': 'casefolded trimmed label equality', 'same_entity_proven': False}
    finally:
        con.close()


def snapshot(p):
    from pathlib import Path
    import pyarrow as pa
    from pyiceberg.catalog.sql import SqlCatalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import NestedField, StringType, LongType
    root = Path.cwd()
    catalog = SqlCatalog('verdugo', uri='sqlite:///'+str(root/'catalog.db'), warehouse=(root/'warehouse').as_uri())
    try:
        catalog.create_namespace('verdugo')
        schema = Schema(NestedField(1, 'channel', StringType(), required=False),
                        *[NestedField(i+2, name, LongType(), required=False) for i, name in enumerate(
                            ('spend_minor', 'revenue_minor', 'leads', 'conversions'))])
        table = catalog.create_table('verdugo.campaigns', schema=schema)
        table.append(pa.Table.from_pylist(p['rows']))
        observed = table.scan().to_arrow().to_pylist()
        if observed != p['rows']: raise ValueError('Iceberg readback mismatch')
        return {'rows': len(observed), 'snapshots': len(table.metadata.snapshots),
                'currency': p['currency'], 'readback_verified': True,
                'catalog_scope': 'temporary-local', 'durable_result_store': 'Engine'}
    finally:
        catalog.engine.dispose()


def feature_store(p):
    from datetime import datetime, timedelta, timezone
    from pathlib import Path
    import pandas as pd
    from feast import Entity, FeatureStore, FeatureView, Field, FileSource, ValueType
    from feast.types import Float64
    from feast.repo_config import RepoConfig
    root = Path.cwd()
    date = datetime(2020, 1, 2, tzinfo=timezone.utc)
    rows = [dict(r, event_timestamp=date) for r in p['rows']]
    pd.DataFrame(rows).to_parquet(root/'features.parquet', index=False)
    config = RepoConfig(project='verdugo', provider='local', registry=str(root/'registry.db'),
                        offline_store={'type': 'file'}, online_store={'type': 'sqlite', 'path': str(root/'online.db')})
    store = FeatureStore(config=config)
    entity = Entity(name='entity', join_keys=['entity_id'], value_type=ValueType.INT64)
    view = FeatureView(name='observations', entities=[entity], ttl=timedelta(days=36500),
                       schema=[Field(name='value', dtype=Float64)],
                       source=FileSource(path=str(root/'features.parquet'), timestamp_field='event_timestamp'))
    store.apply([entity, view])
    store.materialize(datetime(2020, 1, 1, tzinfo=timezone.utc), datetime(2020, 1, 3, tzinfo=timezone.utc))
    data = store.get_online_features(features=['observations:value'],
                                    entity_rows=[{'entity_id': r['entity_id']} for r in p['rows']]).to_dict()
    values = data['value']
    if values != [r['value'] for r in p['rows']]: raise ValueError('Feature readback mismatch')
    return {'entity_ids': data['entity_id'], 'values': values, 'readback_verified': True,
            'store_scope': 'temporary-local', 'durable_result_store': 'Engine'}


def lineage(p):
    import attr
    from uuid import uuid5, NAMESPACE_URL
    from openlineage.client.event_v2 import JobEvent, Job, InputDataset, OutputDataset
    event = JobEvent(eventTime='2000-01-01T00:00:00Z',
                     producer='https://github.com/josuechavando350-png/Verdugo-Digital',
                     job=Job(namespace='verdugo-'+p['dataset'], name=p['job']),
                     inputs=[InputDataset(namespace='verdugo-'+p['dataset'], name=n) for n in p['inputs']],
                     outputs=[OutputDataset(namespace='verdugo-'+p['dataset'], name=n) for n in p['outputs']])
    return {'event': attr.asdict(event), 'event_kind': 'static job metadata',
            'timestamp_is_placeholder': True, 'execution_attested': False, 'sent': False}


def effect(p):
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from causalml.inference.meta import BaseSRegressor
    estimator = BaseSRegressor(learner=LinearRegression())
    estimates = estimator.fit_predict(np.asarray(p['covariates']), np.asarray(p['treatment']),
                                     np.asarray(p['outcome']), return_ci=False, verbose=False)
    return {'estimated_effect': float(np.asarray(estimates).mean()), 'method': 'linear S-learner',
            'causal_assumptions_verified': False, 'rows': len(p['outcome'])}


def profile(p):
    import pandas as pd
    from ydata_profiling import ProfileReport
    r = ProfileReport(pd.DataFrame(p['rows'], dtype=float), minimal=True, progress_bar=False,
                      pool_size=1, samples=None).get_description()
    variables = r.variables
    return {'rows': len(p['rows']), 'columns': len(p['rows'][0]),
            'missing_cells': int(r.table['n_cells_missing']),
            'column_missing': [int(variables[c]['n_missing']) for c in variables],
            'raw_rows_returned': False}


def privacy(p):
    import opendp.prelude as dp
    dp.enable_features('contrib')
    measurement = dp.m.make_laplace(dp.atom_domain(T=int), dp.absolute_distance(T=int), scale=float(p['scale']))
    epsilon = float(measurement.map(p['sensitivity']))
    return {'epsilon_bound': epsilon, 'delta': 0, 'sensitivity': p['sensitivity'], 'scale': p['scale'],
            'private_data_processed': False, 'release_generated': False,
            'basis': 'Calibration only; no dataset privacy budget consumed or certified'}


def automl(p):
    import numpy as np
    from flaml import AutoML
    estimator = AutoML()
    estimator.fit(X_train=np.asarray(p['train_x']), y_train=np.asarray(p['train_y']), task='regression',
                  estimator_list=['rf'], max_iter=3, time_budget=5, n_jobs=1, seed=0,
                  eval_method='holdout', split_ratio=0.25, metric='mse', verbose=0, log_file_name='')
    return {'predictions': estimator.predict(np.asarray(p['score_x'])).tolist(),
            'validation_mse': float(estimator.best_loss), 'estimator': estimator.best_estimator,
            'independent_test_set_used': False, 'search_trial_limit': 3}


def ranking(p):
    import pandas as pd
    from recommenders.evaluation.python_evaluation import precision_at_k, recall_at_k
    truth = pd.DataFrame({'userID': ['local']*len(p['relevant']), 'itemID': p['relevant'], 'rating': [1]*len(p['relevant'])})
    ranked = pd.DataFrame({'userID': ['local']*len(p['ranked']), 'itemID': p['ranked'],
                           'prediction': list(range(len(p['ranked']), 0, -1))})
    return {'precision_at_k': float(precision_at_k(truth, ranked, k=p['k'])),
            'recall_at_k': float(recall_at_k(truth, ranked, k=p['k'])), 'k': p['k'],
            'users_evaluated': 1, 'relevance_is_operator_supplied': True}


def online_regression(p):
    from vowpalwabbit import Workspace
    model = Workspace(quiet=True, loss_function='squared', learning_rate=0.3, bit_precision=16, random_seed=0)
    def features(row):
        return '|x '+' '.join('f'+str(i)+':'+str(float(v)) for i, v in enumerate(row))
    try:
        for _ in range(10):
            for x, y in zip(p['train_x'], p['train_y']): model.learn(str(float(y))+' '+features(x))
        predictions = [float(model.predict(features(x))) for x in p['score_x']]
        return {'predictions': predictions, 'epochs': 10, 'holdout_evaluated': False, 'external_model_loaded': False}
    finally:
        model.finish()


def trade(p):
    import pandas as pd
    from ecomplexity import ecomplexity
    data = pd.DataFrame([dict(r, year=2000) for r in p['rows']])
    r = ecomplexity(data, {'time': 'year', 'loc': 'location', 'prod': 'product', 'val': 'value'},
                   val_errors_flag='raise', verbose=False)
    cells = [{'location': str(row.location), 'product': str(row.product), 'rca': float(row.rca),
              'diversity': int(row.diversity), 'ubiquity': int(row.ubiquity)} for row in r.itertuples()]
    return {'cells': sorted(cells, key=lambda row: (row['location'], row['product'])),
            'basis': 'Supplied single-period trade matrix', 'forecast_generated': False}


def routes(p):
    import networkx as nx
    from osmnx.routing import shortest_path
    graph = nx.MultiDiGraph()
    node_index = {node: i for i, node in enumerate(p['nodes'])}
    graph.add_nodes_from(node_index.values())
    for e in p['edges']: graph.add_edge(node_index[e['from']], node_index[e['to']], length=float(e['length']))
    path = shortest_path(graph, node_index[p['origin']], node_index[p['destination']], weight='length', cpus=1)
    distance = sum(min(edge['length'] for edge in graph[u][v].values()) for u, v in zip(path, path[1:])) if path else None
    return {'path': [p['nodes'][i] for i in path] if path is not None else None, 'length': distance, 'external_map_downloaded': False,
            'basis': 'Directed edges and lengths supplied by operator'}


def capacity(p):
    from mesa import Agent, Model
    class Worker(Agent):
        def step(self):
            if self.model.remaining:
                self.model.remaining -= 1
                self.model.completed += 1
    model = Model(rng=0)
    model.remaining = p['jobs']; model.completed = 0
    for _ in range(p['workers']): Worker(model)
    for _ in range(p['steps']): model.agents.do('step')
    return {'completed': model.completed, 'remaining': model.remaining,
            'workers': len(model.agents), 'steps': p['steps'],
            'rule': 'One job per worker per step', 'simulation_only': True, 'real_capacity_validated': False}


def chunks(p):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, add_start_index=True)
    docs = splitter.create_documents([p['text']])
    return {'chunks': [{'text': d.page_content, 'start': d.metadata['start_index']} for d in docs],
            'count': len(docs), 'maximum_characters': 500, 'content_is_untrusted_data': True}


def messages(p):
    from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart, ModelMessagesTypeAdapter
    turns = [ModelRequest(parts=[UserPromptPart(content=m['text'])]) if m['role'] == 'user'
             else ModelResponse(parts=[TextPart(content=m['text'])]) for m in p['messages']]
    blob = ModelMessagesTypeAdapter.dump_json(turns)
    parsed = ModelMessagesTypeAdapter.validate_json(blob)
    return {'messages': len(parsed), 'user_turns': sum(m['role'] == 'user' for m in p['messages']),
            'assistant_turns': sum(m['role'] == 'assistant' for m in p['messages']),
            'text_characters': sum(len(m['text']) for m in p['messages']),
            'schema_roundtrip_verified': True, 'model_called': False, 'text_returned': False}


def answers(p):
    import dspy
    from dspy.evaluate.metrics import answer_exact_match
    matches = [bool(answer_exact_match(dspy.Example(answer=r['reference']), dspy.Prediction(answer=r['answer']))) for r in p['pairs']]
    return {'matches': matches, 'matched': sum(matches), 'total': len(matches),
            'normalized_exact_match_rate': sum(matches)/len(matches),
            'semantic_truth_verified': False, 'model_called': False}


def document(p):
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    result = DocumentConverter(allowed_formats=[InputFormat.HTML]).convert_string(p['html'], format=InputFormat.HTML)
    text = result.document.export_to_markdown()
    return {'markdown': text[:20000], 'truncated': len(text) > 20000,
            'format': 'HTML', 'ocr_executed': False, 'content_is_untrusted_data': True}


def mix(p):
    import numpy as np
    from pipecat.audio.utils import mix_audio
    out = mix_audio(np.asarray(p['left'], dtype='<i2').tobytes(), np.asarray(p['right'], dtype='<i2').tobytes())
    samples = np.frombuffer(out, dtype='<i2').astype(int).tolist()
    return {'samples': samples, 'sample_count': len(samples), 'format': 'mono PCM signed 16-bit',
            'playback_started': False}


def audio_features(p):
    import numpy as np
    from whisper.audio import log_mel_spectrogram
    import torch
    torch.set_num_threads(1)
    mel = log_mel_spectrogram(np.asarray(p['samples'], dtype=np.float32)/32768, device='cpu').numpy()
    return {'bands': int(mel.shape[0]), 'frames': int(mel.shape[1]),
            'band_means': mel.mean(axis=1).tolist(), 'sample_rate': 16000,
            'model_loaded': False, 'speech_transcribed': False}


def liquidity(p):
    from financetoolkit.ratios.liquidity_model import get_current_ratio, get_quick_ratio
    return {'current_ratio': float(get_current_ratio(p['current_assets'], p['current_liabilities'])),
            'quick_ratio': float(get_quick_ratio(p['cash'], p['securities'], p['receivables'], p['current_liabilities'])),
            'currency': p['currency'], 'basis': 'Operator supplied balance sheet amounts', 'bank_reconciled': False}


def a2a_artifact(p):
    from a2a.compat.v0_3.types import Artifact, Part, TextPart
    artifact = Artifact(artifact_id=p['artifact_id'], parts=[Part(root=TextPart(text=p['text']))],
                        metadata={'verdugo_dataset': p['dataset']})
    encoded = artifact.model_dump_json(by_alias=True, exclude_none=True)
    restored = Artifact.model_validate_json(encoded)
    return {'artifact': restored.model_dump(mode='json', by_alias=True, exclude_none=True),
            'protocol': 'A2A 0.3 compatibility', 'schema_roundtrip_verified': True, 'sent': False}


def mcp_result(p):
    from mcp_types import CallToolResult, TextContent
    result = CallToolResult(content=[TextContent(text=p['text'])], is_error=p['is_error'])
    encoded = result.model_dump_json(by_alias=True, exclude_none=True)
    restored = CallToolResult.model_validate_json(encoded)
    return {'envelope': restored.model_dump(mode='json', by_alias=True, exclude_none=True),
            'schema_roundtrip_verified': True, 'sent': False}


HANDLERS = {
    'advertools': links, 'pywikibot': wiki, 'splink': link_records, 'iceberg': snapshot,
    'feast': feature_store, 'openlineage': lineage, 'causalml': effect, 'ydata-profiling': profile,
    'opendp': privacy, 'flaml': automl, 'recommenders': ranking, 'vowpal': online_regression,
    'py-ecomplexity': trade, 'osmnx': routes, 'mesa': capacity, 'langchain': chunks,
    'pydantic-ai': messages, 'dspy': answers, 'docling': document, 'pipecat': mix,
    'whisper': audio_features, 'financetoolkit': liquidity, 'a2a-python': a2a_artifact,
    'mcp-python-sdk': mcp_result,
}
