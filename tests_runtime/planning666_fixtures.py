"""Synthetic original graph, formal process and review fixtures."""
STAGES = ['plan', 'limits', 'operator_review', 'simulate', 'measure']
CASES = {
    'harness-sdk': {'dataset': 'demo', 'budget_minor': 50, 'capacity_contacts': 20,
                    'actions': [{'contacts': 10, 'cost_per_contact_minor': 6}]},
    'unified-planning': {'dataset': 'demo', 'sequence': STAGES,
                         'limits_satisfied': True, 'hypothetical_review_available': True},
    'voltagent': {'dataset': 'demo', 'target_clients': 20, 'simulated_median': 20,
                  'observed_clients': 17, 'observed_contacts': 200},
}


def assert_result(test, sid, r):
    test.assertEqual(sid, r['original_sdk'])
    test.assertEqual(0, r['llm_calls'])
    test.assertFalse(r['external_execution_authorized'])
    test.assertTrue(r['operator_approval_required'])
    if sid == 'harness-sdk':
        test.assertEqual(60, r['planned_cost_minor'])
        test.assertFalse(r['within_budget'])
        test.assertTrue(r['within_capacity'])
        test.assertEqual('revise_limits', r['recommendation'])
        test.assertTrue(r['join_dependencies_verified'])
    elif sid == 'unified-planning':
        test.assertTrue(r['sequence_valid'])
        test.assertEqual(5, r['validated_transition_count'])
        test.assertFalse(r['operator_approval_verified'])
    else:
        test.assertEqual(-3, r['difference_from_median'])
        test.assertEqual('review_shortfall', r['review_recommendation'])
        test.assertFalse(r['remote_telemetry_enabled'])
