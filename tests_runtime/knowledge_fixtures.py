CASES = {
    'langgraph-supervisor': {'dataset': 'demo', 'text': 'Analyze the supplied campaign totals.'},
    'mem0': {'dataset': 'demo', 'versions': ['Initial report', 'Reviewed report']},
    'pysd': {'dataset': 'demo', 'x': [0, 10, 20], 'y': [0, 100, 150], 'queries': [5, 15]},
    'pymc-marketing': {'dataset': 'demo', 'spend': [1, 0, 0], 'alpha': 0.5, 'lags': 3},
    'graphrag': {'dataset': 'demo', 'edges': [
        {'source': 'a', 'target': 'b', 'weight': 1}, {'source': 'b', 'target': 'c', 'weight': 1}, {'source': 'a', 'target': 'c', 'weight': 1},
        {'source': 'd', 'target': 'e', 'weight': 1}, {'source': 'e', 'target': 'f', 'weight': 1}, {'source': 'd', 'target': 'f', 'weight': 1}]},
    'forecasting-tools': {'dataset': 'demo', 'lower': 0, 'upper': 100,
        'percentiles': [{'percentile': 0, 'value': 0}, {'percentile': 0.5, 'value': 50}, {'percentile': 1, 'value': 100}], 'targets': [0.25, 0.75]},
    'indexnow-for-python': {'dataset': 'demo', 'xml': '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.invalid/a</loc></url><url><loc>https://example.invalid/b</loc></url></urlset>'},
    'waybackpy': {'dataset': 'demo', 'timestamp': '20260102030405', 'original_url': 'https://example.invalid/article', 'status': 200, 'digest': 'A'*32, 'length': 1234},
    'ipranges': {'dataset': 'demo', 'addresses': ['66.249.64.1', '192.0.2.1']},
    'the-great-gpt-firewall': {'dataset': 'demo', 'domains': ['www.bbc.com', 'example.invalid']},
}


def assert_result(t, sid, r):
    if sid == 'langgraph-supervisor':
        t.assertEqual('verdugo_analysis', r['destination']); t.assertEqual(3, r['message_count']); t.assertFalse(r['destination_executed'])
    elif sid == 'mem0':
        t.assertEqual(2, r['versions']); t.assertEqual('Reviewed report', r['latest']); t.assertTrue(r['readback_verified'])
    elif sid == 'pysd':
        t.assertEqual([50., 125.], r['values']); t.assertFalse(r['dynamic_model_simulated'])
    elif sid == 'pymc-marketing':
        t.assertEqual([1., 0.5, 0.25], r['carryover']); t.assertFalse(r['parameters_fitted']); t.assertFalse(r['causal_effect_proven'])
    elif sid == 'graphrag':
        t.assertEqual(6, r['nodes_covered']); t.assertEqual(2, r['community_count'])
        t.assertEqual({frozenset('abc'), frozenset('def')}, {frozenset(row['nodes']) for row in r['communities']})
    elif sid == 'forecasting-tools':
        t.assertEqual([25., 75.], [row['value'] for row in r['percentiles']]); t.assertFalse(r['forecast_generated']); t.assertFalse(r['published'])
    elif sid == 'indexnow-for-python':
        t.assertEqual(2, r['locations']); t.assertEqual(1, r['distinct_hosts']); t.assertEqual(0, r['submitted_to_search_engines'])
    elif sid == 'waybackpy':
        t.assertEqual('2026-01-02T03:04:05Z', r['captured_at']); t.assertEqual(1234, r['declared_bytes']); t.assertFalse(r['capture_authenticity_verified'])
    elif sid == 'ipranges':
        t.assertEqual([True, False], r['matches']); t.assertEqual(41, r['ranges_in_snapshot']); t.assertFalse(r['crawler_identity_verified'])
    elif sid == 'the-great-gpt-firewall':
        t.assertTrue(r['domains'][0]['recorded_gptbot_block']); t.assertFalse(r['domains'][1]['in_snapshot']); t.assertFalse(r['permission_granted'])
    else: t.fail('Missing knowledge assertions: '+sid)
