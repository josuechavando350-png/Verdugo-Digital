"""Synthetic analytical inputs and independently checkable expected results."""
import math

CAMPAIGNS = {'dataset': 'demo', 'currency': 'MXN', 'rows': [
    {'channel': 'organic', 'spend_minor': 100, 'revenue_minor': 500, 'leads': 4, 'conversions': 1},
    {'channel': 'organic', 'spend_minor': 200, 'revenue_minor': 700, 'leads': 6, 'conversions': 2},
    {'channel': 'referral', 'spend_minor': 0, 'revenue_minor': 300, 'leads': 1, 'conversions': 1}]}
X = [[i / 10] for i in range(40)]
Y = [1 + 2 * r[0] for r in X]
REGRESSION = {'dataset': 'demo', 'train_x': X, 'train_y': Y, 'score_x': [[1], [2]]}
CASES = {
    **{sid: CAMPAIGNS for sid in ('arrow', 'polars', 'ibis', 'great-tables')},
    'markitdown': {'dataset': 'demo', 'html': '<html><body><h1>Nexus</h1><p>Appointment analysis.</p></body></html>'},
    'spacy': {'dataset': 'demo', 'text': 'Hola Nexus. Tenemos dos citas.'},
    'networkx': {'dataset': 'demo', 'nodes': ['intake', 'qualify', 'report'], 'edges': [['intake', 'qualify'], ['qualify', 'report']]},
    'sqlglot': {'dataset': 'demo', 'dialect': 'postgres'},
    'faker': {'dataset': 'demo', 'count': 3, 'seed': 42},
    'statsmodels': REGRESSION, 'shap': REGRESSION,
    'mapie': {**REGRESSION, 'calibration_x': [[i / 10 + 0.02] for i in range(30)],
              'calibration_y': [1+2*(i/10+0.02) + (i%3-1)*0.1 for i in range(30)]},
    'causal-learn': {'dataset': 'demo', 'rows': [[math.sin(i), math.cos(i)] for i in range(100)]},
    'numpy-financial': {'dataset': 'demo', 'currency': 'MXN', 'rate': 0.1, 'cashflows': [-100, 60, 60]},
    'datasketch': {'dataset': 'demo', 'left': ['a', 'b', 'c'], 'right': ['b', 'c', 'd']},
    'nashpy': {'dataset': 'demo', 'row_payoffs': [[1, -1], [-1, 1]], 'column_payoffs': [[-1, 1], [1, -1]]},
    'pymcdm': {'dataset': 'demo', 'rows': [[1, 3], [2, 2], [3, 1]], 'weights': [0.5, 0.5], 'directions': [1, -1]},
    'h3': {'dataset': 'demo', 'locations': [[19.4326, -99.1332], [19.4326, -99.1332]], 'resolution': 7},
    'mlxtend': {'dataset': 'demo', 'baskets': [['a', 'b'], ['a', 'b'], ['a', 'c']], 'minimum_support': 0.5},
    'lifelines': {'dataset': 'demo', 'durations': [1, 2, 3, 4], 'events': [True, True, True, True], 'times': [0, 1, 2, 4]},
    'pyod': {'dataset': 'demo', 'reference': [[i/100] for i in range(30)], 'current': [[0.1], [10]]},
    'pandera': {'dataset': 'demo', 'rows': [[1, 2], [3, None], [5, 20]], 'minimum': 0, 'maximum': 10},
    'river': {'dataset': 'demo', 'values': [1, 2, 3, 4]},
    'statsforecast': {'dataset': 'demo', 'values': [1, 2, 3, 4], 'horizon': 3},
}


