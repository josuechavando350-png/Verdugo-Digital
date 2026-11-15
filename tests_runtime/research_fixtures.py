import math
from analytics_fixtures import CAMPAIGNS, REGRESSION

CASES = {
    'advertools': {'dataset': 'demo', 'texts': ['https://example.invalid/a https://example.invalid/b', 'no links', 'https://example.invalid/a']},
    'pywikibot': {'dataset': 'demo', 'text': 'Visible <!-- hidden --> content <nowiki>ignored</nowiki>.'},
    'splink': {'dataset': 'demo', 'records': [{'id': 'a', 'label': ' Nexus '}, {'id': 'b', 'label': 'nexus'}, {'id': 'c', 'label': 'Different'}]},
    'iceberg': CAMPAIGNS,
    'feast': {'dataset': 'demo', 'rows': [{'entity_id': 1, 'value': 2.5}, {'entity_id': 2, 'value': 7.0}]},
    'openlineage': {'dataset': 'demo', 'job': 'campaign-report', 'inputs': ['campaigns'], 'outputs': ['summary']},
    'causalml': {'dataset': 'demo', 'covariates': [[i/100, math.sin(i)] for i in range(80)],
                'treatment': [i%2 for i in range(80)],
                'outcome': [2+3*(i%2)+i/100+0.5*math.sin(i) for i in range(80)], 'assumptions_acknowledged': True},
    'ydata-profiling': {'dataset': 'demo', 'rows': [[1, 2], [3, None], [5, 6]]},
    'opendp': {'dataset': 'demo', 'sensitivity': 1, 'scale': 2.0},
    'flaml': REGRESSION, 'vowpal': REGRESSION,
    'recommenders': {'dataset': 'demo', 'relevant': ['a', 'c'], 'ranked': ['a', 'b', 'c'], 'k': 2},
    'py-ecomplexity': {'dataset': 'demo', 'rows': [
        {'location': loc, 'product': product, 'value': value}
        for loc, vals in [('a', [100, 20, 5]), ('b', [10, 100, 20]), ('c', [20, 10, 100])]
        for product, value in zip(['x', 'y', 'z'], vals)]},
    'osmnx': {'dataset': 'demo', 'nodes': ['a', 'b', 'c'],
             'edges': [{'from': 'a', 'to': 'b', 'length': 2}, {'from': 'b', 'to': 'c', 'length': 3},
                       {'from': 'a', 'to': 'c', 'length': 10}], 'origin': 'a', 'destination': 'c'},
    'mesa': {'dataset': 'demo', 'workers': 3, 'jobs': 20, 'steps': 4},
    'langchain': {'dataset': 'demo', 'text': ('Nexus records appointments. '*60).strip()},
    'pydantic-ai': {'dataset': 'demo', 'messages': [{'role': 'user', 'text': 'Report'}, {'role': 'assistant', 'text': 'Ready'}]},
    'dspy': {'dataset': 'demo', 'pairs': [{'reference': 'Paris', 'answer': 'Paris'}, {'reference': 'Madrid', 'answer': 'Rome'}]},
    'docling': {'dataset': 'demo', 'html': '<html><body><h1>Nexus</h1><p>Campaign report.</p></body></html>'},
    'pipecat': {'dataset': 'demo', 'left': [30000, -30000, 100], 'right': [30000, -30000, -100]},
    'whisper': {'dataset': 'demo', 'samples': [0]*800},
    'financetoolkit': {'dataset': 'demo', 'currency': 'MXN', 'current_assets': 200,
                      'current_liabilities': 100, 'cash': 50, 'securities': 20, 'receivables': 30},
    'a2a-python': {'dataset': 'demo', 'artifact_id': 'campaigns', 'text': 'Local report'},
    'mcp-python-sdk': {'dataset': 'demo', 'text': 'Local report', 'is_error': False},
}


