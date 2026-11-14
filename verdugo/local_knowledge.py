"""Original graph, memory, curve and provenance libraries on supplied data."""
import json

SPECS = {
    'langgraph-supervisor': ('handoff.prepare', 'langgraph-supervisor', '0.0.31'),
    'mem0': ('history.materialize', 'mem0ai', '2.2.1'),
    'pysd': ('curve.interpolate', 'pysd', '3.14.3'),
    'pymc-marketing': ('media.adstock', 'pymc-marketing', '1.4.0'),
    'graphrag': ('graph.cluster', 'graphrag', '3.3.0'),
    'forecasting-tools': ('distribution.interpolate', 'forecasting-tools', '0.3.7'),
    'indexnow-for-python': ('sitemap.inspect', 'index-now-for-python', '1.1.2'),
    'waybackpy': ('capture.describe', 'waybackpy', '3.0.6'),
}
PROFILES = {sid: ('MODELING' if sid in ('pysd', 'pymc-marketing') else
                 'GRAPH_FORECAST' if sid in ('graphrag', 'forecasting-tools') else 'KNOWLEDGE') for sid in SPECS}
EXTRA = {}


def validate(service, operation, p):
    from .common import fields, identifier, integer, VerdugoError
    from .local_runtime import string, finite
    if service not in SPECS or SPECS[service][0] != operation:
        raise VerdugoError('Unsupported knowledge operation')
    required = {'langgraph-supervisor': ('text',), 'mem0': ('versions',),
        'pysd': ('x', 'y', 'queries'), 'pymc-marketing': ('spend', 'alpha', 'lags'),
        'graphrag': ('edges',), 'forecasting-tools': ('percentiles', 'lower', 'upper', 'targets'),
        'indexnow-for-python': ('xml',), 'waybackpy': ('timestamp', 'original_url', 'status', 'digest', 'length')}
    try: fields(p, ('dataset', *required[service]))
    except (ValueError, TypeError, OverflowError) as exc: raise VerdugoError('Bounded finite JSON required') from exc
    if p['dataset'] not in ('demo', 'real'): raise VerdugoError('Explicit dataset required')

    def items(values, low=1, high=100):
        if not isinstance(values, list) or not low <= len(values) <= high: raise VerdugoError('Bounded list required')
        return values

    if service == 'langgraph-supervisor': string(p['text'], 8000)
    elif service == 'mem0':
        for text in items(p['versions'], high=20): string(text, 1500)
    elif service == 'pysd':
        for key in ('x', 'y', 'queries'):
            for value in items(p[key], low=2 if key in ('x', 'y') else 1): finite(value)
        if len(p['x']) != len(p['y']) or any(a >= b for a, b in zip(p['x'], p['x'][1:])):
            raise VerdugoError('Strictly increasing matching curve points required')
        if any(not p['x'][0] <= value <= p['x'][-1] for value in p['queries']):
            raise VerdugoError('Extrapolation is not supported')
    elif service == 'pymc-marketing':
        for value in items(p['spend'], low=3): finite(value, 0, 1e9)
        finite(p['alpha'], 0, 0.999); integer(p['lags'], 1, min(20, len(p['spend'])))
    elif service == 'graphrag':
        seen = set(); nodes = set()
        for row in items(p['edges'], low=2, high=200):
            fields(row, ('source', 'target', 'weight')); identifier(row['source']); identifier(row['target']); finite(row['weight'], 0.001, 1e6)
            key = tuple(sorted((row['source'], row['target'])))
            if key[0] == key[1] or key in seen: raise VerdugoError('Duplicate or self edge')
            seen.add(key); nodes.update(key)
        if len(nodes) > 80: raise VerdugoError('At most eighty graph nodes supported')
    elif service == 'forecasting-tools':
        finite(p['lower']); finite(p['upper'])
        if p['lower'] >= p['upper']: raise VerdugoError('Ordered bounds required')
        previous = (-1., -float('inf'))
        for row in items(p['percentiles'], low=2, high=20):
            fields(row, ('percentile', 'value')); finite(row['percentile'], 0, 1); finite(row['value'], p['lower'], p['upper'])
            if row['percentile'] <= previous[0] or row['value'] <= previous[1]: raise VerdugoError('Strictly increasing percentiles and values required')
            previous = (row['percentile'], row['value'])
        for value in items(p['targets'], high=20): finite(value, p['percentiles'][0]['percentile'], p['percentiles'][-1]['percentile'])
    elif service == 'indexnow-for-python':
        import xml.etree.ElementTree as ET
        string(p['xml'], 40000)
        if '<!DOCTYPE' in p['xml'].upper() or '<!ENTITY' in p['xml'].upper(): raise VerdugoError('XML declarations/entities forbidden')
        try: root = ET.fromstring(p['xml'])
        except ET.ParseError as exc: raise VerdugoError('Invalid sitemap XML') from exc
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        if root.tag != ns+'urlset' or not 1 <= len(root) <= 100 or len(list(root.iter())) > 1000:
            raise VerdugoError('Bounded sitemap urlset required')
        for row in root:
            loc = row.find(ns+'loc')
            if row.tag != ns+'url' or loc is None or not loc.text: raise VerdugoError('Each sitemap entry needs a location')
            _url(loc.text.strip())
    elif service == 'waybackpy':
        from datetime import datetime
        import re
        if not isinstance(p['timestamp'], str) or not re.fullmatch(r'[0-9]{14}', p['timestamp']): raise VerdugoError('Fourteen-digit timestamp required')
        try: datetime.strptime(p['timestamp'], '%Y%m%d%H%M%S')
        except ValueError as exc: raise VerdugoError('Invalid capture timestamp') from exc
        _url(p['original_url']); integer(p['status'], 100, 599); integer(p['length'], 1, 10**9)
        if not isinstance(p['digest'], str) or not re.fullmatch(r'[A-Z2-7]{32}', p['digest']): raise VerdugoError('Base32 SHA1 capture digest required')


