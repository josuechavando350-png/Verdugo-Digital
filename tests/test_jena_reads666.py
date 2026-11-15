"""Original Fuseki status schema, explicit Basic protection and count-only replay."""
import base64
from contextlib import closing
import json
import os
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

TOKEN='synthetic-user:synthetic-private-password'
AUTH='Basic '+base64.b64encode(TOKEN.encode()).decode()
REPLY={'version':'6.3.0-SNAPSHOT','startDateTime':'2026-11-15T00:00:00Z','uptime':12,
       'datasets':[{'ds.name':PRIVATE,'ds.state':True,'ds.services':[
           {'srv.type':'query','srv.description':TOKEN,'srv.endpoints':['query',None,'']}]},
           {'ds.name':'/synthetic-offline','ds.state':False,'ds.services':[]}]}
SPECS={'jena':batch.SPECS['jena']}
GATES=('native_auth_enforced_reviewed','dedicated_instance_reviewed','status_route_basic_auth_reviewed')


def configured():
    cfg=template('nexus')
    cfg['tenants']['nexus']['services']['jena'].update(enabled=True,license_reviewed=True,
        version='synthetic-666',**{x:True for x in GATES})
    return cfg


class JenaReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg=configured();self.service=self.cfg['tenants']['nexus']['services']['jena']
        env=patch.dict(os.environ,{self.service['token_env']:TOKEN});env.start();self.addCleanup(env.stop)

    def test_original_route_basic_header_and_disabled_defaults(self):
        r=build('jena','datasets.summary',{},self.service)
        self.assertEqual('https://example.invalid/$/server',r['public']['url'])
        self.assertEqual('GET',r['public']['method']);self.assertIsNone(r['public']['body'])
        self.assertEqual(AUTH,r['headers']['Authorization']);self.assertFalse(r['mutates'])
        self.assertNotIn(TOKEN,json.dumps(r['public']));self.assertNotIn(AUTH,json.dumps(r['public']))
        self.assertEqual('datasets.summary',product.read_operations()['jena'])
        default=template('nexus')['tenants']['nexus']['services']['jena']
        for flag in ('enabled','license_reviewed',*GATES):self.assertIs(default[flag],False)

    def test_anonymous_route_unreviewed_instance_or_arbitrary_input_rejected(self):
        for flag in GATES:
            for value in (False,None,1,'true'):
                with self.assertRaises(VerdugoError):build('jena','datasets.summary',{},self.service|{flag:value})
        for change in ({'api_surface':'public'},{'auth_mode':'none'},{'auth_mode':'native_api_key_bearer'}):
            with self.assertRaises(VerdugoError):build('jena','datasets.summary',{},self.service|change)
        for params in ({'query':'SELECT * {}'},{'dataset':PRIVATE},{'url':'https://other.invalid'},
                       {'token':TOKEN},{'method':'POST'},{'tenant':'other'},{'contextPath':'/other'}):
            with self.assertRaises(VerdugoError):build('jena','datasets.summary',params,self.service)
        with self.assertRaises(VerdugoError):build('jena','datasets.delete',{},self.service)
        for token in ('no-colon',':password','user:'):
            with patch.dict(os.environ,{self.service['token_env']:token}),self.assertRaises(VerdugoError):
                build('jena','datasets.summary',{},self.service)

    def test_projection_keeps_counts_and_no_dataset_contents(self):
        r=check('jena','datasets.summary',REPLY)
        self.assertEqual((2,1,1,1,3),tuple(r[k] for k in ('datasets_in_response','datasets_accepting_requests',
            'datasets_not_accepting_requests','services_described','endpoints_described')))
        self.assertFalse(r['dataset_contents_inspected']);self.assertFalse(r['live_verified'])
        self.assertEqual(0,r['sparql_queries_executed']);self.assertEqual(0,r['datasets_modified'])
        for value in (PRIVATE,TOKEN,'SNAPSHOT','2026-11-15'):self.assertNotIn(value,json.dumps(r))
        self.assertEqual(0,check('jena','datasets.summary',REPLY|{'datasets':[]})['datasets_in_response'])

    def test_malformed_types_duplicates_and_limits_fail_closed(self):
        bad=[{},[],REPLY|{'uptime':True},REPLY|{'uptime':-1},REPLY|{'uptime':10**12+1},
             REPLY|{'version':None},REPLY|{'datasets':{}},REPLY|{'datasets':[REPLY['datasets'][0]]*2},
             REPLY|{'datasets':[{}]},REPLY|{'datasets':[REPLY['datasets'][0]]*1001}]
        row=REPLY['datasets'][0];item=row['ds.services'][0]
        bad += [REPLY|{'datasets':[row|change]} for change in ({'ds.name':''},{'ds.state':1},{'ds.services':{}},
            {'ds.services':[item]*129},{'ds.services':[item|{'srv.endpoints':[1]}]},
            {'ds.services':[item|{'srv.type':[]}]},{'ds.services':[item|{'srv.endpoints':['x']*129}]} )]
        for response in bad:
            with self.subTest(response=str(response)[:120]),self.assertRaises(VerdugoError):check('jena','datasets.summary',response)

    def test_socket_workflow_mcp_cli_restart_and_private_payloads(self):
        spec={'id':'jena-counts','steps':[{'id':'inventory','service':'jena','operation':'datasets.summary','params':{}}]}
        with tempfile.TemporaryDirectory() as tmp,wire(self.cfg,{'jena':REPLY},SPECS,{'jena':('Authorization',AUTH)}) as server:
            state=str(Path(tmp)/'state.sqlite3')
            with closing(Engine(state,self.cfg)) as e:
                self.assertEqual([],invoke(e,'verdugo_workflow',{'workflow':spec})['approval_batch'])
                result=invoke(e,'verdugo_workflow',{'workflow':spec,'execute':True})
                self.assertEqual('succeeded',result['state'],result)
                dump='\n'.join(e.db.iterdump())
                for secret in (PRIVATE,TOKEN,AUTH):self.assertNotIn(secret,dump)
            with closing(Engine(state,self.cfg,transport=lambda *_:self.fail('network replay'))) as e:
                self.assertEqual(result['steps'],workflow.run(e,spec,True)['steps'])
            config=Path(tmp)/'config.json';config.write_text(json.dumps(self.cfg));config.chmod(0o600)
            request=Path(tmp)/'request.json';request.write_text(json.dumps(spec))
            cli=subprocess.run([sys.executable,'-m','verdugo','--config',str(config),'--state',state,
                'workflow','@'+str(request),'--execute'],capture_output=True,text=True)
            self.assertEqual(0,cli.returncode,cli.stderr);self.assertEqual(1,len(server['calls']))

    def test_status_size_and_credential_or_review_changes_block_replay(self):
        with wire(self.cfg,{'jena':REPLY},SPECS,{'jena':('Authorization',AUTH)}) as server,closing(Engine(':memory:',self.cfg)) as e:
            def command(key):return {'service':'jena','operation':'datasets.summary','params':{},'key':key}
            for status in (202,204,302,401,403,500):
                server['status']=status;self.assertEqual('failed',e.execute(command(str(status)),True)['state'])
            server['status']=200;server['raw']=b'x'*(1024*1024+1)
            self.assertEqual('failed',e.execute(command('size'),True)['state'])
            server['raw']=None;self.assertEqual('succeeded',e.execute(command('reuse'),True)['state'])
            with patch.dict(os.environ,{self.service['token_env']:'changed-user:changed-password'}),self.assertRaises(VerdugoError):
                e.execute(command('reuse'),True)
            self.service['status_route_basic_auth_reviewed']=False
            with self.assertRaises(VerdugoError):e.execute(command('reuse'),True)

    def test_original_evidence_and_server_not_executed(self):
        r=next(x for x in json.loads(batch.CONTRACT.read_text())['records'] if x['id']=='jena')
        self.assertEqual(batch.PINNED_COMMITS['jena'],r['commit']);self.assertTrue(r['license_text_read'])
        self.assertFalse(r['original_server_executed']);self.assertFalse(r['live_verified'])
        self.assertEqual(12,len(r['files']))
        for f in r['files']:self.assertRegex(f['git_blob_sha'],'^[a-f0-9]{40}$');self.assertRegex(f['sha256'],'^[a-f0-9]{64}$')
