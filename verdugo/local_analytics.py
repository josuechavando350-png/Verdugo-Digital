"""v0.17: bounded local analytics recipes for the permissive-license portfolio.

Same contract as local_extended: parent-side validation imports the core
lazily; worker-side recipes import only installed dependencies. No network,
no model downloads, no user code, no file paths. Every recipe observes the
supplied JSON only and never proves a business outcome.

These recipes run in their own administrator-provisioned environment
(VERDUGO_ANALYTICS_PYTHON, see runtime_profile) so their dependency set never
disturbs the primary or Ragas environments.
"""
import math
import re

# service: (operation, primary distribution, exact tested version)
SPECS = {
    'networkx': ('graph.rank', 'networkx', '3.6.1'),
    'statsmodels': ('trend.fit', 'statsmodels', '0.14.6'),
    'polars': ('campaigns.summarize', 'polars', '1.40.1'),
    'sqlglot': ('sql.inspect', 'sqlglot', '28.10.1'),
    'faker': ('contacts.synthesize', 'Faker', '40.15.0'),
    'pandera': ('rows.validate', 'pandera', '0.31.1'),
    'datasketch': ('texts.near_duplicates', 'datasketch', '1.10.0'),
    'h3': ('points.index', 'h3', '4.5.0'),
    'lifelines': ('retention.estimate', 'lifelines', '0.30.3'),
    'pyod': ('outliers.detect', 'pyod', '3.2.0'),
    'river': ('stream.drift', 'river', '0.25.0'),
    'numpy-financial': ('cashflow.evaluate', 'numpy-financial', '1.0.0'),
    'nashpy': ('game.solve', 'nashpy', '0.0.43'),
    'pymcdm': ('alternatives.rank', 'pymcdm', '1.4.0'),
    'mlxtend': ('baskets.mine', 'mlxtend', '0.24.0'),
    'arrow': ('table.summarize', 'pyarrow', '24.0.0'),
    'markitdown': ('html.to_markdown', 'markitdown', '0.1.6'),
    'great-tables': ('table.render', 'great-tables', '0.21.0'),
    'spacy': ('text.segment', 'spacy', '3.8.14'),
    'parsedmarc': ('dmarc.summarize', 'parsedmarc', '9.10.2'),
    'shap': ('features.attribute', 'shap', '0.52.0'),
    'statsforecast': ('series.forecast', 'statsforecast', '2.0.4'),
    'opendp': ('count.privatize', 'opendp', '0.15.2'),
    'splink': ('records.link', 'splink', '4.0.16'),
    'ibis': ('campaigns.summarize', 'ibis-framework', '12.0.0'),
    'advertools': ('keywords.generate', 'advertools', '0.17.1'),
    'dnstwist': ('domain.permutations', 'dnstwist', '20250130'),
}
EXTRA = {}

FIELDS = {
    'networkx': (('edges',), ('top',)),
    'statsmodels': (('values',), ()),
    'polars': (('currency', 'rows'), ()),
    'ibis': (('currency', 'rows'), ()),
    'sqlglot': (('sql', 'dialect'), ()),
    'faker': (('count', 'seed', 'locale'), ()),
    'pandera': (('rows', 'schema'), ()),
    'datasketch': (('documents',), ('threshold',)),
    'h3': (('points',), ('resolution',)),
    'lifelines': (('durations', 'observed'), ()),
    'pyod': (('rows',), ('contamination',)),
    'river': (('values',), ()),
    'numpy-financial': (('currency', 'rate', 'cashflows_minor'), ()),
    'nashpy': (('payoffs_row', 'payoffs_column'), ()),
    'pymcdm': (('alternatives', 'weights', 'criteria'), ()),
    'mlxtend': (('baskets',), ('min_support',)),
    'arrow': (('rows',), ()),
    'markitdown': (('html',), ()),
    'great-tables': (('title', 'rows'), ()),
    'spacy': (('text', 'language'), ()),
    'parsedmarc': (('xml',), ()),
    'shap': (('train_x', 'train_y'), ()),
    'statsforecast': (('values', 'horizon', 'season_length'), ()),
    'opendp': (('true_count', 'epsilon'), ()),
    'splink': (('records',), ('threshold',)),
    'advertools': (('products', 'words'), ('match_types',)),
    'dnstwist': (('domain',), ('limit',)),
}
DIALECTS = ('duckdb', 'postgres', 'mysql', 'sqlite', 'bigquery', 'clickhouse')
MATCH_TYPES = ('Exact', 'Phrase', 'Modified', 'Broad')
DOMAIN = re.compile(r'^(?=.{4,100}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?){1,3}$')