def _url(value):
    from urllib.parse import urlsplit
    from .common import VerdugoError
    from .local_runtime import string
    string(value, 2048)
    try: parsed = urlsplit(value)
    except ValueError as exc: raise VerdugoError('Invalid location') from exc
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query or any(c.isspace() for c in value):
        raise VerdugoError('Only credential-free HTTP locations without query/fragment supported')
    return parsed


def handoff(p):
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph_supervisor.handoff import create_handoff_tool
    native = create_handoff_tool(agent_name='verdugo_analysis')
    state = {'messages': [HumanMessage(content=p['text']), AIMessage(content='', tool_calls=[{'name': native.name, 'args': {}, 'id': 'local-handoff'}])]}
    command = native.invoke({'type': 'tool_call', 'name': native.name, 'id': 'local-handoff', 'args': {'state': state}})
    if command.goto != 'verdugo_analysis': raise ValueError('Unexpected destination')
    return {'destination': command.goto, 'message_count': len(command.update['messages']),
            'command_prepared': True, 'destination_executed': False, 'model_calls': 0}


def history(p):
    from mem0.memory.storage import SQLiteManager
    manager = SQLiteManager(':memory:')
    try:
        old = None
        for i, value in enumerate(p['versions']):
            stamp = '2000-01-01T00:00:%02dZ' % i
            manager.add_history('local', old, value, 'ADD' if i == 0 else 'UPDATE', created_at=stamp, updated_at=stamp)
            old = value
        rows = manager.get_history('local')
        if [row['new_memory'] for row in rows] != p['versions']: raise ValueError('History readback mismatch')
        return {'versions': len(rows), 'latest': rows[-1]['new_memory'], 'readback_verified': True,
                'history_scope': 'temporary-local', 'durable_result_store': 'Engine', 'semantic_retrieval_performed': False}
    finally: manager.close()


