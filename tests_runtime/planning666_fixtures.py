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
    elif sid == 'servers':
        test.assertEqual(3, r['entity_count'])
        test.assertEqual(2, r['unique_relation_count'])
        test.assertEqual(1, r['duplicate_relations_skipped'])
        test.assertEqual(1, r['matching_entity_count'])
        test.assertEqual(2, r['matching_incident_relation_count'])
        test.assertTrue(r['temporary_server_restart_verified'])
        test.assertTrue(r['sdk_graph_deleted'])
    elif sid == 'openmanus':
        test.assertEqual(1, r['status_counts']['blocked'])
        test.assertEqual('simulate', r['first_incomplete_stage'])
        test.assertTrue(r['sdk_plan_deleted'])
        test.assertFalse(r['operator_approval_verified'])
    else:
        test.assertEqual(-3, r['difference_from_median'])
        test.assertEqual('review_shortfall', r['review_recommendation'])
        test.assertFalse(r['remote_telemetry_enabled'])

CASES["openmanus"] = {"dataset": "demo", "statuses": ["completed", "completed", "completed", "blocked", "not_started"]}

CASES["servers"] = {"dataset":"demo", "statuses":["completed","blocked","not_started"], "edges":[[0,1],[2,1],[0,1]], "query":"blocked"}
