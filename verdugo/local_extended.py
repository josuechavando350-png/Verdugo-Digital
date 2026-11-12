"""Seven bounded local operations. No provider clients, LLMs or user code.

Parent-side validation imports the core lazily. Worker-side recipes import only
installed dependencies. Temporary library stores are not production services.
"""
import math

SPECS = {
    'dlt': ('campaigns.load', 'dlt', '1.32.0'),
    'langgraph': ('leads.route', 'langgraph', '1.2.20'),
    'llama-index': ('documents.rank', 'llama-index-retrievers-bm25', '0.8.0'),
    'ragas': ('retrieval.evaluate', 'ragas', '0.4.3'),
    'mlflow': ('experiment.record', 'mlflow-skinny', '3.18.0'),
    'dowhy': ('effect.estimate', 'dowhy', '0.14'),
    'econml': ('effect.estimate', 'econml', '0.17.0'),
}
EXTRA = {'dlt': {'duckdb': '1.5.6'}}


def validate(service, operation, p):
    from .common import VerdugoError, fields, identifier, integer
    from .local_runtime import finite, string, matrix, labels, validate as base_validate
    required = {
        'campaigns.load': ('dataset', 'currency', 'rows'),
        'leads.route': ('dataset', 'leads'),
        'documents.rank': ('dataset', 'documents', 'query'),
        'retrieval.evaluate': ('dataset', 'retrieved_contexts', 'reference_contexts'),
        'experiment.record': ('dataset', 'metrics'),
        'effect.estimate': ('dataset', 'covariates', 'treatment', 'outcome', 'assumptions_acknowledged'),
    }
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported extended local operation')
    try:
        fields(p, required[operation], ('top_k',) if service == 'llama-index' else ())
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerdugoError('Extended input must be finite JSON') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit demo or real dataset is required')
    if service == 'dlt':
        base_validate('duckdb', 'campaigns.aggregate', p)
    elif service == 'langgraph':
        if not isinstance(p['leads'], list) or not 1 <= len(p['leads']) <= 100:
            raise VerdugoError('Provide 1..100 leads')
        seen = set()
        for lead in p['leads']:
            fields(lead, ('id', 'need_confirmed', 'budget_confirmed', 'authority_confirmed', 'decision_days'))
            key = identifier(lead['id'])
            if key in seen:
                raise VerdugoError('Duplicate lead ID')
            seen.add(key)
            for name in ('need_confirmed', 'budget_confirmed', 'authority_confirmed'):
                if type(lead[name]) is not bool:
                    raise VerdugoError('Qualification flags must be boolean')
            integer(lead['decision_days'], 0, 3650)
    elif service == 'llama-index':
        base_validate('haystack', 'documents.search', p)
        string(p['query'], 500)
        if not any(c.isalnum() for c in p['query']):
            raise VerdugoError('Query must contain searchable text')
        if any(not any(c.isalnum() for c in row['content']) for row in p['documents']):
            raise VerdugoError('Every document must contain searchable text')
    elif service == 'ragas':
        for field in ('retrieved_contexts', 'reference_contexts'):
            value = p[field]
            if not isinstance(value, list) or not 1 <= len(value) <= 20:
                raise VerdugoError('Provide 1..20 contexts per set')
            for context in value:
                string(context, 2000)
            if len(set(value)) != len(value):
                raise VerdugoError('Duplicate contexts must be removed before evaluation')
    elif service == 'mlflow':
        metrics = p['metrics']
        if not isinstance(metrics, dict) or not 1 <= len(metrics) <= 30:
            raise VerdugoError('Provide 1..30 scalar metrics')
        for name, value in metrics.items():
            identifier(name)
            finite(value)
    else:
        width = matrix(p['covariates'], minimum=40)
        if width > 8:
            raise VerdugoError('At most 8 observed covariates are supported')
        n = len(p['covariates'])
        labels(p['treatment'], n, minimum_per_class=10)
        if not isinstance(p['outcome'], list) or len(p['outcome']) != n:
            raise VerdugoError('Outcome and covariates must have equal row counts')
        for value in p['outcome']:
            finite(value, -1e6, 1e6)
        if p['assumptions_acknowledged'] is not True:
            raise VerdugoError('Causal assumptions must be explicitly acknowledged')
        if len(set(p['outcome'])) < 2:
            raise VerdugoError('Constant outcomes do not support this estimator')


