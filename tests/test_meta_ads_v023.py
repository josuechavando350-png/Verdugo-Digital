from contextlib import closing, contextmanager
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from verdugo.__main__ import template
from verdugo.engine import Engine
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo import meta_ads

TOKEN='synthetic-token+/=?never-real'
REPLY={'data':[{'spend':'123.25','clicks':'4','impressions':'100','date_start':'2026-11-01','date_stop':'2026-11-02','account_currency':'MXN','account_name':'private@example.invalid'}]}


def configure(config):
    config['tenants']['nexus']['services']['meta-ads'].update(enabled=True,license_reviewed=True,
        version='v26.0.4',account_id='act_123',account_scope_reviewed=True,
        report_start_date='2026-11-01',report_end_date='2026-11-02')


class MetaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.config=template('nexus'); configure(self.config); self.cfg=self.config['tenants']['nexus']['services']['meta-ads']
        env=patch.dict(os.environ,VERDUGO_NEXUS_META_ADS_TOKEN=TOKEN); env.start(); self.addCleanup(env.stop)
        self.e=Engine(Path(self.tmp.name)/'state.sqlite',self.config,transport=lambda r,c:copy.deepcopy(REPLY)); self.addCleanup(self.e.close)
        self.command={'service':'meta-ads','operation':'insights.summary','params':{},'key':'meta-test'}
    def test_private_token_not_in_plan_fingerprint_or_state(self):
        first=self.e.plan(self.command)
        with patch.dict(os.environ,VERDUGO_NEXUS_META_ADS_TOKEN='another-synthetic-token'):
            self.assertEqual(first['fingerprint'],self.e.plan(self.command)['fingerprint'])
        self.assertNotIn('access_token',json.dumps(first)); self.assertNotIn(TOKEN,json.dumps(first))
        self.assertEqual(self.e.execute(self.command,True)['result']['spend'],123.25)
        dump='\n'.join(self.e.db.iterdump())
        for secret in (TOKEN,'private@example.invalid','access_token'): self.assertNotIn(secret,dump)
    def test_fixed_query_no_param_overrides(self):
        req=build('meta-ads','insights.summary',{},self.cfg)
        self.assertNotIn('Authorization',req['headers'])
        query=parse_qs(urlsplit(meta_ads.wire_path(req)).query)
        self.assertEqual(query['access_token'],[TOKEN]); self.assertEqual(query['level'],['account']); self.assertEqual(query['fields'],[meta_ads.FIELDS]); self.assertEqual(query['limit'],['1'])
        for key in ('account_id','start_date','end_date','token','url','fields','page'):
            with self.assertRaises(VerdugoError): build('meta-ads','insights.summary',{key:'x'},self.cfg)
    def test_config_gates(self):
        for key,value in (('base_url','https://example.invalid'),('api_version','v99.0'),('account_scope_reviewed',False),('account_id','act_1/insights?x=1'),('report_end_date','2027-11-02')):
            with self.subTest(key=key),self.assertRaises(VerdugoError): build('meta-ads','insights.summary',{},self.cfg|{key:value})
    def test_schema_and_pagination_fail_closed(self):
        req=build('meta-ads','insights.summary',{},self.cfg)['public']
        for reply in ({'error':{'message':TOKEN}},{'data':[{},{}]},{'data':[REPLY['data'][0]|{'clicks':'nan'}]},{'data':[REPLY['data'][0]|{'date_stop':'2026-11-03'}]},REPLY|{'paging':{'next':'https://example.invalid?access_token='+TOKEN}}):
            with self.assertRaises(VerdugoError): meta_ads.check('meta-ads','insights.summary',reply,req)
    def test_loopback_wire_replay_and_redacted_http_errors(self):
        calls=[]; status=[200]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_GET(self):
                calls.append(self.path); self.send_response(status[0]); self.end_headers(); self.wfile.write(json.dumps(REPLY).encode())
        server=HTTPServer(('127.0.0.1',0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            self.cfg.update(base_url='http://127.0.0.1:'+str(server.server_port),allow_local_http=True)
            with closing(Engine(self.e.state_path,self.config)) as engine:
                self.assertEqual(engine.execute(self.command,True)['state'],'succeeded')
                self.assertTrue(engine.execute(self.command,True)['replayed']); self.assertEqual(len(calls),1)
                self.assertEqual(parse_qs(urlsplit(calls[0]).query)['access_token'],[TOKEN])
                status[0]=400
                failed=engine.execute(self.command|{'key':'error'},True)
                self.assertEqual(failed['state'],'failed'); self.assertNotIn(TOKEN,json.dumps(failed))
                self.assertNotIn(TOKEN,'\n'.join(engine.db.iterdump()))
        finally: server.shutdown(); thread.join(); server.server_close()
