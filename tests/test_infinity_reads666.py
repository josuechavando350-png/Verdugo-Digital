"""Original Python Infinity inventory, not embedding/model execution."""
import json
import os
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from verdugo import knowledge_reads666 as batch, workflow, product
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from test_operations_reads_v019 import wire, PRIVATE

TOKEN = 'synthetic-infinity-credential'
REPLY = {'object':'list', 'data':[{'id':PRIVATE, 'object':'model', 'owned_by':'infinity',
                                 'stats':{'private':TOKEN}, 'capabilities':['embed']}]}
SPECS = {'infinity': batch.SPECS['infinity']}


def configured():
    cfg = template('nexus')
    cfg['tenants']['nexus']['services']['infinity'].update(enabled=True, license_reviewed=True,
        version='synthetic-666', native_auth_enforced_reviewed=True, dedicated_instance_reviewed=True)
    return cfg


class InfinityReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg=configured(); self.service=self.cfg['tenants']['nexus']['services']['infinity']
        env=patch.dict(os.environ,{self.service['token_env']:TOKEN});env.start();self.addCleanup(env.stop)

    def test_original_python_root_route_and_protected_defaults(self):
        r=build('infinity','models.summary',{},self.service)
        self.assertEqual('https://example.invalid/models',r['public']['url'])
        self.assertEqual('GET',r['public']['method']);self.assertIsNone(r['public']['body'])
        self.assertEqual('Bearer '+TOKEN,r['headers']['Authorization']);self.assertFalse(r['mutates'])
        self.assertNotIn(TOKEN,json.dumps(r['public']))
        self.assertEqual('models.summary',product.read_operations()['infinity'])
        default=template('nexus')['tenants']['nexus']['services']['infinity']
        for flag in ('enabled','license_reviewed','native_auth_enforced_reviewed','dedicated_instance_reviewed'):
            self.assertIs(default[flag],False)

    def test_no_unreviewed_auth_instance_or_alternate_server(self):
        for flag in ('native_auth_enforced_reviewed','dedicated_instance_reviewed'):
            for value in (False,None,1,'true'):
                with self.assertRaises(VerdugoError):build('infinity','models.summary',{},self.service|{flag:value})
        for changes in ({'api_surface':'cloud'},{'api_surface':'native_v3'},{'auth_mode':'none'}):
            with self.assertRaises(VerdugoError):build('infinity','models.summary',{},self.service|changes)
        for params in ({'model':PRIVATE},{'texts':[PRIVATE]},{'url':'https://other.invalid'},
                       {'url_prefix':'/v1'},{'method':'POST'},{'token':TOKEN},{'tenant':'other'}):
            with self.assertRaises(VerdugoError):build('infinity','models.summary',params,self.service)
        with self.assertRaises(VerdugoError):build('infinity','embeddings.create',{},self.service)

    def test_only_counts_persist_and_no_models_called(self):
        r=check('infinity','models.summary',REPLY)
        self.assertEqual(1,r['models_in_response']);self.assertEqual(0,r['models_called'])
        self.assertEqual(0,r['model_weights_downloaded']);self.assertFalse(r['live_verified'])
        self.assertFalse(r['model_quality_verified']);self.assertNotIn(PRIVATE,json.dumps(r))
        self.assertNotIn(TOKEN,json.dumps(r))
        self.assertEqual(0,check('infinity','models.summary',{'object':'list','data':[]})['models_in_response'])

    def test_invalid_response_and_cardinality(self):
        for r in ({},[],REPLY|{'object':'error'},REPLY|{'data':None},REPLY|{'data':[{}]},
                  REPLY|{'data':REPLY['data']*1001}):
            with self.assertRaises(VerdugoError):check('infinity','models.summary',r)
        for changes in ({'id':None},{'id':'a'*1025},{'object':'embedding'},{'owned_by':'other'},{'stats':[]}):
            with self.assertRaises(VerdugoError):
                check('infinity','models.summary',REPLY|{'data':[REPLY['data'][0]|changes]})

    def test_socket_mcp_cli_restart_and_privacy(self):
        spec={'id':'infinity-inventory','steps':[{'id':'inventory','service':'infinity','operation':'models.summary','params':{}}]}
        with tempfile.TemporaryDirectory() as tmp, wire(self.cfg,{'infinity':REPLY},SPECS,{'infinity':('Authorization','Bearer '+TOKEN)}) as server:
            state=str(Path(tmp)/'state.sqlite3')
            with closing(Engine(state,self.cfg)) as e:
                self.assertEqual([],invoke(e,'verdugo_workflow',{'workflow':spec})['approval_batch'])
                result=invoke(e,'verdugo_workflow',{'workflow':spec,'execute':True})
                self.assertEqual('succeeded',result['state'],result)
                dump='\n'.join(e.db.iterdump());self.assertNotIn(PRIVATE,dump);self.assertNotIn(TOKEN,dump)
            with closing(Engine(state,self.cfg,transport=lambda *_:self.fail('network replay'))) as e:
                self.assertEqual(result['steps'],workflow.run(e,spec,True)['steps'])
            config=Path(tmp)/'config.json';config.write_text(json.dumps(self.cfg));config.chmod(0o600)
            req=Path(tmp)/'request.json';req.write_text(json.dumps(spec))
            cli=subprocess.run([sys.executable,'-m','verdugo','--config',str(config),'--state',state,
                                'workflow','@'+str(req),'--execute'],capture_output=True,text=True)
            self.assertEqual(0,cli.returncode,cli.stderr);self.assertEqual(1,len(server['calls']))

    def test_http_status_bounds_and_changed_review_block_replay(self):
        with wire(self.cfg,{'infinity':REPLY},SPECS,{'infinity':('Authorization','Bearer '+TOKEN)}) as server, closing(Engine(':memory:',self.cfg)) as e:
            def command(key):return {'service':'infinity','operation':'models.summary','params':{},'key':key}
            for status in (202,204,302,401,500):
                server['status']=status;self.assertEqual('failed',e.execute(command(str(status)),True)['state'])
            server['status']=200;server['raw']=b'x'*(1024*1024+1)
            self.assertEqual('failed',e.execute(command('oversize'),True)['state'])
            server['raw']=None;self.assertEqual('succeeded',e.execute(command('replay'),True)['state'])
            self.service['native_auth_enforced_reviewed']=False
            with self.assertRaises(VerdugoError):e.execute(command('replay'),True)

    def test_original_evidence_and_no_server_execution(self):
        r=next(x for x in json.loads(batch.CONTRACT.read_text())['records'] if x['id']=='infinity')
        self.assertEqual(batch.PINNED_COMMITS['infinity'],r['commit']);self.assertTrue(r['license_text_read'])
        self.assertFalse(r['original_server_executed']);self.assertFalse(r['live_verified'])
        self.assertEqual(4,len(r['files']))
        for f in r['files']:self.assertRegex(f['git_blob_sha'],'^[a-f0-9]{40}$');self.assertRegex(f['sha256'],'^[a-f0-9]{64}$')