def assert_result(t, sid, r):
    if sid == 'advertools':
        t.assertEqual([2, 0, 1], r['counts']); t.assertEqual(2, r['distinct_links']); t.assertFalse(r['urls_returned'])
    elif sid == 'pywikibot':
        t.assertNotIn('hidden', r['text']); t.assertNotIn('ignored', r['text']); t.assertIn('Visible', r['text'])
    elif sid == 'splink':
        t.assertEqual([['a', 'b']], r['candidate_pairs']); t.assertFalse(r['same_entity_proven'])
    elif sid == 'iceberg':
        t.assertEqual(3, r['rows']); t.assertEqual(1, r['snapshots']); t.assertTrue(r['readback_verified'])
    elif sid == 'feast':
        t.assertEqual([1, 2], r['entity_ids']); t.assertEqual([2.5, 7], r['values']); t.assertTrue(r['readback_verified'])
    elif sid == 'openlineage':
        t.assertEqual('campaign-report', r['event']['job']['name']); t.assertFalse(r['execution_attested']); t.assertFalse(r['sent'])
        t.assertEqual('campaigns', r['event']['inputs'][0]['name'])
    elif sid == 'causalml':
        t.assertAlmostEqual(3, r['estimated_effect'], places=5); t.assertFalse(r['causal_assumptions_verified'])
    elif sid == 'ydata-profiling':
        t.assertEqual(1, r['missing_cells']); t.assertEqual([0, 1], r['column_missing'])
    elif sid == 'opendp':
        t.assertAlmostEqual(0.5, r['epsilon_bound']); t.assertFalse(r['release_generated'])
    elif sid == 'flaml':
        t.assertEqual('rf', r['estimator']); t.assertEqual(2, len(r['predictions']))
        t.assertLess(r['predictions'][0], r['predictions'][1]); t.assertLess(r['validation_mse'], 4)
    elif sid == 'vowpal':
        t.assertEqual(2, len(r['predictions'])); t.assertLess(r['predictions'][0], r['predictions'][1])
        for expected, observed in zip([3, 5], r['predictions']): t.assertAlmostEqual(expected, observed, delta=1)
    elif sid == 'recommenders':
        t.assertEqual(0.5, r['precision_at_k']); t.assertEqual(0.5, r['recall_at_k'])
    elif sid == 'py-ecomplexity':
        t.assertEqual(9, len(r['cells'])); t.assertGreater(r['cells'][0]['rca'], 1)
        t.assertLess(r['cells'][1]['rca'], 1)
    elif sid == 'osmnx':
        t.assertEqual(['a', 'b', 'c'], r['path']); t.assertEqual(5, r['length'])
    elif sid == 'mesa':
        t.assertEqual(12, r['completed']); t.assertEqual(8, r['remaining']); t.assertTrue(r['simulation_only'])
    elif sid == 'langchain':
        t.assertGreater(r['count'], 1)
        for c in r['chunks']:
            t.assertLessEqual(len(c['text']), 500); t.assertGreaterEqual(c['start'], 0)
            t.assertEqual(c['text'], CASES[sid]['text'][c['start']:c['start']+len(c['text'])])
    elif sid == 'pydantic-ai':
        t.assertEqual(2, r['messages']); t.assertEqual(1, r['user_turns']); t.assertFalse(r['model_called'])
    elif sid == 'dspy':
        t.assertEqual([True, False], r['matches']); t.assertEqual(0.5, r['normalized_exact_match_rate'])
    elif sid == 'docling':
        t.assertIn('Nexus', r['markdown']); t.assertIn('Campaign report.', r['markdown']); t.assertFalse(r['ocr_executed'])
    elif sid == 'pipecat':
        t.assertEqual([32767, -32768, 0], r['samples'])
    elif sid == 'whisper':
        t.assertEqual(80, r['bands']); t.assertGreater(r['frames'], 0); t.assertFalse(r['speech_transcribed'])
        t.assertEqual(80, len(r['band_means'])); t.assertTrue(all(math.isfinite(v) for v in r['band_means']))
    elif sid == 'financetoolkit':
        t.assertEqual(2, r['current_ratio']); t.assertEqual(1, r['quick_ratio']); t.assertFalse(r['bank_reconciled'])
    elif sid == 'a2a-python':
        t.assertEqual('campaigns', r['artifact']['artifactId']); t.assertEqual('Local report', r['artifact']['parts'][0]['text']); t.assertFalse(r['sent'])
    elif sid == 'mcp-python-sdk':
        t.assertEqual('Local report', r['envelope']['content'][0]['text']); t.assertFalse(r['sent'])
    else:
        t.fail('Missing research assertions for '+sid)