def validate(service, operation, p):
    from .common import VerdugoError, fields, identifier, integer
    from .local_runtime import finite, string, matrix, labels, validate as base_validate
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported analytics local operation')
    required, optional = FIELDS[service]
    try:
        fields(p, ('dataset',) + required, optional)
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerdugoError('Analytics input must be finite JSON') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit demo or real dataset is required')

    def series(value, low, high, bound=1e9):
        if not isinstance(value, list) or not low <= len(value) <= high:
            raise VerdugoError('Provide %d..%d numeric values' % (low, high))
        for v in value:
            finite(v, -bound, bound)
        return value

    def scalar(value):
        if value is None or type(value) is bool:
            return
        if type(value) in (int, float):
            finite(value, -1e15, 1e15)
        elif not isinstance(value, str) or len(value) > 200 or '\x00' in value:
            raise VerdugoError('Cells must be null, boolean, bounded number or short text')

    def table(rows, max_rows, max_columns, same_keys=True):
        if not isinstance(rows, list) or not 1 <= len(rows) <= max_rows:
            raise VerdugoError('Provide 1..%d rows' % max_rows)
        keys = None
        for row in rows:
            if not isinstance(row, dict) or not 1 <= len(row) <= max_columns:
                raise VerdugoError('Rows must be flat objects with bounded columns')
            for name, value in row.items():
                identifier(name)
                scalar(value)
            if same_keys and keys is not None and set(row) != keys:
                raise VerdugoError('Every row must have the same columns')
            keys = set(row) if keys is None else keys

    def strings(value, low, high, limit=60):
        if not isinstance(value, list) or not low <= len(value) <= high:
            raise VerdugoError('Provide %d..%d short texts' % (low, high))
        for item in value:
            string(item, limit)
        if len(set(value)) != len(value):
            raise VerdugoError('Duplicate texts are not allowed')

    if service == 'networkx':
        edges = p['edges']
        if not isinstance(edges, list) or not 1 <= len(edges) <= 2000:
            raise VerdugoError('Provide 1..2000 edges')
        for edge in edges:
            if not isinstance(edge, list) or len(edge) != 2:
                raise VerdugoError('Each edge is a [source, target] pair')
            identifier(edge[0])
            identifier(edge[1])
        integer(p.get('top', 10), 1, 50)
    elif service in ('statsmodels', 'river'):
        values = series(p['values'], 8 if service == 'statsmodels' else 30, 500 if service == 'statsmodels' else 2000)
        if len(set(values)) < 2:
            raise VerdugoError('A constant series has no trend or drift to estimate')
    elif service in ('polars', 'ibis'):
        base_validate('duckdb', 'campaigns.aggregate', p)
    elif service == 'sqlglot':
        string(p['sql'], 4000)
        if p['dialect'] not in DIALECTS:
            raise VerdugoError('Supported SQL dialect must be explicit')
    elif service == 'faker':
        if p['dataset'] != 'demo':
            raise VerdugoError('Synthetic contacts are demo data only')
        integer(p['count'], 1, 100)
        integer(p['seed'], 0, 10**6)
        if p['locale'] not in ('es_MX', 'en_US'):
            raise VerdugoError('Supported locale must be es_MX or en_US')
    elif service == 'pandera':
        schema = p['schema']
        if not isinstance(schema, dict) or not 1 <= len(schema) <= 20:
            raise VerdugoError('Provide a schema with 1..20 columns')
        for name, spec in schema.items():
            identifier(name)
            fields(spec, ('type', 'nullable'), ('minimum', 'maximum'))
            if spec['type'] not in ('int', 'float', 'str', 'bool') or type(spec['nullable']) is not bool:
                raise VerdugoError('Column type must be int, float, str or bool with boolean nullable')
            for bound in ('minimum', 'maximum'):
                if bound in spec:
                    if spec['type'] not in ('int', 'float'):
                        raise VerdugoError('Bounds apply only to numeric columns')
                    finite(spec[bound], -1e15, 1e15)
        table(p['rows'], 500, 20, same_keys=False)
        if any(set(row) - set(schema) for row in p['rows']):
            raise VerdugoError('Rows contain columns that are not in the schema')
    elif service == 'datasketch':
        documents = p['documents']
        if not isinstance(documents, list) or not 2 <= len(documents) <= 50:
            raise VerdugoError('Provide 2..50 documents')
        seen = set()
        for doc in documents:
            fields(doc, ('id', 'content'))
            if identifier(doc['id']) in seen:
                raise VerdugoError('Duplicate document ID')
            seen.add(doc['id'])
            string(doc['content'], 4000)
        finite(p.get('threshold', 0.8), 0.3, 1.0)
    elif service == 'h3':
        points = p['points']
        if not isinstance(points, list) or not 1 <= len(points) <= 2000:
            raise VerdugoError('Provide 1..2000 points')
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise VerdugoError('Each point is a [latitude, longitude] pair')
            finite(point[0], -90, 90)
            finite(point[1], -180, 180)
        integer(p.get('resolution', 8), 0, 15)
    elif service == 'lifelines':
        durations = series(p['durations'], 10, 2000, 1e6)
        if any(v <= 0 for v in durations):
            raise VerdugoError('Durations must be positive')
        observed = p['observed']
        if not isinstance(observed, list) or len(observed) != len(durations) or \
                any(type(v) is not int or v not in (0, 1) for v in observed):
            raise VerdugoError('Observed flags must be 0/1 integers, one per duration')
    elif service == 'pyod':
        matrix(p['rows'], 20)
        finite(p.get('contamination', 0.1), 0.01, 0.4)
    elif service == 'numpy-financial':
        if p['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('Supported currency must be explicit: MXN, USD or EUR')
        finite(p['rate'], -0.99, 10)
        flows = p['cashflows_minor']
        if not isinstance(flows, list) or not 2 <= len(flows) <= 240:
            raise VerdugoError('Provide 2..240 cash flows')
        for flow in flows:
            integer(flow, -10**12, 10**12)
    elif service == 'nashpy':
        width = matrix(p['payoffs_row'])
        if matrix(p['payoffs_column']) != width or len(p['payoffs_row']) != len(p['payoffs_column']):
            raise VerdugoError('Both payoff matrices must have the same shape')
        if not 2 <= width <= 6 or not 2 <= len(p['payoffs_row']) <= 6:
            raise VerdugoError('Games are limited to 2..6 strategies per player')
    elif service == 'pymcdm':
        weights = series(p['weights'], 1, 10, 1)
        if any(w <= 0 for w in weights) or abs(sum(weights) - 1) > 1e-6:
            raise VerdugoError('Weights must be positive and sum to 1')
        criteria = p['criteria']
        if not isinstance(criteria, list) or len(criteria) != len(weights) or \
                any(c not in ('benefit', 'cost') for c in criteria):
            raise VerdugoError('Each criterion must be benefit or cost')
        alternatives = p['alternatives']
        if not isinstance(alternatives, list) or not 2 <= len(alternatives) <= 50:
            raise VerdugoError('Provide 2..50 alternatives')
        seen = set()
        for item in alternatives:
            fields(item, ('id', 'values'))
            if identifier(item['id']) in seen:
                raise VerdugoError('Duplicate alternative ID')
            seen.add(item['id'])
            series(item['values'], len(weights), len(weights))
        for index in range(len(weights)):
            if len({item['values'][index] for item in alternatives}) < 2:
                raise VerdugoError('Every criterion needs at least two distinct values')
    elif service == 'mlxtend':
        baskets = p['baskets']
        if not isinstance(baskets, list) or not 5 <= len(baskets) <= 1000:
            raise VerdugoError('Provide 5..1000 baskets')
        items = set()
        for basket in baskets:
            if not isinstance(basket, list) or not 1 <= len(basket) <= 30 or len(set(map(str, basket))) != len(basket):
                raise VerdugoError('Each basket holds 1..30 distinct item identifiers')
            for item in basket:
                items.add(identifier(item))
        if len(items) > 60:
            raise VerdugoError('At most 60 distinct items are supported')
        finite(p.get('min_support', 0.3), 0.05, 1)
    elif service == 'arrow':
        table(p['rows'], 1000, 20)
    elif service == 'great-tables':
        string(p['title'], 200)
        table(p['rows'], 100, 10)
    elif service in ('markitdown', 'parsedmarc'):
        document = string(p['html' if service == 'markitdown' else 'xml'], 20000)
        lowered = document.lower()
        if '<!entity' in lowered or (service == 'parsedmarc' and '<!doctype' in lowered):
            raise VerdugoError('Entity or DOCTYPE declarations are not supported')
    elif service == 'spacy':
        string(p['text'], 16000)
        if p['language'] not in ('es', 'en'):
            raise VerdugoError('Supported language must be es or en')
    elif service == 'shap':
        matrix(p['train_x'], 20)
        labels(p['train_y'], len(p['train_x']), minimum_per_class=5)
    elif service == 'statsforecast':
        values = series(p['values'], 24, 500)
        integer(p['horizon'], 1, 36)
        integer(p['season_length'], 1, min(52, len(values) // 2))
    elif service == 'opendp':
        integer(p['true_count'], 0, 10**9)
        finite(p['epsilon'], 0.01, 10)
    elif service == 'splink':
        records = p['records']
        if not isinstance(records, list) or not 2 <= len(records) <= 200:
            raise VerdugoError('Provide 2..200 records')
        seen = set()
        for record in records:
            fields(record, ('id',), ('name', 'email', 'phone'))
            if identifier(record['id']) in seen:
                raise VerdugoError('Duplicate record ID')
            seen.add(record['id'])
            for key in ('name', 'email', 'phone'):
                if record.get(key) is not None:
                    string(record[key], 200)
        finite(p.get('threshold', 0.5), 0.01, 0.999)
    elif service == 'advertools':
        strings(p['products'], 1, 20)
        strings(p['words'], 1, 20)
        match_types = p.get('match_types', ['Exact', 'Phrase'])
        if not isinstance(match_types, list) or not match_types or len(set(match_types)) != len(match_types) or \
                any(m not in MATCH_TYPES for m in match_types):
            raise VerdugoError('Match types must be a distinct subset of Exact, Phrase, Modified, Broad')
    elif service == 'dnstwist':
        if not isinstance(p['domain'], str) or not DOMAIN.fullmatch(p['domain']):
            raise VerdugoError('A lowercase registrable domain name is required')
        integer(p.get('limit', 100), 1, 500)


def run(service, p):
    return {'networkx': rank_graph, 'statsmodels': fit_trend, 'polars': summarize_polars,
            'ibis': summarize_ibis, 'sqlglot': inspect_sql, 'faker': synthesize_contacts,
            'pandera': validate_rows, 'datasketch': near_duplicates, 'h3': index_points,
            'lifelines': estimate_retention, 'pyod': detect_outliers, 'river': detect_stream_drift,
            'numpy-financial': evaluate_cashflow, 'nashpy': solve_game, 'pymcdm': rank_alternatives,
            'mlxtend': mine_baskets, 'arrow': summarize_table, 'markitdown': html_to_markdown,
            'great-tables': render_table, 'spacy': segment_text, 'parsedmarc': summarize_dmarc,
            'shap': attribute_features, 'statsforecast': forecast_series, 'opendp': privatize_count,
            'splink': link_records, 'advertools': generate_keywords, 'dnstwist': permute_domain}[service](p)


def _num(value, digits=8):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return round(value, digits) if math.isfinite(value) else None


def _campaigns(rows, currency):
    channels = []
    for row in rows:
        leads, conversions = int(row['leads']), int(row['conversions'])
        channels.append({'channel': str(row['channel']), 'spend_minor': int(row['spend_minor']),
                         'revenue_minor': int(row['revenue_minor']), 'leads': leads,
                         'conversions': conversions,
                         'conversion_rate': round(conversions / leads, 6) if leads else None})
    return {'currency': currency, 'channels': channels,
            'totals': {key: sum(c[key] for c in channels)
                       for key in ('spend_minor', 'revenue_minor', 'leads', 'conversions')},
            'bank_reconciled': False, 'source': 'operator_supplied_rows'}


def rank_graph(p):
    import networkx as nx
    graph = nx.DiGraph()
    graph.add_edges_from((a, b) for a, b in p['edges'])
    scores = nx.pagerank(graph, alpha=0.85)
    top = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:p.get('top', 10)]
    return {'nodes': graph.number_of_nodes(), 'edges': graph.number_of_edges(),
            'top': [{'id': k, 'pagerank': round(float(v), 6)} for k, v in top],
            'without_inbound': sorted(n for n, d in graph.in_degree() if d == 0)[:50],
            'without_outbound': sorted(n for n, d in graph.out_degree() if d == 0)[:50],
            'crawled_anything': False}


def fit_trend(p):
    import numpy as np
    import statsmodels.api as sm
    y = np.asarray(p['values'], dtype=float)
    fit = sm.OLS(y, sm.add_constant(np.arange(len(y), dtype=float))).fit()
    return {'observations': int(len(y)), 'slope_per_step': _num(fit.params[1]),
            'intercept': _num(fit.params[0]), 'r_squared': _num(fit.rsquared),
            'slope_p_value': _num(fit.pvalues[1]), 'forecast_guarantee': False}


def summarize_polars(p):
    import polars as pl
    frame = pl.DataFrame(p['rows'])
    grouped = frame.group_by('channel').agg(
        pl.col('spend_minor').sum(), pl.col('revenue_minor').sum(),
        pl.col('leads').sum(), pl.col('conversions').sum()).sort('channel')
    return _campaigns(grouped.to_dicts(), p['currency'])


def summarize_ibis(p):
    import ibis
    import pyarrow as pa
    table = ibis.memtable(pa.Table.from_pylist(p['rows']))
    expr = table.group_by('channel').aggregate(
        spend_minor=table.spend_minor.sum(), revenue_minor=table.revenue_minor.sum(),
        leads=table.leads.sum(), conversions=table.conversions.sum()).order_by('channel')
    return _campaigns(expr.to_pyarrow().to_pylist(), p['currency'])


def inspect_sql(p):
    import sqlglot
    from sqlglot import exp
    writes = {'insert', 'update', 'delete', 'drop', 'create', 'alter', 'altertable', 'merge',
              'command', 'truncatetable', 'copy', 'grant', 'set', 'use', 'transaction',
              'commit', 'rollback', 'into', 'pragma', 'attach', 'detach'}
    trees = [tree for tree in sqlglot.parse(p['sql'], read=p['dialect']) if tree is not None]
    kinds, tables, read_only = [], set(), bool(trees)
    for tree in trees:
        kinds.append(tree.key)
        if tree.key not in ('select', 'union', 'intersect', 'except') or \
                any(node.key in writes for node in tree.find_all(exp.Expression)):
            read_only = False
        tables.update(t.name for t in tree.find_all(exp.Table) if t.name)
    return {'statements': len(trees), 'statement_kinds': kinds[:20], 'read_only': read_only,
            'tables': sorted(tables)[:100], 'dialect': p['dialect'], 'executed': False}


def synthesize_contacts(p):
    from faker import Faker
    fake = Faker(p['locale'])
    fake.seed_instance(p['seed'])
    contacts = [{'name': fake.name(), 'email': fake.safe_email(), 'company': fake.company()}
                for _ in range(p['count'])]
    return {'contacts': contacts, 'synthetic': True, 'real_people': False}


def validate_rows(p):
    import pandas as pd
    from pandera.errors import SchemaErrors
    try:
        import pandera.pandas as pa
    except ImportError:
        import pandera as pa
    kinds = {'int': 'Int64', 'float': 'Float64', 'str': 'string', 'bool': 'boolean'}
    columns = {}
    for name, spec in p['schema'].items():
        checks = []
        if 'minimum' in spec:
            checks.append(pa.Check.ge(spec['minimum']))
        if 'maximum' in spec:
            checks.append(pa.Check.le(spec['maximum']))
        columns[name] = pa.Column(kinds[spec['type']], checks=checks, nullable=spec['nullable'], coerce=True)
    frame = pd.DataFrame(p['rows'], columns=list(p['schema']))
    failures = []
    try:
        pa.DataFrameSchema(columns, strict=True).validate(frame, lazy=True)
    except SchemaErrors as error:
        counts = {}
        cases = error.failure_cases
        for column, check in zip(cases['column'], cases['check']):
            key = (str(column), str(check)[:80])
            counts[key] = counts.get(key, 0) + 1
        failures = [{'column': c, 'check': k, 'count': n} for (c, k), n in sorted(counts.items())]
    return {'rows': len(frame), 'valid': not failures, 'failures': failures[:100],
            'failed_checks': sum(f['count'] for f in failures), 'values_returned': False}


def near_duplicates(p):
    from datasketch import MinHash

    def sketch(text):
        tokens = text.lower().split()
        sketch_ = MinHash(num_perm=128)
        for i in range(max(1, len(tokens) - 2)):
            sketch_.update(' '.join(tokens[i:i + 3]).encode('utf-8'))
        return sketch_
    sketches = [(doc['id'], sketch(doc['content'])) for doc in p['documents']]
    threshold = p.get('threshold', 0.8)
    pairs = []
    for i in range(len(sketches)):
        for j in range(i + 1, len(sketches)):
            score = float(sketches[i][1].jaccard(sketches[j][1]))
            if score >= threshold:
                pairs.append({'a': sketches[i][0], 'b': sketches[j][0], 'estimated_jaccard': round(score, 4)})
    pairs.sort(key=lambda r: (-r['estimated_jaccard'], r['a'], r['b']))
    return {'documents': len(sketches), 'threshold': threshold, 'pairs': pairs[:200],
            'pairs_found': len(pairs), 'estimate_not_exact': True}


def index_points(p):
    import h3
    to_cell = getattr(h3, 'latlng_to_cell', None) or h3.geo_to_h3
    resolution = p.get('resolution', 8)
    counts = {}
    for latitude, longitude in p['points']:
        cell = str(to_cell(latitude, longitude, resolution))
        counts[cell] = counts.get(cell, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return {'points': len(p['points']), 'resolution': resolution, 'cells': len(counts),
            'top_cells': [{'cell': c, 'count': n} for c, n in top], 'coordinates_returned': False}


def estimate_retention(p):
    from lifelines import KaplanMeierFitter
    fitter = KaplanMeierFitter().fit(p['durations'], event_observed=p['observed'])
    horizon = max(p['durations'])
    steps = [round(horizon * i / 4, 6) for i in range(1, 5)]
    return {'subjects': len(p['durations']), 'events': sum(p['observed']),
            'median_survival': _num(fitter.median_survival_time_),
            'survival': [{'t': t, 'probability': _num(fitter.predict(t))} for t in steps],
            'causal_claim': False}


def detect_outliers(p):
    import numpy as np
    from pyod.models.ecod import ECOD
    model = ECOD(contamination=p.get('contamination', 0.1))
    model.fit(np.asarray(p['rows'], dtype=float))
    flagged = [i for i, v in enumerate(model.labels_) if int(v) == 1]
    return {'rows': len(p['rows']), 'outliers': len(flagged), 'outlier_indices': flagged[:200],
            'method': 'ECOD', 'ground_truth_available': False}


def detect_stream_drift(p):
    from river import drift, stats
    mean, variance, detector, changes = stats.Mean(), stats.Var(), drift.ADWIN(), []
    for index, value in enumerate(p['values']):
        mean.update(value)
        variance.update(value)
        detector.update(value)
        if detector.drift_detected:
            changes.append(index)
    return {'observations': len(p['values']), 'mean': _num(mean.get()), 'variance': _num(variance.get()),
            'drifts': len(changes), 'drift_indices': changes[:100], 'detector': 'ADWIN',
            'cause_identified': False}


def evaluate_cashflow(p):
    import numpy_financial as npf
    flows = p['cashflows_minor']
    cumulative, payback = 0, None
    for index, flow in enumerate(flows):
        cumulative += flow
        if payback is None and cumulative >= 0:
            payback = index
    return {'currency': p['currency'], 'periods': len(flows), 'rate_per_period': p['rate'],
            'npv_minor': int(round(float(npf.npv(p['rate'], flows)))),
            'irr_per_period': _num(npf.irr(flows)), 'payback_period': payback,
            'investment_advice': False}


def solve_game(p):
    import warnings
    import numpy as np
    import nashpy
    game = nashpy.Game(np.asarray(p['payoffs_row'], dtype=float), np.asarray(p['payoffs_column'], dtype=float))
    found = []
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for row, column in game.support_enumeration():
            found.append({'row_strategy': [round(float(v), 6) for v in row],
                          'column_strategy': [round(float(v), 6) for v in column]})
            if len(found) == 20:
                break
    return {'shape': [len(p['payoffs_row']), len(p['payoffs_row'][0])], 'equilibria': found,
            'equilibria_found': len(found), 'real_world_prediction': False}


def rank_alternatives(p):
    import numpy as np
    from pymcdm.methods import TOPSIS
    matrix = np.asarray([item['values'] for item in p['alternatives']], dtype=float)
    types = np.asarray([1 if c == 'benefit' else -1 for c in p['criteria']])
    scores = TOPSIS()(matrix, np.asarray(p['weights'], dtype=float), types)
    order = sorted(zip((item['id'] for item in p['alternatives']), scores), key=lambda kv: (-float(kv[1]), kv[0]))
    return {'method': 'TOPSIS', 'ranking': [{'id': k, 'score': round(float(v), 6)} for k, v in order],
            'weights_are_operator_judgement': True}


def mine_baskets(p):
    import pandas as pd
    from mlxtend.frequent_patterns import apriori
    from mlxtend.preprocessing import TransactionEncoder
    encoder = TransactionEncoder()
    frame = pd.DataFrame(encoder.fit(p['baskets']).transform(p['baskets']), columns=encoder.columns_)
    found = apriori(frame, min_support=p.get('min_support', 0.3), use_colnames=True, max_len=3)
    rows = [{'items': sorted(str(i) for i in items), 'support': round(float(support), 6)}
            for support, items in zip(found['support'], found['itemsets'])]
    rows.sort(key=lambda r: (-r['support'], len(r['items']), r['items']))
    return {'baskets': len(p['baskets']), 'itemsets_found': len(rows), 'itemsets': rows[:100],
            'causal_claim': False}


def summarize_table(p):
    import pyarrow as pa
    import pyarrow.compute as pc
    table = pa.Table.from_pylist(p['rows'])
    columns = []
    for name in table.column_names:
        column = table[name]
        info = {'name': name, 'type': str(column.type), 'nulls': int(column.null_count)}
        if pa.types.is_integer(column.type) or pa.types.is_floating(column.type):
            bounds = pc.min_max(column).as_py()
            info.update(minimum=bounds['min'], maximum=bounds['max'])
        columns.append(info)
    return {'rows': table.num_rows, 'columns': columns, 'values_returned': False}


def html_to_markdown(p):
    import io
    from markitdown import MarkItDown
    result = MarkItDown(enable_plugins=False).convert_stream(
        io.BytesIO(p['html'].encode('utf-8')), file_extension='.html')
    text = result.text_content
    return {'markdown': text[:60000], 'characters': len(text), 'fetched_remote_content': False}


def render_table(p):
    import pandas as pd
    from great_tables import GT
    html = GT(pd.DataFrame(p['rows'])).tab_header(title=p['title']).as_raw_html()
    return {'rows': len(p['rows']), 'html': html, 'html_bytes': len(html.encode('utf-8')),
            'contains_supplied_values': True, 'published': False}


def segment_text(p):
    import spacy
    nlp = spacy.blank(p['language'])
    nlp.add_pipe('sentencizer')
    doc = nlp(p['text'])
    counts = {}
    for token in doc:
        if token.is_alpha and not token.is_stop and len(token.text) > 2:
            counts[token.lower_] = counts.get(token.lower_, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return {'language': p['language'], 'sentences': sum(1 for _ in doc.sents), 'tokens': len(doc),
            'top_terms': [{'term': t, 'count': n} for t, n in top], 'trained_model_loaded': False}


def summarize_dmarc(p):
    import parsedmarc
    report = parsedmarc.parse_aggregate_report_xml(p['xml'], offline=True)
    total = aligned = 0
    dispositions = {}
    for record in report['records']:
        count = int(record['count'])
        total += count
        if record['alignment']['dmarc']:
            aligned += count
        disposition = str(record['policy_evaluated']['disposition'])[:20]
        dispositions[disposition] = dispositions.get(disposition, 0) + count
    published = report['policy_published']
    return {'domain': str(published['domain'])[:255], 'published_policy': str(published['p'])[:20],
            'messages': total, 'dmarc_aligned': aligned, 'dmarc_failed': total - aligned,
            'dispositions': dispositions, 'source_ips_returned': False, 'dns_lookups_made': False}


def attribute_features(p):
    import numpy as np
    import shap
    from sklearn.ensemble import GradientBoostingClassifier
    x = np.asarray(p['train_x'], dtype=float)
    model = GradientBoostingClassifier(n_estimators=30, max_depth=2, random_state=0)
    model.fit(x, np.asarray(p['train_y'], dtype=int))
    values = np.asarray(shap.TreeExplainer(model).shap_values(x))
    if values.ndim == 3:
        values = values[..., -1]
    importance = np.abs(values).mean(axis=0)
    total = float(importance.sum()) or 1.0
    return {'rows': int(x.shape[0]), 'model': 'GradientBoostingClassifier',
            'features': [{'index': i, 'mean_abs_shap': round(float(v), 6), 'share': round(float(v) / total, 6)}
                         for i, v in enumerate(importance)],
            'in_sample_only': True, 'causal_claim': False}


def forecast_series(p):
    import numpy as np
    from statsforecast.models import HistoricAverage, SeasonalNaive
    y = np.asarray(p['values'], dtype=np.float64)
    horizon = p['horizon']
    seasonal = SeasonalNaive(season_length=p['season_length']).forecast(y=y, h=horizon)['mean']
    average = HistoricAverage().forecast(y=y, h=horizon)['mean']
    return {'observations': int(len(y)), 'horizon': horizon,
            'seasonal_naive': [round(float(v), 6) for v in seasonal],
            'historic_average': [round(float(v), 6) for v in average],
            'baseline_models_only': True, 'forecast_guarantee': False}


def privatize_count(p):
    import opendp.prelude as dp
    dp.enable_features('contrib')
    scale = 1.0 / p['epsilon']
    mechanism = dp.m.make_laplace(dp.atom_domain(T=int), dp.absolute_distance(T=int), scale=scale)
    return {'noisy_count': int(mechanism(p['true_count'])), 'epsilon': _num(mechanism.map(1), 6),
            'scale': round(scale, 6), 'sensitivity': 1, 'mechanism': 'discrete Laplace',
            'true_count_returned': False}


def link_records(p):
    import pandas as pd
    import splink.comparison_library as cl
    from splink import DuckDBAPI, Linker, SettingsCreator, block_on
    frame = pd.DataFrame([{'unique_id': r['id'], 'name': r.get('name'), 'email': r.get('email'),
                           'phone': r.get('phone')} for r in p['records']])
    settings = SettingsCreator(
        link_type='dedupe_only', probability_two_random_records_match=0.01,
        comparisons=[cl.JaroWinklerAtThresholds('name', [0.9, 0.8]), cl.ExactMatch('email'), cl.ExactMatch('phone')],
        blocking_rules_to_generate_predictions=[block_on('email'), block_on('phone'), block_on('name')])
    linker = Linker(frame, settings, db_api=DuckDBAPI())
    scored = linker.inference.predict(threshold_match_probability=p.get('threshold', 0.5)).as_pandas_dataframe()
    pairs = [{'a': min(str(a), str(b)), 'b': max(str(a), str(b)), 'match_probability': round(float(m), 6)}
             for a, b, m in zip(scored['unique_id_l'], scored['unique_id_r'], scored['match_probability'])]
    pairs.sort(key=lambda r: (-r['match_probability'], r['a'], r['b']))
    return {'records': len(frame), 'pairs_found': len(pairs), 'candidate_pairs': pairs[:200],
            'model_trained_on_this_data': False, 'merged_anything': False}


def generate_keywords(p):
    import advertools as adv
    frame = adv.kw_generate(products=p['products'], words=p['words'], max_len=3,
                            match_types=p.get('match_types', ['Exact', 'Phrase']))
    rows = [{'campaign': str(a), 'ad_group': str(b), 'keyword': str(c), 'match_type': str(d)}
            for a, b, c, d in zip(frame['Campaign'], frame['Ad Group'], frame['Keyword'], frame['Criterion Type'])]
    return {'keywords': len(rows), 'sample': rows[:200], 'campaigns_created': False, 'spend_executed': False}


def permute_domain(p):
    import dnstwist
    fuzzer = dnstwist.Fuzzer(p['domain'])
    fuzzer.generate()
    rows = [{'technique': str(d.get('fuzzer')), 'domain': str(d.get('domain'))} for d in fuzzer.permutations()]
    rows = [r for r in rows if r['technique'] != '*original' and r['domain'] != p['domain']]
    techniques = {}
    for row in rows:
        techniques[row['technique']] = techniques.get(row['technique'], 0) + 1
    return {'domain': p['domain'], 'permutations': len(rows), 'by_technique': techniques,
            'sample': rows[:p.get('limit', 100)], 'dns_lookups_made': False, 'registration_checked': False}
