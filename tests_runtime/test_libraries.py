"""Acceptance against installed libraries. REQUIRED=1 prohibits skipped providers."""
import json
import os
from pathlib import Path
import sys
import unittest

from verdugo import local_runtime
from verdugo.__main__ import template
from verdugo.engine import Engine
from fixtures import CASES

REQUIRED = os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1'
SELECTED = os.getenv('VERDUGO_RUNTIME_SERVICES', '').split(',')
SELECTED = [x for x in SELECTED if x] or list(local_runtime.SPECS)
EVIDENCE = []


class RuntimeAcceptance(unittest.TestCase):
    def test_actual_operations_through_engine(self):
        for sid in SELECTED:
            if not local_runtime.installed(sid)['version_matches']:
                if REQUIRED:
                    self.fail('Required exact package versions are missing for '+sid)
                continue
            config=template('nexus')
            cfg=config['tenants']['nexus']['services'][sid]
            cfg.update(enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=90)
            if sid=='playwright':
                cfg['browser_path']=os.environ.get('PLAYWRIGHT_BROWSERS_PATH',str(Path.home()/'.cache/ms-playwright'))
                if not Path(cfg['browser_path']).is_dir() and not REQUIRED:
                    continue
            engine=Engine(':memory:',config)
            command={'service':sid,'operation':local_runtime.SPECS[sid][0],
                     'params':CASES[sid],'key':'acceptance-'+sid}
            try:
                with self.subTest(service=sid):
                    result=engine.execute(command,True)
                    self.assertEqual('succeeded',result['state'],json.dumps(result))
                    data=result['result']
                    self.assertTrue(data['ok']);self.assertEqual('demo',data['dataset'])
                    self.assertFalse(data['external_provider_calls_made'])
                    self.assertFalse(data['production_certified'])
                    self.assertIsNone(data['commercial_success_probability'])
                    self.assertEqual(local_runtime.SPECS[sid][2],data['version'])
                    value=data['result']
                    if sid=='trafilatura':
                        self.assertIn('appointment',value['text'].lower())
                        self.assertFalse(value['fetched_remote_content'])
                    elif sid=='scrapy':
                        self.assertEqual('Synthetic Nexus article',value['title'])
                        self.assertIn('Appointment automation',value['h1'])
                        self.assertEqual(0,value['links_followed'])
                    elif sid=='duckdb':
                        organic=value['channels'][0]
                        self.assertEqual(300,organic['spend_minor'])
                        self.assertEqual(1200,organic['revenue_minor'])
                        self.assertEqual(10,organic['leads'])
                        self.assertEqual(3,organic['conversions'])
                        self.assertFalse(value['bank_reconciled'])
                    elif sid=='or-tools':
                        self.assertEqual({'alpha','beta'},set(value['selected_ids']))
                        self.assertEqual(10,value['total_cost_minor'])
                        self.assertEqual(13,value['objective_value'])
                        self.assertTrue(value['optimal_for_declared_inputs'])
                        self.assertFalse(value['spend_executed'])
                    elif sid=='optuna':
                        self.assertGreaterEqual(value['selection_f1'],value['baseline_f1_at_half'])
                        self.assertFalse(value['independent_validation'])
                        self.assertGreater(value['completed_trials'],0)
                    elif sid in ('scikit-learn','catboost'):
                        self.assertEqual(2,len(value['model_scores']))
                        self.assertLess(value['model_scores'][0],value['model_scores'][1])
                        self.assertEqual(10,value['holdout']['holdout_rows'])
                        self.assertFalse(value['calibrated_for_deployment'])
                    elif sid=='haystack':
                        self.assertEqual('appointments',value['matches'][0]['id'])
                        self.assertFalse(value['llm_called'])
                    elif sid=='great-expectations':
                        self.assertFalse(value['data_valid'])
                        self.assertEqual(4,value['checks_executed'])
                    elif sid=='evidently':
                        self.assertEqual(40,value['current_rows'])
                        self.assertTrue(value['report'])
                    elif sid=='presidio':
                        self.assertNotIn('maria@example.com',value['text'])
                        self.assertNotIn('4111 1111 1111 1111',value['text'])
                        self.assertGreater(value['redactions_by_type'].get('EMAIL_ADDRESS',0),0)
                        self.assertFalse(value['exhaustive_privacy_guarantee'])
                    elif sid=='playwright':
                        self.assertEqual(2,len(value['views']))
                        self.assertEqual(1,value['views'][0]['observations']['h1_count'])
                        self.assertTrue(value['views'][0]['observations']['horizontal_overflow'])
                        self.assertFalse(value['views'][1]['observations']['horizontal_overflow'])
                        self.assertFalse(value['javascript_enabled'])
                    replay=engine.execute(command,True)
                    self.assertTrue(replay['replayed'])
                    self.assertEqual(result['result'],replay['result'])
                    EVIDENCE.append({'service':sid,'operation':command['operation'],
                        'distribution':data['distribution'],'version':data['version'],
                        'implementation_sha256':data['implementation_sha256'],
                        'engine_execution':'passed','result_assertions':'passed','idempotent_replay':'passed',
                        'dataset':'demo','production_certified':False})
            finally:
                engine.close()
        if REQUIRED:
            self.assertEqual(len(SELECTED),len(EVIDENCE),'Not every required recipe completed')
        else:
            self.assertTrue(EVIDENCE,'No real runtime library was tested')

    @classmethod
    def tearDownClass(cls):
        target=os.environ.get('VERDUGO_RUNTIME_EVIDENCE')
        if target:
            Path(target).write_text(json.dumps({'schema':'verdugo.runtime-acceptance.v1',
                'required_services':SELECTED,'checks':EVIDENCE,
                'certifies_production':False},indent=2)+'\n')


if __name__=='__main__': unittest.main()
