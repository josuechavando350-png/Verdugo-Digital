"""Fixed scenarios and a failed synthetic target; no real market evidence."""
import copy
from executive666_fixtures import GOAL
SECOND=copy.deepcopy(GOAL)
SECOND['channels'][0]['contacts_available']=100
CASES={'griptape':{'dataset':'demo','goals':[copy.deepcopy(GOAL),SECOND]},
       'beeai-framework':{'dataset':'demo','budget_ok':True,'capacity_ok':True,
                         'observed_clients':17,'target_clients':20}}


def assert_result(test,service,value):
    test.assertEqual(service,value['original_sdk'])
    test.assertEqual(0,value['llm_calls'])
    test.assertFalse(value['external_execution_authorized'])
    if service=='griptape':
        test.assertEqual([0],value['pareto_nondominated_indices'])
        test.assertEqual([20.0,10.0],[x['conditional_expected_clients'] for x in value['scenarios']])
        test.assertFalse(value['real_market_optimality_proven'])
    else:
        test.assertEqual('revise_strategy',value['recommendation'])
        test.assertEqual(['assess','revise'],value['sdk_step_path'])
        test.assertTrue(value['operator_approval_required'])
