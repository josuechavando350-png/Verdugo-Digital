import copy
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_runtime
from verdugo.__main__ import template
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo import workflow

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests_runtime'))
from fixtures import CASES


class LocalContractTests(unittest.TestCase):
    def test_all_recipes_are_real_catalog_entries_and_have_strict_contracts(self):
        from verdugo.catalog import catalog
        ids = {r['id'] for r in catalog()}
        self.assertEqual(19, len(local_runtime.SPECS))
        self.assertTrue(set(local_runtime.SPECS) <= ids)
        for sid, (op, _, _) in local_runtime.SPECS.items():
            with self.subTest(sid=sid):
                local_runtime.validate(sid, op, CASES[sid])
                changed = dict(CASES[sid], shell='bad')
                with self.assertRaises(VerdugoError): local_runtime.validate(sid, op, changed)

    def test_no_dynamic_code_paths_queries_or_callback_fields(self):
        for name in ('sql', 'path', 'python', 'callback', 'url', 'token', 'tenant', 'execute'):
            p = dict(CASES['duckdb'], **{name: 'untrusted'})
            with self.subTest(name=name), self.assertRaises(VerdugoError):
                local_runtime.validate('duckdb', 'campaigns.aggregate', p)

    def test_unknown_operation_does_not_fall_back(self):
        with self.assertRaises(VerdugoError): local_runtime.validate('duckdb', 'sql.execute', {})
        with self.assertRaises(VerdugoError): local_runtime.validate('whisper', 'transcribe', {})

    def test_dataset_is_required_and_not_implicit(self):
        for value in ('production', '', None, True):
            p = dict(CASES['duckdb'], dataset=value)
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                local_runtime.validate('duckdb', 'campaigns.aggregate', p)

    def test_invalid_numeric_inputs_rejected(self):
        for value in (True, float('inf'), float('nan'), 10**500, '12'):
            with self.subTest(value=str(value)[:30]), self.assertRaises(VerdugoError):
                local_runtime.finite(value)

    def test_ragged_features_and_single_class_rejected(self):
        for changes in ({'train_x': [[1,2],[3]]}, {'train_y': [0]*40}, {'score_x': [[1,2,3]]}):
            with self.subTest(changes=list(changes)), self.assertRaises(VerdugoError):
                local_runtime.validate('scikit-learn', 'classifier.score', dict(CASES['scikit-learn'], **changes))

    def test_duplicate_optimization_ids_rejected(self):
        p = copy.deepcopy(CASES['or-tools']); p['items'][1]['id'] = 'alpha'
        with self.assertRaises(VerdugoError): local_runtime.validate('or-tools', 'selection.solve', p)

    def test_amounts_currency_and_conversion_definition_checked(self):
        for key, value in [('spend_minor', -1), ('leads', True), ('conversions', 500)]:
            p = copy.deepcopy(CASES['duckdb']); p['rows'][0][key] = value
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                local_runtime.validate('duckdb', 'campaigns.aggregate', p)
        with self.assertRaises(VerdugoError):
            local_runtime.validate('duckdb', 'campaigns.aggregate', dict(CASES['duckdb'], currency='mixed'))

    def test_missing_dependencies_never_report_success(self):
        with patch('verdugo.local_runtime.metadata.version', side_effect=importlib.metadata.PackageNotFoundError):
            self.assertIsNone(local_runtime.installed('duckdb')['installed'])
            with self.assertRaises(VerdugoError): local_runtime.preflight('duckdb','campaigns.aggregate',
                {'version': '1.5.6', 'runtime_reviewed': True})

    def test_explicit_version_runtime_review_and_resource_budget_required(self):
        for cfg in ({'version': 'latest'}, {'version': '1.5.6'},
                    {'version': '1.5.6','runtime_reviewed':True,'timeout_seconds':9999}):
            with self.subTest(cfg=cfg), self.assertRaises(VerdugoError):
                local_runtime.preflight('duckdb','campaigns.aggregate',cfg)

    def test_status_separates_source_http_local_and_live(self):
        e = Engine(':memory:')
        try: s = e.status()
        finally: e.close()
        self.assertEqual(322,s['source_pinned'])
        self.assertEqual(59,s['api_adapters_implemented'])
        self.assertEqual(19,s['local_adapters_implemented'])
        self.assertEqual(78,s['total_adapters_implemented'])
        self.assertEqual(244,s['projects_without_any_adapter'])
        self.assertEqual(0,s['live_verified'])

    def test_configuration_keeps_local_integrations_disabled(self):
        config=template('nexus')
        for sid,(_,_,version) in local_runtime.SPECS.items():
            cfg=config['tenants']['nexus']['services'][sid]
            self.assertIs(cfg['enabled'],False)
            self.assertIs(cfg['runtime_reviewed'],False)
            self.assertIs(cfg['license_reviewed'],False)
            self.assertEqual(version,cfg['version'])


