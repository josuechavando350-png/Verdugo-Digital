"""Synthetic aggregate claims, including a deliberately false revenue claim."""
CASES = {'langroid': {'dataset':'demo','currency':'MXN',
    'before':{'contacts':100,'clients':10,'spend_minor':1000,'revenue_minor':2000},
    'after':{'contacts':100,'clients':20,'spend_minor':1500,'revenue_minor':1300},
    'claims':['conversion_rate_increased','cost_per_client_decreased','revenue_above_ad_spend']}}


def assert_result(test, value):
    test.assertEqual(['supported','supported','contradicted'],[x['verdict'] for x in value['claims']])
    test.assertEqual('langroid',value['original_sdk'])
    test.assertEqual(0,value['llm_calls'])
    test.assertFalse(value['causality_established'])
    test.assertFalse(value['net_profit_verified'])
    test.assertFalse(value['autonomous_agent'])
