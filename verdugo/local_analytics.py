"""Bounded analytical operations over caller-supplied JSON, in the existing worker.

No downloads, arbitrary queries, model files, callbacks or remote clients. Source
API evidence and installed distribution versions are deliberately separate.
"""
import math

SPECS = {
    'markitdown': ('html.markdown', 'markitdown', '0.1.9'),
    'spacy': ('text.segment', 'spacy', '3.8.18'),
    'arrow': ('campaigns.aggregate', 'pyarrow', '26.0.1'),
    'polars': ('campaigns.aggregate', 'polars', '2.1.0'),
    'ibis': ('campaigns.aggregate', 'ibis-framework', '12.0.0'),
    'networkx': ('dependencies.analyze', 'networkx', '3.7'),
    'sqlglot': ('campaigns.query', 'sqlglot', '30.31.0'),
    'faker': ('fixtures.generate', 'Faker', '40.54.0'),
    'statsmodels': ('regression.fit', 'statsmodels', '0.15.0'),
    'shap': ('regression.explain', 'shap', '0.54.1'),
    'causal-learn': ('independence.test', 'causal-learn', '0.1.4.8'),
    'numpy-financial': ('cashflows.discount', 'numpy-financial', '1.0.0'),
    'datasketch': ('sets.compare', 'datasketch', '2.0.0'),
    'nashpy': ('game.equilibria', 'nashpy', '0.0.43'),
    'pymcdm': ('alternatives.rank', 'pymcdm', '1.4.0'),
    'h3': ('locations.aggregate', 'h3', '4.5.0'),
    'mlxtend': ('baskets.patterns', 'mlxtend', '0.25.0'),
    'lifelines': ('retention.estimate', 'lifelines', '0.30.3'),
    'pyod': ('anomalies.score', 'pyod', '3.6.8'),
    'mapie': ('regression.intervals', 'mapie', '1.6.0'),
    'pandera': ('data.validate', 'pandera', '0.36.0'),
    'great-tables': ('campaigns.render', 'great-tables', '1.1.0'),
    'river': ('stream.summarize', 'river', '0.27.0'),
    'statsforecast': ('series.baseline', 'statsforecast', '2.1.1'),
}
EXTRA = {sid: {'numpy': '2.5.4', 'pandas': '2.3.3'} for sid in (
    'arrow', 'polars', 'ibis', 'statsmodels', 'shap', 'causal-learn', 'numpy-financial',
    'datasketch', 'nashpy', 'pymcdm', 'mlxtend', 'lifelines', 'pyod', 'mapie',
    'pandera', 'great-tables', 'river', 'statsforecast')}
EXTRA['ibis'].update({'duckdb': '1.5.6', 'sqlglot': '30.31.0'})
for _sid in ('shap', 'pyod', 'mapie'):
    EXTRA[_sid]['scikit-learn'] = '1.9.1'


