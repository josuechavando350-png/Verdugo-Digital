"""Composition and restart across all v0.21 runtimes, with real original packages."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_runtime, product
from verdugo.__main__ import template
from verdugo.engine import Engine
from cli_fixtures import CASES as CLI, assert_result as assert_cli
from content_fixtures import CASES as CONTENT, assert_result as assert_content
from native_fixtures import CASES as NATIVE, assert_result as assert_native

CASES={**CLI,**CONTENT,**NATIVE}

class FinalProduct(unittest.TestCase):
    def test_original_operations_compose_and_restart(self):
        selected=set(filter(None,os.getenv('VERDUGO_RUNTIME_SERVICES','').split(','))) or set(CASES)
        selected &= set(CASES)
        if not selected:self.skipTest('Other runtime group selected')
        if any(not local_runtime.installed(s)['version_matches'] for s in selected):
            if os.getenv('VERDUGO_RUNTIME_REQUIRED')=='1':self.fail('Missing required profile')
            self.skipTest('Profiles not installed')
        config=template('nexus')
        for sid in selected:config['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=120)
        tasks=[{'id':s,'service':s,'params':copy.deepcopy(CASES[s])} for s in sorted(selected)]
        for task in tasks:
            sid=task['id']
            if sid=='grype' and 'syft' in selected:
                task['params']['packages']={'$ref':'analysis-syft.result.packages'};task['depends_on']=['analysis-syft']
            if sid=='geo-lint' and 'site-md' in selected:
                task['params']['text']={'$ref':'analysis-site-md.result.markdown'};task['depends_on']=['analysis-site-md']
            if sid=='structured-data-validator' and 'seo-graph' in selected:
                task['params']['graph']={'$ref':'analysis-seo-graph.result.graph'};task['depends_on']=['analysis-seo-graph']
        request={'id':'final-product-demo','services':[],'dataset':'demo','currency':'MXN','analyses':tasks}
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)/'state.db'
            with closing(Engine(state,config)) as e:
                first=product.observe(e,request,True)
                self.assertEqual('succeeded',first['state'],json.dumps(first))
                for row in first['analyses']:
                    sid=row['service'];r=row['analysis']['result']
                    if sid in CLI:assert_cli(self,sid,r)
                    elif sid in CONTENT:assert_content(self,sid,r)
                    elif sid=='structured-data-validator' and 'seo-graph' in selected:self.assertEqual(0,r['issues'])
                    elif sid!='geo-lint':assert_native(self,sid,r)
                    else:self.assertGreater(r['issues'],0)
                self.assertEqual(len(selected)+1,e.db.execute("SELECT count(*) FROM runs WHERE state='succeeded'").fetchone()[0])
                stored='\n'.join(e.db.iterdump())
                for sid in selected:
                    secret=CASES[sid].get('secret_text')
                    if secret:
                        self.assertNotIn(secret,stored);self.assertNotIn(secret,json.dumps(first))
            with closing(Engine(state,config)) as e,patch('verdugo.local_runtime.execute',side_effect=AssertionError('Replay executed worker')):
                replay=product.observe(e,request,True)
                self.assertEqual('succeeded',replay['state']);self.assertEqual(len(selected),replay['reused_analyses'])
                for a,b in zip(first['analyses'],replay['analyses']):self.assertEqual(a['analysis'],b['analysis'])
        target=os.getenv('VERDUGO_PRODUCT_EVIDENCE')
        if target:Path(target).write_text(json.dumps({'services':sorted(selected),'steps':len(selected)+1,'execution':'passed','sqlite_restart':'passed','replay_worker_calls':0,'private_input_persisted':False,'production_certified':False},indent=2)+'\n')
