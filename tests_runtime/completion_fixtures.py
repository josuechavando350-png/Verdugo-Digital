CASES = {
    'meridian': {'dataset':'demo','media':[0,10,0,0],'alpha':0.5,'max_lag':2,'half_saturation':5,'slope':1},
    'tfcausalimpact': {'dataset':'demo','control':[10+(i%5)*2+(i%3) for i in range(40)],
        'outcome':[3*(10+(i%5)*2+(i%3))+(i%4)*0.2+(8 if i>=30 else 0) for i in range(40)],
        'intervention_index':30,'assumptions_reviewed':True},
    'vanna': {'dataset': 'demo', 'currency': 'MXN', 'rows': [
        {'channel': 'organic', 'spend_minor': 100, 'revenue_minor': 300, 'leads': 3, 'conversions': 1},
        {'channel': 'organic', 'spend_minor': 50, 'revenue_minor': 400, 'leads': 2, 'conversions': 1}]},
    'trendspyg': {'dataset': 'demo', 'traffic': ['2K+', '1.5M+', '50,000+', '0']},
    'youtube-comment-downloader': {'dataset': 'demo', 'threads': [
        {'id': 'a', 'likes': 2, 'replies': 1}, {'id': 'b', 'likes': 4, 'replies': 0}]},
    'comtradeapicall': {'dataset': 'demo', 'groups': [
        {'id': 'NORTH', 'countries': [484, 840]}, {'id': 'SOUTH', 'countries': [32, 76]}], 'selection': ['SOUTH', 'NORTH']},
    'browser-use': {'dataset': 'demo', 'allowed': ['*.example.org'],
                    'hosts': ['example.org', 'shop.example.org', 'example.org.evil.org']},
    'storm': {'dataset': 'demo', 'text': 'Evidence [1] and missing [4]. Grouped [1, 2].', 'reference_count': 2},
}

CASES['dbt'] = CASES['vanna']

from pathlib import Path
import base64
CASES['c2pa'] = {'dataset': 'demo', 'secret_text': base64.b64encode(
    (Path(__file__).parent/'fixtures/c2pa/signed-test.png').read_bytes()).decode()}
CASES['a2a'] = {'dataset': 'demo', 'tasks': [{'id': 'lead-a', 'state': 'completed'},
                                          {'id': 'lead-b', 'state': 'working'}]}
CASES['gpt-researcher'] = {'dataset': 'demo', 'query': 'solar energy',
                          'passages': ['solar energy grows', 'banana prices', 'solar battery']}

CASES.update({
    'cognee': {'dataset': 'demo', 'text': 'Solar energy. Market demand!'},
    'autogeo': {'dataset': 'demo', 'source_count': 2, 'sentences': [
        {'tokens': ['solar', 'energy'], 'citations': [0]}, {'tokens': ['market', 'demand'], 'citations': [1]}]},
    'claude-skills-c-level': {'dataset': 'demo', 'currency': 'MXN', 'cash_minor': 1000, 'mrr_minor': 100,
                            'opex_minor': 200, 'gross_margin': 0.8, 'growth_rate': 0, 'months': 3},
})

def assert_result(test, sid, result):
    if sid == 'meridian':
        for expected, actual in zip([0,40/7,20/7,10/7], result['adstock']):test.assertAlmostEqual(expected,actual,places=5)
        for expected, actual in zip([0,8/15,4/11,2/9], result['saturation']):test.assertAlmostEqual(expected,actual,places=5)
        test.assertFalse(result['causality_established'])
    elif sid == 'tfcausalimpact':
        test.assertEqual(30,result['pre_observations']);test.assertEqual(10,result['post_observations'])
        test.assertAlmostEqual(53.04,result['summary']['average']['actual'],places=3)
        # Stochastic posterior: test a broad scientific property, not exact RNG bytes.
        average=result['summary']['average']
        test.assertLess(average['predicted_lower'],average['predicted_upper'])
        test.assertGreater(average['abs_effect'],3);test.assertLess(average['abs_effect'],13)
        test.assertFalse(result['causality_established']);test.assertFalse(result['convergence_certified'])
    elif sid == 'gpt-researcher':
        test.assertEqual([0, 2, 1], result['ranking'])
        test.assertEqual(0, result['scores'][1])
        test.assertGreater(result['scores'][0], result['scores'][2])
        test.assertEqual(0, result['llm_calls'])
    elif sid == 'c2pa':
        test.assertTrue(result['embedded_manifest_found'])
        test.assertEqual(1, result['manifests'])
        test.assertEqual('0.92.0', result['native_sdk_version'])
        test.assertGreaterEqual(result['active_manifest_diagnostics']['failure'], 1)
        test.assertFalse(result['authenticity_certified'])
    elif sid == 'a2a':
        test.assertEqual(2, result['tasks'])
        test.assertEqual({'completed': 1, 'working': 1}, result['states'])
        test.assertFalse(result['agent_invoked'])
    elif sid == 'cognee':
        test.assertEqual(CASES[sid]['text'], ''.join(r['text'] for r in result['segments']))
        test.assertEqual(['word', 'sentence_end', 'word', 'sentence_end'], [r['boundary'] for r in result['segments']])
    elif sid == 'autogeo':
        test.assertEqual([0.5, 0.5], result['word_shares'])
        test.assertAlmostEqual(0.73105857863, result['position_word_shares'][0])
    elif sid == 'claude-skills-c-level':
        test.assertEqual([880, 760, 640], [r['cash_end_minor'] for r in result['months']])
        test.assertTrue(result['scenario_only'])
    elif sid in ('vanna', 'dbt'):
        test.assertEqual([{'channel': 'organic', 'spend_minor': 150, 'revenue_minor': 700,
                           'leads': 5, 'conversions': 2}], result['rows'])
        if sid == 'vanna': test.assertFalse(result['sql_generated'])
        else: test.assertEqual(2, result['dbt_nodes_succeeded'])
    elif sid == 'trendspyg':
        test.assertEqual([2000, 1500000, 50000, 0], result['minimum_volumes'])
    elif sid == 'youtube-comment-downloader':
        test.assertEqual(2, result['comments_in_input'])
        test.assertEqual(6, result['likes_in_input'])
        test.assertEqual(1, result['replies_in_input'])
    elif sid == 'comtradeapicall':
        test.assertEqual([{'label': '(SOUTH)', 'countries': [32, 76]},
                          {'label': '(NORTH)', 'countries': [484, 840]}], result['groups'])
    elif sid == 'browser-use':
        test.assertEqual([True, True, False], result['allowed_by_native_rules'])
        test.assertFalse(result['browser_launched'])
    elif sid == 'storm':
        test.assertEqual([1, 4], result['citation_indices'])
        test.assertEqual([4], result['out_of_range'])
        test.assertEqual('Evidence  and missing . Grouped .', result['text_without_citations'])
        test.assertFalse(result['citations_fact_checked'])
    else:
        test.fail('Missing native result assertions for ' + sid)