def validate(service, operation, p):
    from .common import VerdugoError, fields, identifier, integer
    from .local_runtime import finite, string, matrix, validate as base
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported analytical operation')
    requirements = {
        'html.markdown': ('html',), 'text.segment': ('text',),
        'campaigns.aggregate': ('currency', 'rows'),
        'dependencies.analyze': ('nodes', 'edges'), 'campaigns.query': ('dialect',),
        'fixtures.generate': ('count', 'seed'),
        'regression.fit': ('train_x', 'train_y', 'score_x'),
        'regression.explain': ('train_x', 'train_y', 'score_x'),
        'regression.intervals': ('train_x', 'train_y', 'calibration_x', 'calibration_y', 'score_x'),
        'independence.test': ('rows',), 'cashflows.discount': ('currency', 'rate', 'cashflows'),
        'sets.compare': ('left', 'right'), 'game.equilibria': ('row_payoffs', 'column_payoffs'),
        'alternatives.rank': ('rows', 'weights', 'directions'),
        'locations.aggregate': ('locations', 'resolution'),
        'baskets.patterns': ('baskets', 'minimum_support'),
        'retention.estimate': ('durations', 'events', 'times'),
        'anomalies.score': ('reference', 'current'),
        'data.validate': ('rows', 'minimum', 'maximum'),
        'campaigns.render': ('currency', 'rows'),
        'stream.summarize': ('values',), 'series.baseline': ('values', 'horizon'),
    }
    try:
        fields(p, ('dataset', *requirements[operation]))
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerdugoError('Analytical input must be finite JSON') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit demo or real dataset is required')

    def vector(v, low=-1e9, high=1e9, minimum=1, maximum=500):
        if not isinstance(v, list) or not minimum <= len(v) <= maximum:
            raise VerdugoError('Invalid bounded vector length')
        for x in v:
            finite(x, low, high)

    if operation in ('campaigns.aggregate', 'campaigns.render'):
        base('duckdb', 'campaigns.aggregate', p)
    elif service == 'markitdown':
        base('trafilatura', 'html.extract', p)
    elif service == 'spacy':
        string(p['text'], 16000)
    elif service == 'networkx':
        nodes, edges = p['nodes'], p['edges']
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= 100:
            raise VerdugoError('Provide 1..100 nodes')
        for n in nodes:
            identifier(n)
        if len(set(nodes)) != len(nodes):
            raise VerdugoError('Duplicate graph node')
        if not isinstance(edges, list) or len(edges) > 300:
            raise VerdugoError('At most 300 graph edges')
        for e in edges:
            if not isinstance(e, list) or len(e) != 2 or any(x not in nodes for x in e):
                raise VerdugoError('Edges must reference declared nodes')
        if len({tuple(e) for e in edges}) != len(edges):
            raise VerdugoError('Duplicate graph edge')
    elif service == 'sqlglot':
        if p['dialect'] not in ('duckdb', 'postgres', 'sqlite'):
            raise VerdugoError('Unsupported output dialect')
    elif service == 'faker':
        if p['dataset'] != 'demo':
            raise VerdugoError('Generated fixtures must remain demo data')
        integer(p['count'], 1, 100)
        integer(p['seed'], 0, 2**31-1)
    elif service in ('statsmodels', 'shap', 'mapie'):
        width = matrix(p['train_x'], minimum=20)
        if width > 8 or matrix(p['score_x']) != width or len(p['score_x']) > 100:
            raise VerdugoError('Regression dimensions exceed limits or disagree')
        vector(p['train_y'])
        if len(p['train_y']) != len(p['train_x']):
            raise VerdugoError('Training row counts disagree')
        if service == 'mapie':
            if matrix(p['calibration_x'], minimum=20) != width:
                raise VerdugoError('Calibration width disagrees')
            vector(p['calibration_y'])
            if len(p['calibration_y']) != len(p['calibration_x']):
                raise VerdugoError('Calibration row counts disagree')
    elif service == 'causal-learn':
        if matrix(p['rows'], minimum=20) != 2:
            raise VerdugoError('Independence test requires exactly two columns')
        if any(len({r[i] for r in p['rows']}) < 2 for i in (0, 1)):
            raise VerdugoError('Independence test requires nonconstant columns')
    elif service == 'numpy-financial':
        if p['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('An explicit supported currency is required')
        finite(p['rate'], 0, 1)
        vector(p['cashflows'], minimum=2, maximum=120)
    elif service == 'datasketch':
        for name in ('left', 'right'):
            values = p[name]
            if not isinstance(values, list) or not 1 <= len(values) <= 200:
                raise VerdugoError('Provide 1..200 values per set')
            for value in values:
                string(value, 200)
    elif service == 'nashpy':
        a, b = p['row_payoffs'], p['column_payoffs']
        if matrix(a, minimum=2) != 2 or len(a) != 2 or matrix(b, minimum=2) != 2 or len(b) != 2:
            raise VerdugoError('Only bounded 2 by 2 games are supported')
    elif service == 'pymcdm':
        width = matrix(p['rows'], minimum=2)
        vector(p['weights'], 0.000001, 1)
        if len(p['weights']) != width or not math.isclose(sum(p['weights']), 1, abs_tol=1e-9):
            raise VerdugoError('Positive criterion weights must sum to one')
        d = p['directions']
        if not isinstance(d, list) or len(d) != width or any(type(x) is not int or x not in (-1, 1) for x in d):
            raise VerdugoError('Criterion directions must be -1 cost or 1 benefit')
        if any(len({r[i] for r in p['rows']}) < 2 for i in range(width)):
            raise VerdugoError('Constant criteria are unsupported')
    elif service == 'h3':
        if matrix(p['locations']) != 2:
            raise VerdugoError('Locations require latitude and longitude')
        for lat, lon in p['locations']:
            finite(lat, -90, 90); finite(lon, -180, 180)
        integer(p['resolution'], 0, 9)
    elif service == 'mlxtend':
        baskets = p['baskets']
        if not isinstance(baskets, list) or not 2 <= len(baskets) <= 200:
            raise VerdugoError('Provide 2..200 baskets')
        for basket in baskets:
            if not isinstance(basket, list) or not 1 <= len(basket) <= 15:
                raise VerdugoError('Provide 1..15 identifiers per basket')
            for item in basket:
                identifier(item)
            if len(set(basket)) != len(basket):
                raise VerdugoError('Duplicate basket item')
        if len({x for b in baskets for x in b}) > 15:
            raise VerdugoError('At most 15 distinct basket items')
        finite(p['minimum_support'], 0.05, 1)
    elif service == 'lifelines':
        vector(p['durations'], 0, 1e6, minimum=2)
        vector(p['times'], 0, 1e6, maximum=50)
        if p['times'] != sorted(set(p['times'])):
            raise VerdugoError('Observation times must increase without duplicates')
        events = p['events']
        if not isinstance(events, list) or len(events) != len(p['durations']) or any(type(x) is not bool for x in events):
            raise VerdugoError('One boolean event flag per duration is required')
    elif service == 'pyod':
        if matrix(p['reference'], minimum=10) != matrix(p['current']):
            raise VerdugoError('Anomaly dataset widths disagree')
    elif service == 'pandera':
        base('great-expectations', 'data.validate', p)
    elif service in ('river', 'statsforecast'):
        vector(p['values'], minimum=2)
        if service == 'statsforecast':
            integer(p['horizon'], 1, 30)


def run(service, p):
    return HANDLERS[service](p)


def markdown(p):
    from io import BytesIO
    from markitdown import MarkItDown, StreamInfo
    result = MarkItDown(enable_plugins=False).convert_stream(
        BytesIO(p['html'].encode()), stream_info=StreamInfo(extension='.html', mimetype='text/html'))
    text = result.text_content
    return {'markdown': text[:20000], 'truncated': len(text) > 20000,
            'content_is_untrusted_data': True, 'links_followed': 0}


def segment(p):
    import spacy
    nlp = spacy.blank('es')
    nlp.add_pipe('sentencizer')
    doc = nlp(p['text'])
    sentences = list(doc.sents)
    return {'lexical_units': len(doc), 'sentences': len(sentences),
            'sentence_spans': [[s.start_char, s.end_char] for s in sentences[:100]],
            'truncated': len(sentences) > 100, 'language_rules': 'es',
            'trained_model_loaded': False, 'entities_extracted': False}


def campaigns(service, p):
    columns = ('spend_minor', 'revenue_minor', 'leads', 'conversions')
    if service == 'arrow':
        import pyarrow as pa
        t = pa.Table.from_pylist(p['rows'])
        result = t.group_by('channel', use_threads=False).aggregate([(c, 'sum') for c in columns]).to_pylist()
        result = [{'channel': r['channel'], **{c: int(r[c+'_sum']) for c in columns}} for r in result]
    elif service == 'polars':
        import polars as pl
        result = pl.DataFrame(p['rows']).group_by('channel').agg(pl.col(*columns).sum()).to_dicts()
    else:
        import ibis
        con = ibis.duckdb.connect(threads=1, enable_external_access=False)
        try:
            import pyarrow as pa
            t = con.create_table('campaigns', ibis.memtable(pa.Table.from_pylist(p['rows'])), temp=True)
            result = t.group_by('channel').aggregate(**{c: t[c].sum() for c in columns}).to_pyarrow().to_pylist()
        finally:
            con.disconnect()
    return {'currency': p['currency'], 'channels': sorted(result, key=lambda r: r['channel']),
            'input_rows': len(p['rows']), 'bank_reconciled': False, 'causal_lift_estimated': False}


def dependencies(p):
    import networkx as nx
    graph = nx.DiGraph()
    graph.add_nodes_from(p['nodes']); graph.add_edges_from(p['edges'])
    dag = nx.is_directed_acyclic_graph(graph)
    return {'nodes': len(graph), 'edges': graph.number_of_edges(), 'acyclic': dag,
            'execution_order': list(nx.lexicographical_topological_sort(graph)) if dag else None,
            'ancestor_counts': {n: len(nx.ancestors(graph, n)) for n in sorted(graph)},
            'executed_any_task': False}


def campaign_query(p):
    import sqlglot
    # Fixed first-party AST: caller selects only one of three vetted dialects.
    query = 'SELECT channel, SUM(spend_minor) AS spend_minor, SUM(revenue_minor) AS revenue_minor FROM campaigns GROUP BY channel ORDER BY channel'
    tree = sqlglot.parse_one(query, read='duckdb')
    rendered = tree.sql(dialect=p['dialect'])
    sqlglot.parse_one(rendered, read=p['dialect'])
    return {'query': rendered, 'dialect': p['dialect'], 'tables': ['campaigns'],
            'template': 'campaign-channel-totals-v1', 'executed': False}


def fixtures(p):
    from faker import Faker
    fake = Faker('es_MX'); fake.seed_instance(p['seed'])
    rows = [{'id': 'demo-'+str(i+1), 'label': fake.company(),
             'email': 'fixture-'+str(i+1)+'@example.invalid'} for i in range(p['count'])]
    return {'rows': rows, 'synthetic': True, 'contactable': False, 'seed': p['seed']}


def regression(p):
    import numpy as np
    import statsmodels.api as sm
    x = sm.add_constant(np.asarray(p['train_x'], dtype=float), has_constant='add')
    if np.linalg.matrix_rank(x) != x.shape[1] or np.linalg.cond(x) > 1e10:
        raise ValueError('Regression design is singular or ill conditioned')
    model = sm.OLS(p['train_y'], x).fit()
    pred = model.predict(sm.add_constant(np.asarray(p['score_x'], dtype=float), has_constant='add'))
    return {'predictions': pred.tolist(), 'coefficients': model.params.tolist(),
            'in_sample_r_squared': float(model.rsquared), 'holdout_evaluated': False,
            'causal_effect_estimated': False}


def explain(p):
    import numpy as np
    import shap
    from sklearn.tree import DecisionTreeRegressor
    model = DecisionTreeRegressor(max_depth=3, random_state=0).fit(p['train_x'], p['train_y'])
    explainer = shap.TreeExplainer(model)
    values = np.asarray(explainer.shap_values(np.asarray(p['score_x'])), dtype=float)
    baseline = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    predictions = model.predict(p['score_x'])
    if not np.allclose(values.sum(axis=1)+baseline, predictions):
        raise ValueError('Explanation additivity mismatch')
    return {'feature_contributions': values.tolist(), 'base_value': baseline,
            'predictions': predictions.tolist(), 'additivity_verified': True,
            'model': 'local-depth-3-regression-tree', 'causal_effects': False}


def independence(p):
    import numpy as np
    from causallearn.utils.cit import CIT
    x = np.asarray(p['rows'], dtype=float)
    if abs(float(np.corrcoef(x.T)[0, 1])) >= 1-1e-12:
        raise ValueError('Perfectly collinear test data')
    value = float(CIT(x, 'fisherz')(0, 1))
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Invalid independence probability')
    return {'p_value': value, 'test': 'Fisher-Z marginal independence', 'rows': len(x),
            'gaussian_assumption_verified': False, 'causal_direction_identified': False}


def discount(p):
    import numpy_financial as nf
    value = float(nf.npv(p['rate'], p['cashflows']))
    return {'net_present_value': value, 'currency': p['currency'],
            'periods': len(p['cashflows'])-1, 'initial_cashflow_at_time_zero': True,
            'rate_per_period': p['rate'], 'bank_reconciled': False,
            'basis': 'Operator supplied equal-period cashflows and discount rate'}


def compare_sets(p):
    from datasketch import MinHash
    sketches = []
    for key in ('left', 'right'):
        sketch = MinHash(num_perm=128, seed=0)
        for value in sorted(set(p[key])):
            sketch.update(value.encode())
        sketches.append(sketch)
    left, right = set(p['left']), set(p['right'])
    return {'estimated_jaccard': float(sketches[0].jaccard(sketches[1])),
            'exact_jaccard': len(left & right)/len(left | right),
            'left_distinct': len(left), 'right_distinct': len(right),
            'permutations': 128, 'seed': 0}


def equilibria(p):
    import numpy as np
    import nashpy as nash
    game = nash.Game(np.asarray(p['row_payoffs']), np.asarray(p['column_payoffs']))
    result = []
    for row, col in game.support_enumeration():
        payoff = game[row, col]
        result.append({'row_strategy': row.tolist(), 'column_strategy': col.tolist(),
                       'payoffs': payoff.tolist()})
    return {'equilibria': result, 'method': 'support enumeration',
            'degenerate_games_may_be_incomplete': True, 'real_market_equilibrium_proven': False}


def rank(p):
    import numpy as np
    from pymcdm.methods import TOPSIS
    scores = TOPSIS()(np.asarray(p['rows']), np.asarray(p['weights']), np.asarray(p['directions']))
    return {'scores': scores.tolist(), 'order': sorted(range(len(scores)), key=lambda i: (-scores[i], i)),
            'method': 'TOPSIS', 'weights_are_operator_assumptions': True}


def locations(p):
    from collections import Counter
    import h3
    counts = Counter(h3.latlng_to_cell(lat, lon, p['resolution']) for lat, lon in p['locations'])
    return {'resolution': p['resolution'], 'cells': [{'cell': k, 'count': counts[k]} for k in sorted(counts)],
            'input_locations': len(p['locations']), 'privacy_anonymity_guaranteed': False}


def baskets(p):
    import pandas as pd
    from mlxtend.frequent_patterns import apriori
    names = sorted({x for row in p['baskets'] for x in row})
    frame = pd.DataFrame([[name in row for name in names] for row in p['baskets']], columns=names, dtype=bool)
    result = apriori(frame, min_support=p['minimum_support'], use_colnames=True, max_len=2)
    patterns = [{'items': sorted(row.itemsets), 'support': float(row.support)} for row in result.itertuples()]
    patterns.sort(key=lambda r: (-r['support'], r['items']))
    return {'patterns': patterns, 'baskets': len(p['baskets']), 'maximum_pattern_length': 2,
            'causal_relationships_proven': False}


def retention(p):
    from lifelines import KaplanMeierFitter
    model = KaplanMeierFitter().fit(p['durations'], event_observed=p['events'])
    median = float(model.median_survival_time_)
    return {'times': p['times'], 'survival': model.predict(p['times']).tolist(),
            'median_duration': median if math.isfinite(median) else None,
            'median_reached': math.isfinite(median), 'method': 'Kaplan-Meier right censoring',
            'noninformative_censoring_assumed': True}


def anomalies(p):
    from pyod.models.knn import KNN
    model = KNN(n_neighbors=5, contamination=0.1, n_jobs=1).fit(p['reference'])
    return {'scores': model.decision_function(p['current']).tolist(),
            'flags': model.predict(p['current']).astype(int).tolist(),
            'threshold': float(model.threshold_), 'method': 'KNN distance',
            'fraud_or_failure_proven': False}


def intervals(p):
    from mapie.regression import SplitConformalRegressor
    from sklearn.linear_model import LinearRegression
    model = SplitConformalRegressor(LinearRegression(), confidence_level=0.9, prefit=False)
    model.fit(p['train_x'], p['train_y'])
    model.conformalize(p['calibration_x'], p['calibration_y'])
    pred, bounds = model.predict_interval(p['score_x'])
    return {'predictions': pred.tolist(), 'intervals': bounds[:, :, 0].tolist(),
            'nominal_coverage': 0.9, 'exchangeability_assumed': True,
            'independent_coverage_measured': False, 'calibration_rows': len(p['calibration_x'])}


def validate_data(p):
    import pandas as pd
    import pandera.pandas as pa
    frame = pd.DataFrame(p['rows'], dtype=float)
    schema = pa.DataFrameSchema({i: pa.Column(float, pa.Check.in_range(p['minimum'], p['maximum']), nullable=False)
                                for i in frame.columns}, strict=True)
    try:
        schema.validate(frame, lazy=True)
        failures = 0
    except pa.errors.SchemaErrors as exc:
        failures = len(exc.failure_cases)
    return {'valid': failures == 0, 'failure_count': failures, 'rows': len(frame),
            'columns': len(frame.columns), 'checks': 'numeric, nonnull, bounded range',
            'raw_failed_values_returned': False}


def render_campaigns(p):
    import hashlib
    import pandas as pd
    from great_tables import GT
    # Channel identifiers are already restricted to alphanumeric/underscore/hyphen.
    frame = pd.DataFrame(p['rows'])
    html = GT(frame).tab_header(title='Campaign observations', subtitle=p['currency']).as_raw_html()
    if len(html.encode()) > 500000:
        raise ValueError('Rendered table exceeds budget')
    return {'html': html, 'sha256': hashlib.sha256(html.encode()).hexdigest(),
            'rows': len(frame), 'currency': p['currency'], 'javascript_added': False,
            'bank_reconciled': False}


def streaming(p):
    from river import stats
    mean, variance = stats.Mean(), stats.Var(ddof=1)
    for value in p['values']:
        mean.update(value); variance.update(value)
    return {'count': len(p['values']), 'mean': float(mean.get()),
            'sample_variance': float(variance.get()), 'incremental': True,
            'state_scope': 'this supplied batch; result persisted by Engine'}


def forecast(p):
    import numpy as np
    from statsforecast.models import Naive
    result = Naive().forecast(y=np.asarray(p['values'], dtype=float), h=p['horizon'])
    return {'predictions': result['mean'].tolist(), 'method': 'last-observation baseline',
            'horizon': p['horizon'], 'accuracy_validated': False}


HANDLERS = {
    'markitdown': markdown, 'spacy': segment,
    'arrow': lambda p: campaigns('arrow', p), 'polars': lambda p: campaigns('polars', p),
    'ibis': lambda p: campaigns('ibis', p), 'networkx': dependencies, 'sqlglot': campaign_query,
    'faker': fixtures, 'statsmodels': regression, 'shap': explain, 'causal-learn': independence,
    'numpy-financial': discount, 'datasketch': compare_sets, 'nashpy': equilibria,
    'pymcdm': rank, 'h3': locations, 'mlxtend': baskets, 'lifelines': retention,
    'pyod': anomalies, 'mapie': intervals, 'pandera': validate_data,
    'great-tables': render_campaigns, 'river': streaming, 'statsforecast': forecast,
}