def run(service, p):
    return {'dlt': load_campaigns, 'langgraph': route_leads,
            'llama-index': rank_documents, 'ragas': evaluate_retrieval,
            'mlflow': record_experiment, 'dowhy': estimate_effect,
            'econml': estimate_dml}[service](p)


def load_campaigns(p):
    from pathlib import Path
    import dlt
    root = Path.cwd()
    pipeline = dlt.pipeline(pipeline_name='verdugo_campaigns',
        pipelines_dir=str(root / 'pipelines'),
        destination=dlt.destinations.duckdb(str(root / 'campaigns.duckdb')),
        dataset_name='marketing', dev_mode=False)
    load = pipeline.run(p['rows'], table_name='campaigns', write_disposition='replace')
    load.raise_on_failed_jobs()
    with pipeline.sql_client() as sql:
        rows = sql.execute_sql('SELECT channel, SUM(spend_minor), SUM(revenue_minor), SUM(leads), SUM(conversions) FROM campaigns GROUP BY channel ORDER BY channel')
        count = sql.execute_sql('SELECT COUNT(*) FROM campaigns')[0][0]
    channels = [dict(zip(('channel', 'spend_minor', 'revenue_minor', 'leads', 'conversions'), row)) for row in rows]
    return {'loaded_rows': int(count), 'currency': p['currency'], 'channels': channels,
            'warehouse_scope': 'temporary-local', 'bank_reconciled': False,
            'durable_result_store': 'Engine', 'external_destination_used': False}


def route_leads(p):
    from typing import TypedDict
    from langgraph.graph import StateGraph, START, END
    class State(TypedDict):
        leads: list
        qualified: list
        nurture: list
        unqualified: list
        counts: dict
    def classify(state):
        buckets = {'qualified': [], 'nurture': [], 'unqualified': []}
        for lead in state['leads']:
            target = ('unqualified' if not lead['need_confirmed'] else
                      'qualified' if all(lead[k] for k in ('budget_confirmed', 'authority_confirmed')) and lead['decision_days'] <= 30 else
                      'nurture')
            buckets[target].append(lead['id'])
        return buckets
    def summarize(state):
        return {'counts': {k: len(state[k]) for k in ('qualified', 'nurture', 'unqualified')}}
    graph = StateGraph(State)
    graph.add_node('classify', classify)
    graph.add_node('summarize', summarize)
    graph.add_edge(START, 'classify')
    graph.add_edge('classify', 'summarize')
    graph.add_edge('summarize', END)
    result = graph.compile().invoke({'leads': p['leads']}, config={'recursion_limit': 5})
    return {k: result[k] for k in ('qualified', 'nurture', 'unqualified', 'counts')} | {
        'basis': 'operator-declared qualification rules, not predicted sales',
        'llm_called': False, 'contacted_anyone': False}


def rank_documents(p):
    from llama_index.core.schema import TextNode
    from llama_index.retrievers.bm25 import BM25Retriever
    nodes = [TextNode(id_=d['id'], text=d['content']) for d in p['documents']]
    retriever = BM25Retriever.from_defaults(nodes=nodes,
        similarity_top_k=min(p.get('top_k', 5), len(nodes)),
        stemmer=None, language='english')
    hits = retriever.retrieve(p['query'])
    matches = [{'id': h.node.node_id, 'score': float(h.score), 'content': h.node.text}
               for h in hits if h.score is not None and math.isfinite(h.score) and h.score > 0]
    return {'matches': matches, 'contexts': [m['content'] for m in matches],
            'algorithm': 'BM25 lexical retrieval', 'llm_called': False,
            'embedding_model_loaded': False, 'content_is_untrusted_data': True}


