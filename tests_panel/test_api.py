from datetime import date
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from verdugo.engine import Engine
from verdugo import subscriptions
from verdugo.panel_server import create_app,local_token
from verdugo.common import VerdugoError

TOKEN='synthetic-panel-credential-for-tests-only'

class PanelAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.cfg=self.root/'config.json';self.state=self.root/'state.sqlite'
        self.cfg.write_text(json.dumps({'tenants':{'cliente-demo':{'services':{}},'nexus':{'services':{}}}}))
        self.headers={'X-Verdugo-Token':TOKEN,'Origin':'http://127.0.0.1:8766'}
        self.client=TestClient(create_app(self.cfg,str(self.state),TOKEN),base_url='http://127.0.0.1:8766');self.addCleanup(self.client.close)
        self.headers['X-Verdugo-CSRF']=self.client.get('/api/session',headers=self.headers).json()['csrf']
    def post(self,action,body):return self.client.post('/api/clients/cliente-demo/'+action,json=body,headers=self.headers)
    def test_auth_and_no_cors(self):
        self.assertEqual(self.client.get('/api/clients').status_code,401)
        result=self.client.get('/api/clients',headers=self.headers)
        self.assertEqual(result.status_code,200);self.assertNotIn('access-control-allow-origin',result.headers)
        self.assertEqual(result.headers['cache-control'],'no-store')
        self.assertIn("frame-ancestors 'none'",result.headers['content-security-policy'])
    def test_origin_host_and_csrf(self):
        for headers in (self.headers|{'Origin':'https://evil.invalid'},self.headers|{'Host':'evil.invalid'},self.headers|{'X-Verdugo-CSRF':'bad'}):
            self.assertEqual(self.client.post('/api/clients/cliente-demo/register',json={'confirm':True,'label':'Cliente demo'},headers=headers).status_code,403)
        h={k:v for k,v in self.headers.items() if k!='Origin'}
        self.assertEqual(self.client.post('/api/clients/cliente-demo/register',json={'confirm':True},headers=h).status_code,403)
    def test_registration_payment_expiration_same_engine(self):
        with patch('verdugo.subscriptions.today',return_value=date(2026,11,16)):
            response=self.post('register',{'confirm':True,'label':'Cliente demo'})
            self.assertEqual(response.status_code,200);self.assertFalse(response.json()['subscription']['active'])
            self.assertEqual(self.client.get('/api/ads?tenant=cliente-demo',headers=self.headers).status_code,400)
            paid=self.post('pay',{'confirm':True,'until':'2026-11-20'})
            self.assertTrue(paid.json()['subscription']['active'])
            e=Engine(str(self.state),json.loads(self.cfg.read_text()),'cliente-demo')
            try:self.assertTrue(subscriptions.state(e)['active']);self.assertEqual(len(e.events()),2)
            finally:e.close()
        with patch('verdugo.subscriptions.today',return_value=date(2026,11,21)):
            clients=self.client.get('/api/clients',headers=self.headers).json()['clients']
            self.assertFalse(next(c for c in clients if c['tenant']=='cliente-demo')['active'])
    def test_confirm_role_unknown_fields_and_tenant(self):
        self.assertEqual(self.post('register',{'confirm':False,'label':'Cliente demo'}).status_code,400)
        self.assertEqual(self.post('register',{'confirm':True,'label':'Cliente demo','role':'operator'}).status_code,400)
        self.assertEqual(self.client.post('/api/clients/unknown/register',json={'confirm':True,'label':'Cliente demo'},headers=self.headers).status_code,400)
        viewer=TestClient(create_app(self.cfg,str(self.state),TOKEN,role='viewer'),base_url='http://127.0.0.1:8766');self.addCleanup(viewer.close)
        self.assertEqual(viewer.get('/api/session',headers=self.headers).json()['role'],'viewer')
        self.assertEqual(viewer.post('/api/clients/cliente-demo/register',json={'confirm':True,'label':'Cliente demo'},headers=self.headers).status_code,403)
    def test_pause_resume_and_audit_projection(self):
        self.post('register',{'confirm':True,'label':'Cliente demo'})
        self.post('pause',{'confirm':True,'reason':'synthetic private detail'})
        events=self.client.get('/api/events?tenant=cliente-demo',headers=self.headers)
        self.assertNotIn('synthetic private detail',events.text);self.assertEqual(len(events.json()['events']),2)
        self.assertEqual(self.post('resume',{'confirm':True}).status_code,200)
        self.assertEqual(self.client.get('/api/events?tenant=nexus',headers=self.headers).json()['events'],[])
    def test_no_generic_commands_or_secret_query_auth(self):
        self.assertEqual(self.client.get('/api/clients?token='+TOKEN).status_code,401)
        self.assertEqual(self.client.post('/api/run',headers=self.headers,json={}).status_code,404)
        self.assertEqual(self.post('register',{'confirm':True,'label':'x'*40000}).status_code,413)
    def test_token_permissions_and_symlinks(self):
        path=self.root/'panel.token';token=local_token(path)
        self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(token,local_token(path))
        path.chmod(0o644)
        with self.assertRaises(VerdugoError):local_token(path)
        path.unlink();path.symlink_to(self.cfg)
        with self.assertRaises((OSError,VerdugoError)):local_token(path)
    def test_read_views_and_safe_static_csp(self):
        for route in ('/api/funnel?tenant=nexus','/api/product?tenant=nexus','/api/ads?tenant=nexus'):
            self.assertEqual(self.client.get(route,headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/ads?tenant=nexus&budget_month=nope',headers=self.headers).status_code,400)
        self.assertEqual(self.client.get('/api/ads?tenant=nexus&url=https://evil.invalid',headers=self.headers).status_code,400)
        self.assertEqual(self.client.get('/api/events?tenant=unknown',headers=self.headers).status_code,400)
        response=self.client.get('/')
        if response.status_code==200:self.assertIn('sha256-',response.headers['content-security-policy'])
