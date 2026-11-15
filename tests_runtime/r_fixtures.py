CASES = {
    'pricesensitivitymeter': {'dataset': 'demo', 'currency': 'MXN', 'responses': [
        {'toocheap': 5+i, 'cheap': 10+2*i, 'expensive': 20+2*i, 'tooexpensive': 30+2*i}
        for i in range(6)]},
    'robyn': {'dataset': 'demo', 'spend': [100, 0, 0, 0], 'theta': 0.5, 'alpha': 1, 'gamma': 0.5},
}


def assert_result(test, sid, value):
    if sid == 'pricesensitivitymeter':
        test.assertEqual(6, value['responses'])
        test.assertEqual({'lower': 10, 'upper': 30}, value['acceptable_range'])
        test.assertEqual(20, value['indifference_point'])
        test.assertEqual(10, value['optimal_price_point'])
        test.assertFalse(value['revenue_optimum_verified'])
    else:
        test.assertEqual([100, 50, 25, 12.5], value['adstock'])
        for received, expected in zip(value['saturation'], [16/25, 8/17, 4/13, 2/11]):
            test.assertAlmostEqual(expected, received, places=12)
        test.assertFalse(value['model_fitted'])
        test.assertFalse(value['causal_effect_demonstrated'])