def interpolate(p):
    from pysd.py_backend.lookups import HardcodedLookups
    curve = HardcodedLookups(p['x'], p['y'], {}, 'interpolate', {}, 'verdugo_curve')
    curve.initialize()
    return {'values': [float(curve(value)) for value in p['queries']], 'method': 'linear-lookup', 'dynamic_model_simulated': False}


def adstock(p):
    import os
    os.environ['PYTENSOR_FLAGS'] = 'cxx=,mode=FAST_COMPILE'
    import numpy as np
    import pytensor.tensor as pt
    import pytensor.xtensor as ptx
    from pymc_marketing.mmm.transformers import geometric_adstock
    x = ptx.as_xtensor(pt.as_tensor_variable(np.asarray(p['spend'], dtype=float)), dims=('time',))
    values = geometric_adstock(x, alpha=p['alpha'], l_max=p['lags'], normalize=False, dim='time').eval().tolist()
    return {'carryover': values, 'alpha_supplied': p['alpha'], 'lags': p['lags'],
            'parameters_fitted': False, 'causal_effect_proven': False}


def cluster(p):
    import pandas as pd
    from graphrag.index.operations.cluster_graph import cluster_graph
    result = cluster_graph(pd.DataFrame(p['edges']), max_cluster_size=10, use_lcc=False, seed=7)
    rows = [{'level': level, 'id': group, 'parent': parent, 'nodes': sorted(nodes)} for level, group, parent, nodes in result]
    return {'communities': sorted(rows, key=lambda x: (x['level'], x['id'])), 'community_count': len(rows),
            'nodes_covered': len(set(n for row in rows for n in row['nodes'])), 'model_calls': 0, 'text_extraction_performed': False}


def distribution(p):
    from forecasting_tools.data_models.numeric_report import NumericDistribution, Percentile
    model = NumericDistribution(declared_percentiles=[Percentile(**row) for row in p['percentiles']],
        open_upper_bound=False, open_lower_bound=False, lower_bound=p['lower'], upper_bound=p['upper'], zero_point=None)
    result = model.get_percentiles_at_target_heights(p['targets'])
    return {'percentiles': [{'percentile': row.percentile, 'value': row.value} for row in result],
            'forecast_generated': False, 'accuracy_verified': False, 'published': False}


def sitemap(p):
    import xml.etree.ElementTree as ET
    from index_now.submit.sitemap.parse import parse_sitemap_xml_and_get_urls
    urls = parse_sitemap_xml_and_get_urls(p['xml'])
    expected = [row.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text.strip() for row in ET.fromstring(p['xml'])]
    if urls != expected: raise ValueError('Sitemap parser mismatch')
    return {'locations': len(urls), 'distinct_hosts': len({_url(value).hostname for value in urls}),
            'submitted_to_search_engines': 0, 'locations_fetched': 0, 'raw_locations_returned': False}


def describe_capture(p):
    from waybackpy.cdx_snapshot import CDXSnapshot
    original = _url(p['original_url'])
    record = CDXSnapshot({'urlkey': original.hostname, 'timestamp': p['timestamp'], 'original': p['original_url'],
        'mimetype': 'text/html', 'statuscode': str(p['status']), 'digest': p['digest'], 'length': str(p['length'])})
    return {'archive_url': record.archive_url, 'captured_at': record.datetime_timestamp.isoformat()+'Z',
            'status': int(record.statuscode), 'declared_bytes': int(record.length),
            'capture_fetched': False, 'capture_authenticity_verified': False}


HANDLERS = {'langgraph-supervisor': handoff, 'mem0': history, 'pysd': interpolate,
            'pymc-marketing': adstock, 'graphrag': cluster, 'forecasting-tools': distribution,
            'indexnow-for-python': sitemap, 'waybackpy': describe_capture}


def run(service, params):
    return HANDLERS[service](params)