def assert_result(t, sid, r):
    if sid in ('arrow', 'polars', 'ibis'):
        t.assertEqual([{'channel': 'organic', 'spend_minor': 300, 'revenue_minor': 1200, 'leads': 10, 'conversions': 3},
                       {'channel': 'referral', 'spend_minor': 0, 'revenue_minor': 300, 'leads': 1, 'conversions': 1}], r['channels'])
        t.assertFalse(r['bank_reconciled'])
    elif sid == 'markitdown':
        t.assertIn('# Nexus', r['markdown']); t.assertIn('Appointment analysis.', r['markdown'])
    elif sid == 'spacy':
        t.assertEqual(2, r['sentences']); t.assertEqual(7, r['lexical_units']); t.assertFalse(r['trained_model_loaded'])
    elif sid == 'networkx':
        t.assertTrue(r['acyclic']); t.assertEqual(['intake', 'qualify', 'report'], r['execution_order'])
        t.assertEqual(2, r['ancestor_counts']['report'])
    elif sid == 'sqlglot':
        t.assertIn('GROUP BY channel', r['query']); t.assertFalse(r['executed'])
    elif sid == 'faker':
        t.assertEqual(3, len(r['rows'])); t.assertTrue(r['synthetic'])
        t.assertTrue(all(x['email'].endswith('@example.invalid') for x in r['rows']))
    elif sid == 'statsmodels':
        for actual, expected in zip(r['predictions'], [3, 5]): t.assertAlmostEqual(expected, actual)
        t.assertAlmostEqual(1, r['in_sample_r_squared'])
    elif sid == 'shap':
        t.assertTrue(r['additivity_verified']); t.assertEqual(2, len(r['feature_contributions']))
        for terms, prediction in zip(r['feature_contributions'], r['predictions']):
            t.assertAlmostEqual(prediction, r['base_value']+sum(terms))
        t.assertNotEqual(0, r['feature_contributions'][0][0])
    elif sid == 'mapie':
        for point, bounds, expected in zip(r['predictions'], r['intervals'], [3, 5]):
            t.assertAlmostEqual(expected, point); t.assertLess(bounds[0], point); t.assertGreater(bounds[1], point)
        t.assertFalse(r['independent_coverage_measured'])
    elif sid == 'causal-learn':
        t.assertGreater(r['p_value'], 0.5); t.assertFalse(r['causal_direction_identified'])
    elif sid == 'numpy-financial':
        t.assertAlmostEqual(-100+60/1.1+60/1.21, r['net_present_value']); t.assertFalse(r['bank_reconciled'])
    elif sid == 'datasketch':
        t.assertEqual(0.5, r['exact_jaccard']); t.assertAlmostEqual(0.5, r['estimated_jaccard'], delta=0.15)
    elif sid == 'nashpy':
        t.assertEqual(1, len(r['equilibria']))
        t.assertEqual([0.5, 0.5], r['equilibria'][0]['row_strategy'])
        t.assertEqual([0.5, 0.5], r['equilibria'][0]['column_strategy'])
    elif sid == 'pymcdm':
        t.assertEqual([2, 1, 0], r['order']); t.assertEqual([0, 0.5, 1], r['scores'])
    elif sid == 'h3':
        t.assertEqual(1, len(r['cells'])); t.assertEqual(2, r['cells'][0]['count'])
    elif sid == 'mlxtend':
        patterns = {tuple(x['items']): x['support'] for x in r['patterns']}
        t.assertEqual(1, patterns[('a',)]); t.assertAlmostEqual(2/3, patterns[('a', 'b')])
        t.assertNotIn(('c',), patterns)
    elif sid == 'lifelines':
        for expected, observed in zip([1, 0.75, 0.5, 0], r['survival']): t.assertAlmostEqual(expected, observed)
        t.assertEqual(2, r['median_duration'])
    elif sid == 'pyod':
        t.assertLess(r['scores'][0], r['scores'][1]); t.assertEqual([0, 1], r['flags'])
    elif sid == 'pandera':
        t.assertFalse(r['valid']); t.assertEqual(2, r['failure_count'])
    elif sid == 'great-tables':
        t.assertIn('<table', r['html']); t.assertIn('organic', r['html']); t.assertEqual(3, r['rows'])
        t.assertEqual(64, len(r['sha256']))
    elif sid == 'river':
        t.assertEqual(2.5, r['mean']); t.assertAlmostEqual(5/3, r['sample_variance'])
    elif sid == 'statsforecast':
        t.assertEqual([4, 4, 4], r['predictions']); t.assertFalse(r['accuracy_validated'])
    else:
        t.fail('Missing result assertions for '+sid)
