"""The pilot baseline has no model, no real market proof and no outside effects."""
import copy
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import objectives, workflow
from verdugo.common import VerdugoError, digest
from verdugo.engine import Engine
from verdugo.mcp import invoke, tool_definitions

ROOT = Path(__file__).resolve().parents[1]
GOAL = {'dataset': 'demo', 'target_clients': 20, 'horizon_days': 30,
        'budget_minor': 0, 'currency': 'MXN', 'channels': [
            {'channel': 'referral', 'contacts_available': 300, 'cost_per_contact_minor': 0,
             'history_contacts': 200, 'history_clients': 20}]}


def command(operation='objective.simulate', key='simulation'):
    params = {'goal': copy.deepcopy(GOAL)}
    if operation == 'objective.simulate':
        params['seed'] = 666
    return {'service': 'core', 'operation': operation, 'params': params, 'key': key}


def approve(state, plan, tenant='nexus'):
    with closing(Engine(state, tenant=tenant, role='approver', actor='synthetic-test-approver')) as reviewer:
        return reviewer.approve(plan['key'], plan['fingerprint'])


class ObjectiveMathTests(unittest.TestCase):
    def test_intervals_are_nontrivial_and_simulation_is_reproducible(self):
        params = {'goal': copy.deepcopy(GOAL), 'seed': 666}
        r = objectives.simulate(params)
        self.assertEqual(r, objectives.simulate(params))
        self.assertEqual(200, r['planned_contacts'])
        self.assertEqual(0, r['simulated_cost_minor'])
        lo, hi = r['actions'][0]['history_rate_interval_95']
        self.assertLess(lo, .1)
        self.assertGreater(hi, .1)
        q = r['clients_quantiles']
        self.assertLess(q['p05'], q['p50'])
        self.assertLess(q['p50'], q['p95'])
        self.assertEqual(128, r['simulations'])
        self.assertFalse(r['local_model_used'])
        self.assertFalse(r['calibrated_to_real_market'])
        self.assertFalse(r['forecast_is_guarantee'])
        self.assertTrue(r['dry_run'])

    def test_budget_capacity_and_combined_exposure_are_bounded(self):
        goal = copy.deepcopy(GOAL)
        goal['target_clients'] = 10000
        goal['budget_minor'] = 997
        goal['channels'][0].update(cost_per_contact_minor=10, contacts_available=20000)
        r = objectives.plan(goal)
        self.assertEqual(99, r['planned_contacts'])
        self.assertEqual(990, r['simulated_cost_minor'])
        self.assertFalse(r['target_feasible_under_point_assumptions'])
        goal['channels'] = [dict(goal['channels'][0], channel=name, cost_per_contact_minor=0)
                            for name in sorted(objectives.CHANNELS)]
        r = objectives.plan(goal)
        self.assertEqual(20000, r['planned_contacts'])
        self.assertEqual(0, r['simulated_cost_minor'])

    def test_zero_success_history_is_not_reported_as_impossible_truth(self):
        goal = copy.deepcopy(GOAL)
        goal['channels'][0]['history_clients'] = 0
        r = objectives.plan(goal)
        self.assertEqual(0, r['planned_contacts'])
        self.assertGreater(r['actions'][0]['history_rate_interval_95'][1], 0)
        self.assertFalse(r['target_feasible_under_point_assumptions'])
        self.assertFalse(r['forecast_is_guarantee'])

    def test_schema_rejects_private_data_destinations_credentials_and_real_claims(self):
        mutations = [
            lambda g: g.update(dataset='real'),
            lambda g: g.update(target_clients=True),
            lambda g: g.update(target_clients=float('inf')),
            lambda g: g.update(horizon_days=0),
            lambda g: g.update(budget_minor=-1),
            lambda g: g.update(client_name='private-name'),
            lambda g: g.update(model='remote-provider'),
            lambda g: g['channels'][0].update(url='https://example.invalid'),
            lambda g: g['channels'][0].update(token='private-token'),
            lambda g: g['channels'][0].update(history_clients=201),
            lambda g: g['channels'][0].update(history_contacts=0),
            lambda g: g['channels'].append(copy.deepcopy(g['channels'][0])),
        ]
        for i, mutate in enumerate(mutations):
            goal = copy.deepcopy(GOAL)
            mutate(goal)
            with self.subTest(mutation=i), self.assertRaises((VerdugoError, ValueError)):
                objectives.plan(goal)


class ObjectiveEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = str(Path(self.temp.name) / 'engine.sqlite3')
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def engine(self, **kwargs):
        config = {'tenants': {'nexus': {'services': {}}, 'other': {'services': {}}}}
        return Engine(self.state, config=config, transport=lambda *args: self.calls.append(args), **kwargs)

    def test_preview_requires_separate_approval_and_no_network(self):
        with patch('socket.socket', side_effect=AssertionError('network attempted')):
            with closing(self.engine()) as engine:
                cmd = command()
                preview = engine.execute(cmd)
                self.assertTrue(preview['requires_approval'])
                self.assertEqual(0, engine.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0])
                blocked = engine.execute(cmd, True)
                self.assertEqual('awaiting_approval', blocked['state'])
                with self.assertRaises(VerdugoError):
                    engine.approve(preview['key'], preview['fingerprint'])
            approve(self.state, preview)
            with closing(self.engine()) as engine:
                done = engine.execute(cmd, True)
                self.assertEqual('succeeded', done['state'])
                self.assertEqual(1, engine.db.execute('SELECT used FROM plans WHERE key=?', (cmd['key'],)).fetchone()[0])
        self.assertEqual([], self.calls)

    def test_restart_replay_preserves_result_and_never_resimulates(self):
        with closing(self.engine()) as engine:
            cmd = command()
            p = engine.plan(cmd)
        approve(self.state, p)
        with closing(self.engine()) as engine:
            original = engine.execute(cmd, True)
        with closing(self.engine()) as engine, patch.object(objectives, 'simulate', side_effect=AssertionError('rerun')):
            replay = engine.execute(cmd, True)
            self.assertTrue(replay['replayed'])
            self.assertEqual(original['result'], replay['result'])
            self.assertEqual(1, engine.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0])

    def test_approval_is_exact_and_expiry_blocks_execution(self):
        with closing(self.engine()) as engine:
            cmd = command()
            p = engine.plan(cmd)
        approve(self.state, p)
        with closing(self.engine()) as engine:
            changed = copy.deepcopy(cmd)
            changed['params']['seed'] = 1
            with self.assertRaises(VerdugoError):
                engine.execute(changed, True)
            with engine.transaction():
                engine.db.execute('UPDATE plans SET expires=0 WHERE key=?', (cmd['key'],))
            self.assertEqual('awaiting_approval', engine.execute(cmd, True)['state'])

    def test_changed_algorithm_cannot_consume_an_older_approval(self):
        with closing(self.engine()) as engine:
            cmd = command()
            p = engine.plan(cmd)
        approve(self.state, p)
        with closing(self.engine()) as engine, patch.object(objectives, 'implementation_digest', return_value='0'*64):
            with self.assertRaises(VerdugoError):
                engine.execute(cmd, True)
            self.assertEqual(0, engine.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0])

    def test_other_tenant_and_viewer_cannot_use_approval(self):
        with closing(self.engine()) as engine:
            cmd = command()
            p = engine.plan(cmd)
        approve(self.state, p)
        with closing(self.engine(tenant='other')) as engine:
            self.assertEqual('awaiting_approval', engine.execute(cmd, True)['state'])
        with closing(self.engine(role='viewer')) as engine:
            with self.assertRaises(VerdugoError):
                engine.execute(cmd, True)

    def test_measurement_uses_saved_simulation_and_checks_exposure_and_tenant(self):
        with closing(self.engine()) as engine:
            cmd = command()
            p = engine.plan(cmd)
        approve(self.state, p)
        measurement = {'service': 'core', 'operation': 'objective.measure', 'key': 'measure',
                       'params': {'simulation_key': cmd['key'], 'observed_contacts': 200,
                                  'observed_clients': 17, 'dataset': 'demo'}}
        with closing(self.engine()) as engine:
            simulated = engine.execute(cmd, True)['result']
            measured = engine.execute(measurement, True)
            self.assertEqual('succeeded', measured['state'])
            r = measured['result']
            self.assertEqual(digest(simulated), r['simulation_result_digest'])
            self.assertEqual(17-simulated['clients_quantiles']['p50'], r['difference_from_simulated_median'])
            self.assertEqual(0, r['real_clients_verified'])
            mismatch = copy.deepcopy(measurement)
            mismatch['key'] = 'other-exposure'
            mismatch['params']['observed_contacts'] = 199
            self.assertEqual('failed', engine.execute(mismatch, True)['state'])
        with closing(self.engine(tenant='other')) as engine:
            self.assertEqual('failed', engine.execute(measurement, True)['state'])

    def test_other_core_results_are_not_accepted_as_simulations(self):
        with closing(self.engine()) as engine:
            engine.execute(command('objective.plan', 'not-simulation'), True)
            p = {'simulation_key': 'not-simulation', 'observed_contacts': 200,
                 'observed_clients': 10, 'dataset': 'demo'}
            with self.assertRaises(VerdugoError):
                objectives.measure(engine, p)

    def test_same_workflow_cli_mcp_and_database_are_used(self):
        spec = json.loads((ROOT / 'examples/objective666.synthetic.json').read_text())
        with closing(self.engine()) as engine:
            planned = invoke(engine, 'verdugo_workflow', {'workflow': spec})
            self.assertEqual(1, len(planned['approval_batch']))
            blocked = workflow.run(engine, spec, True, include_evidence=True)
            self.assertEqual('paused', blocked['state'])
            self.assertEqual('simulate', blocked['step'])
            self.assertEqual('awaiting_approval', blocked['outcome']['state'])
        with closing(self.engine(role='approver')) as engine:
            engine.approve_many(planned['approval_batch'])
        with closing(self.engine()) as engine:
            done = invoke(engine, 'verdugo_workflow', {'workflow': spec, 'execute': True})
            self.assertEqual('succeeded', done['state'])
            self.assertEqual({'plan', 'simulate', 'measure'}, set(done['steps']))
            self.assertFalse(done['steps']['measure']['real_revenue_verified'])
        proc = subprocess.run([sys.executable, '-m', 'verdugo', '--state', self.state,
                               'workflow', '@'+str(ROOT/'examples/objective666.synthetic.json'), '--execute'],
                              cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual('succeeded', json.loads(proc.stdout)['state'])
        self.assertEqual(25, len(tool_definitions()))
        self.assertFalse(any('approve' in t['name'] for t in tool_definitions()))
        self.assertEqual([], self.calls)
