"""Fixed synthetic cases. Values are not evidence of commercial performance."""
import random

_rng = random.Random(17)
_X = [[_rng.uniform(-1, 1), _rng.uniform(-1, 1)] for _ in range(240)]
_T = [i % 2 for i in range(240)]
_Y = [3.0*t + 1.5*x[0] - 0.75*x[1] for x, t in zip(_X, _T)]
CAUSAL = {'dataset': 'demo', 'covariates': _X, 'treatment': _T,
          'outcome': _Y, 'assumptions_acknowledged': True}
APPOINTMENTS = 'Appointment booking and calendar scheduling for a dental clinic.'
CASES = {
    'dlt': {'dataset': 'demo', 'currency': 'MXN', 'rows': [
        {'channel': 'organic', 'spend_minor': 100, 'revenue_minor': 500, 'leads': 4, 'conversions': 1},
        {'channel': 'organic', 'spend_minor': 200, 'revenue_minor': 700, 'leads': 6, 'conversions': 2},
        {'channel': 'referral', 'spend_minor': 0, 'revenue_minor': 300, 'leads': 1, 'conversions': 1}]},
    'langgraph': {'dataset': 'demo', 'leads': [
        {'id': 'ready', 'need_confirmed': True, 'budget_confirmed': True, 'authority_confirmed': True, 'decision_days': 7},
        {'id': 'later', 'need_confirmed': True, 'budget_confirmed': False, 'authority_confirmed': True, 'decision_days': 60},
        {'id': 'not-fit', 'need_confirmed': False, 'budget_confirmed': True, 'authority_confirmed': True, 'decision_days': 7}]},
    'llama-index': {'dataset': 'demo', 'query': 'appointment booking', 'top_k': 1, 'documents': [
        {'id': 'appointments', 'content': APPOINTMENTS},
        {'id': 'garden', 'content': 'Garden furniture with tables and chairs.'}]},
    'ragas': {'dataset': 'demo', 'retrieved_contexts': ['Garden furniture with tables and chairs.', APPOINTMENTS],
              'reference_contexts': [APPOINTMENTS]},
    'mlflow': {'dataset': 'demo', 'metrics': {'precision': 0.75, 'rows': 12}},
    'dowhy': CAUSAL,
    'econml': CAUSAL,
}


def assert_result(test, service, value):
    if service == 'dlt':
        test.assertEqual(3, value['loaded_rows'])
        test.assertEqual(300, value['channels'][0]['spend_minor'])
        test.assertEqual(1200, value['channels'][0]['revenue_minor'])
        test.assertEqual(10, value['channels'][0]['leads'])
        test.assertFalse(value['bank_reconciled'])
    elif service == 'langgraph':
        test.assertEqual(['ready'], value['qualified'])
        test.assertEqual(['later'], value['nurture'])
        test.assertEqual(['not-fit'], value['unqualified'])
        test.assertEqual({'qualified': 1, 'nurture': 1, 'unqualified': 1}, value['counts'])
        test.assertFalse(value['llm_called'])
        test.assertFalse(value['contacted_anyone'])
    elif service == 'llama-index':
        test.assertEqual('appointments', value['matches'][0]['id'])
        test.assertEqual([APPOINTMENTS], value['contexts'])
        test.assertFalse(value['llm_called'])
        test.assertFalse(value['embedding_model_loaded'])
    elif service == 'ragas':
        test.assertAlmostEqual(0.5, value['context_precision'], places=6)
        test.assertFalse(value['semantic_correctness_proven'])
        test.assertFalse(value['llm_called'])
    elif service == 'mlflow':
        test.assertEqual({'precision': 0.75, 'rows': 12.0}, value['metrics'])
        test.assertEqual('FINISHED', value['run_status'])
        test.assertTrue(value['readback_verified'])
        test.assertFalse(value['remote_tracking_used'])
    else:
        test.assertAlmostEqual(3.0, value['estimated_effect'], delta=0.5 if service == 'econml' else 0.00001)
        test.assertEqual(240, value['rows'])
        test.assertFalse(value['causal_assumptions_verified'])
        test.assertIsNone(value['commercial_success_probability'])
