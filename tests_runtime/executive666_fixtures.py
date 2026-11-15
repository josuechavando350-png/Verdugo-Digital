"""Aggregate synthetic input for the first two executive SDKs."""
GOAL = {'dataset':'demo', 'target_clients':20, 'horizon_days':30,
        'budget_minor':0, 'currency':'MXN', 'channels':[
            {'channel':'referral', 'contacts_available':300, 'cost_per_contact_minor':0,
             'history_contacts':200, 'history_clients':20}]}
CASES = {'agno': {'dataset':'demo', 'goal':GOAL},
         'ag2': {'dataset':'demo', 'currency':'MXN', 'budget_minor':50,
                 'actions':[{'channel':'referral','contacts':10,'cost_per_contact_minor':6}]}}


def assert_result(test, service, value):
    test.assertEqual(service, value['original_sdk'])
    test.assertFalse(value['autonomous_agent'])
    test.assertEqual(0, value['llm_calls'])
    test.assertGreater(value['reviewed_modules_verified'], 0)
    if service == 'agno':
        test.assertEqual(200, value['planned_contacts'])
        test.assertEqual(2, value['fixed_sdk_steps'])
        test.assertTrue(value['budget_checked'])
        test.assertFalse(value['telemetry_enabled'])
    else:
        test.assertEqual(60, value['planned_cost_minor'])
        test.assertFalse(value['within_budget'])
        test.assertFalse(value['feasible_under_declared_limits'])
        test.assertFalse(value['external_execution_authorized'])