def evaluate_retrieval(p):
    import asyncio
    from ragas import SingleTurnSample
    from ragas.metrics import NonLLMContextPrecisionWithReference
    sample = SingleTurnSample(retrieved_contexts=p['retrieved_contexts'],
                              reference_contexts=p['reference_contexts'])
    metric = NonLLMContextPrecisionWithReference(threshold=0.8)
    score = float(asyncio.run(metric.single_turn_ascore(sample)))
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError('Metric did not return a valid precision')
    return {'context_precision': score, 'lexical_similarity_threshold': 0.8,
            'retrieved_count': len(p['retrieved_contexts']),
            'reference_count': len(p['reference_contexts']),
            'metric': 'NonLLMContextPrecisionWithReference', 'llm_called': False,
            'semantic_correctness_proven': False, 'commercial_success_probability': None}


def record_experiment(p):
    from pathlib import Path
    from mlflow import MlflowClient
    from mlflow.entities import Metric
    root = Path.cwd()
    client = MlflowClient(tracking_uri='sqlite:///' + str(root / 'tracking.sqlite3'))
    experiment = client.create_experiment('verdugo_local', artifact_location=(root / 'artifacts').as_uri())
    run = client.create_run(experiment, tags={'verdugo.dataset': p['dataset']})
    run_id = run.info.run_id
    client.log_batch(run_id, metrics=[Metric(key, float(value), 0, 0) for key, value in sorted(p['metrics'].items())])
    client.set_terminated(run_id, status='FINISHED')
    observed = client.get_run(run_id)
    wanted = {k: float(v) for k, v in p['metrics'].items()}
    if observed.data.metrics != wanted or observed.info.status != 'FINISHED':
        raise ValueError('MLflow metric readback mismatch')
    return {'metrics': observed.data.metrics, 'run_status': observed.info.status,
            'readback_verified': True, 'tracking_scope': 'temporary-local',
            'durable_result_store': 'Engine', 'remote_tracking_used': False}


def causal_data(p):
    import numpy as np
    import pandas as pd
    x = np.asarray(p['covariates'], dtype=float)
    t = np.asarray(p['treatment'], dtype=int)
    y = np.asarray(p['outcome'], dtype=float)
    design = np.column_stack([np.ones(len(x)), x, t])
    if np.linalg.matrix_rank(design) != design.shape[1] or np.linalg.cond(design) > 1e10:
        raise ValueError('Causal design is rank deficient or ill conditioned')
    names = ['x' + str(i) for i in range(x.shape[1])]
    data = pd.DataFrame(x, columns=names)
    data['treatment'], data['outcome'] = t, y
    return data, names, x, t, y


def effect_result(p, effect, method):
    effect = float(effect)
    if not math.isfinite(effect):
        raise ValueError('Nonfinite effect estimate')
    return {'estimated_effect': effect, 'method': method, 'rows': len(p['outcome']),
            'treatment_contrast': [0, 1], 'causal_assumptions_verified': False,
            'assumptions': ['no unobserved confounding', 'overlap', 'consistency', 'model specification'],
            'production_certified': False, 'commercial_success_probability': None}


def estimate_effect(p):
    from dowhy import CausalModel
    import networkx as nx
    data, names, _, _, _ = causal_data(p)
    graph = nx.DiGraph([('treatment', 'outcome')])
    for name in names:
        graph.add_edges_from([(name, 'treatment'), (name, 'outcome')])
    model = CausalModel(data=data, treatment='treatment', outcome='outcome', graph=graph)
    estimand = model.identify_effect(proceed_when_unidentifiable=False)
    effect = model.estimate_effect(estimand, method_name='backdoor.linear_regression',
        control_value=0, treatment_value=1, confidence_intervals=False)
    return effect_result(p, effect.value, 'DoWhy backdoor linear regression')


def estimate_dml(p):
    from econml.dml import LinearDML
    from sklearn.linear_model import LinearRegression, LogisticRegression
    _, _, x, t, y = causal_data(p)
    model = LinearDML(model_y=LinearRegression(),
        model_t=LogisticRegression(max_iter=200, random_state=17),
        discrete_treatment=True, cv=3, random_state=17)
    model.fit(y, t, X=x, inference=None)
    return effect_result(p, model.ate(X=x), 'EconML cross-fitted LinearDML')
