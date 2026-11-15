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

from planning_fixtures import CASES as PLANNING, assert_result as assert_planning

from completion_fixtures import CASES as COMPLETION, assert_result as assert_completion

from r_fixtures import CASES as R_CASES, assert_result as assert_r

from database_fixtures import CASES as DATABASE_CASES, assert_result as assert_database
from native_tools_fixtures import CASES as TOOLS_CASES, assert_result as assert_tools

from media_fixtures import CASES as MEDIA_CASES, assert_result as assert_media
from source_fixtures import CASES as SOURCE_CASES, assert_result as assert_source

CASES={**MEDIA_CASES,**SOURCE_CASES,**TOOLS_CASES,**DATABASE_CASES,**R_CASES,**CLI,**CONTENT,**NATIVE,**PLANNING,**COMPLETION}

class FinalProduct(unittest.TestCase):
    def test_original_operations_compose_and_restart(self):
        selected=set(filter(None,os.getenv('VERDUGO_RUNTIME_SERVICES','').split(','))) or set(CASES)
        selected &= set(CASES)
        if not selected:self.skipTest('Other runtime group selected')
        if any(not local_runtime.installed(s)['version_matches'] for s in selected):
            if os.getenv('VERDUGO_RUNTIME_REQUIRED')=='1':self.fail('Missing required profile')
            self.skipTest('Profiles not installed')
        config=template('nexus')
        reads, http_calls, replies = [], [], {}
        if os.getenv('VERDUGO_COMPLETION_HTTP_FIXTURES') == '1':
            import sys
            sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
            from test_completion_reads_v021 import configure as http_config, REPLIES as HTTP_REPLIES, TOKEN, DEVELOPER
            from test_public_reads_v021 import configure as public_config, REPLIES as PUBLIC_REPLIES
            http_config(config);public_config(config);replies=HTTP_REPLIES|PUBLIC_REPLIES;reads=sorted(replies)
            credentials=patch.dict(os.environ, VERDUGO_COMPLETION_TOKEN=TOKEN, VERDUGO_COMPLETION_DEVELOPER=DEVELOPER)
            credentials.start();self.addCleanup(credentials.stop)
        def transport(request, cfg):
            sid=request['public']['service'];http_calls.append(sid)
            return copy.deepcopy(replies[sid])
        for sid in selected:config['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=120)
        tasks=[{'id':s,'service':s,'params':copy.deepcopy(CASES[s])} for s in sorted(selected)]
        for task in tasks:
            sid=task['id']
            if sid=='dbt' and 'vanna' in selected:
                task['params']['rows']={'$ref':'analysis-vanna.result.rows'};task['depends_on']=['analysis-vanna']
            if sid=='grype' and 'syft' in selected:
                task['params']['packages']={'$ref':'analysis-syft.result.packages'};task['depends_on']=['analysis-syft']
            if sid=='geo-lint' and 'site-md' in selected:
                task['params']['text']={'$ref':'analysis-site-md.result.markdown'};task['depends_on']=['analysis-site-md']
            if sid=='structured-data-validator' and 'seo-graph' in selected:
                task['params']['graph']={'$ref':'analysis-seo-graph.result.graph'};task['depends_on']=['analysis-seo-graph']
        request={'id':'final-product-demo','services':reads,'dataset':'demo','currency':'MXN','analyses':tasks}
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)/'state.db'
            with closing(Engine(state,config,transport=transport)) as e:
                first=product.observe(e,request,True)
                self.assertEqual('succeeded',first['state'],json.dumps(first))
                for row in first['analyses']:
                    sid=row['service'];r=row['analysis']['result']
                    if sid in MEDIA_CASES: assert_media(self,sid,r)
                    elif sid in SOURCE_CASES: assert_source(self,sid,r)
                    elif sid in TOOLS_CASES: assert_tools(self, sid, r)
                    elif sid in DATABASE_CASES:assert_database(self,sid,r)
                    elif sid in R_CASES:assert_r(self,sid,r)
                    elif sid in COMPLETION:assert_completion(self,sid,r)
                    elif sid in PLANNING:assert_planning(self,sid,r)
                    elif sid in CLI:assert_cli(self,sid,r)
                    elif sid in CONTENT:assert_content(self,sid,r)
                    elif sid=='structured-data-validator' and 'seo-graph' in selected:self.assertEqual(0,r['issues'])
                    elif sid!='geo-lint':assert_native(self,sid,r)
                    else:self.assertGreater(r['issues'],0)
                self.assertEqual(len(selected)+len(reads)+1,e.db.execute("SELECT count(*) FROM runs WHERE state='succeeded'").fetchone()[0])
                self.assertEqual(set(reads),set(http_calls));self.assertEqual(len(reads),len(http_calls))
                stored='\n'.join(e.db.iterdump())
                for sid in selected:
                    secret=CASES[sid].get('secret_text')
                    if secret:
                        self.assertNotIn(secret,stored);self.assertNotIn(secret,json.dumps(first))
            with closing(Engine(state,config,transport=lambda *a:self.fail('Replay called provider'))) as e,patch('verdugo.local_runtime.execute',side_effect=AssertionError('Replay executed worker')):
                replay=product.observe(e,request,True)
                self.assertEqual('succeeded',replay['state']);self.assertEqual(len(selected),replay['reused_analyses'])
                self.assertEqual(len(reads),replay['reused_observations'])
                for a,b in zip(first['analyses'],replay['analyses']):self.assertEqual(a['analysis'],b['analysis'])
        target=os.getenv('VERDUGO_PRODUCT_EVIDENCE')
        if target:Path(target).write_text(json.dumps({'services':sorted(selected),'synthetic_http_services':reads,'steps':len(selected)+len(reads)+1,'execution':'passed','sqlite_restart':'passed','replay_worker_calls':0,'replay_http_calls':0,'private_input_persisted':False,'production_certified':False},indent=2)+'\n')