class EngineDispatchTests(unittest.TestCase):
    def setUp(self):
        self.config = template('nexus')
        self.config['tenants']['nexus']['services']['duckdb'].update(
            enabled=True, license_reviewed=True, runtime_reviewed=True)
        self.version = patch('verdugo.local_runtime.metadata.version', return_value='1.5.6')
        self.version.start()
        self.engine = Engine(':memory:', self.config)
        self.command = {'service':'duckdb','operation':'campaigns.aggregate',
                        'params':copy.deepcopy(CASES['duckdb']),'key':'analysis-1'}

    def tearDown(self):
        self.engine.close();self.version.stop()

    def test_plan_is_local_and_does_not_spawn_or_make_network_calls(self):
        with patch('verdugo.local_runtime.subprocess.Popen') as proc, patch.object(self.engine,'transport') as transport:
            result=self.engine.plan(self.command)
            self.assertEqual('local-library',result['request']['transport'])
            self.assertFalse(result['requires_approval'])
            self.assertFalse(proc.called);self.assertFalse(transport.called)

    def test_runtime_result_persists_and_replay_does_not_execute_again(self):
        with patch('verdugo.local_runtime.execute',return_value={'ok':True,'result':{'rows':3}}) as run:
            first=self.engine.execute(self.command,True)
            again=self.engine.execute(self.command,True)
            self.assertEqual('succeeded',first['state'])
            self.assertTrue(again['replayed']);self.assertEqual(1,run.call_count)
            self.assertEqual(first['result'],again['result'])

    def test_worker_failure_is_failed_not_a_fake_success(self):
        with patch('verdugo.local_runtime.execute',side_effect=VerdugoError('Local timeout')):
            result=self.engine.execute(self.command,True)
        self.assertEqual('failed',result['state'])
        self.assertFalse(result['result']['reconciliation_required'])

    def test_local_compute_still_respects_operator_roles(self):
        for role in ('viewer','approver'):
            self.engine.role=role
            with self.subTest(role=role),self.assertRaises(VerdugoError): self.engine.execute(self.command,True)

    def test_input_code_version_and_timeout_change_invalidate_plan(self):
        self.engine.plan(self.command)
        with patch('verdugo.local_runtime.implementation_digest',return_value='changed'):
            with self.assertRaises(VerdugoError): self.engine.plan(self.command)
        self.config['tenants']['nexus']['services']['duckdb']['timeout_seconds']=60
        with self.assertRaises(VerdugoError): self.engine.plan(self.command)

    def test_disabled_and_unreviewed_integrations_fail_closed(self):
        cfg=self.config['tenants']['nexus']['services']['duckdb']
        for field in ('enabled','license_reviewed','runtime_reviewed'):
            cfg[field]=False
            with self.subTest(field=field),self.assertRaises(VerdugoError): self.engine.plan(self.command)
            cfg[field]=True

    def test_mcp_reuses_exact_engine_route_without_new_execution_backdoor(self):
        with patch('verdugo.local_runtime.execute',return_value={'ok':True}) as run:
            preview=invoke(self.engine,'verdugo_execute',{'command':self.command})
            self.assertEqual('planned',preview['state']);self.assertFalse(run.called)
            completed=invoke(self.engine,'verdugo_execute',{'command':self.command,'execute':True})
            self.assertEqual('succeeded',completed['state']);self.assertEqual(1,run.call_count)

    def test_workflow_can_use_local_operations_with_same_idempotence(self):
        spec={'id':'analysis-flow','steps':[{'id':'aggregate','service':'duckdb',
              'operation':'campaigns.aggregate','params':copy.deepcopy(CASES['duckdb'])}]}
        with patch('verdugo.local_runtime.execute',return_value={'ok':True}) as run:
            result=workflow.run(self.engine,spec,True)
            self.assertEqual('succeeded',result['state'])
            workflow.run(self.engine,spec,True)
            self.assertEqual(1,run.call_count)

    def test_environment_does_not_inherit_provider_secrets(self):
        from unittest.mock import MagicMock
        process=MagicMock();process.pid=123456789;process.returncode=2
        with patch.dict(os.environ,{'VERDUGO_SECRET_TEST':'private-example-value'}), \
             patch('verdugo.local_runtime.subprocess.Popen',return_value=process) as popen, \
             patch('verdugo.local_runtime.os.killpg'):
            request=local_runtime.build('duckdb','campaigns.aggregate',self.command['params'],
                self.config['tenants']['nexus']['services']['duckdb'])
            with self.assertRaises(VerdugoError): local_runtime.execute(request,
                self.config['tenants']['nexus']['services']['duckdb'])
            kwargs=popen.call_args.kwargs
            self.assertNotIn('VERDUGO_SECRET_TEST',kwargs['env'])
            self.assertFalse(kwargs.get('shell',False))
            self.assertTrue(kwargs['start_new_session'])

    def test_timeout_kills_process_group_and_does_not_mark_success(self):
        from unittest.mock import MagicMock
        process=MagicMock();process.pid=123456789
        process.communicate.side_effect=[subprocess.TimeoutExpired('worker',45),(None,None)]
        with patch('verdugo.local_runtime.subprocess.Popen',return_value=process), \
             patch('verdugo.local_runtime.os.killpg') as kill:
            result=self.engine.execute(self.command,True)
            self.assertEqual('failed',result['state'])
            self.assertTrue(kill.called)


if __name__ == '__main__': unittest.main()
