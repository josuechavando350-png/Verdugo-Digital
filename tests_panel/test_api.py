from datetime import date
from contextlib import closing
import base64
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

    def test_create_tenant_starts_off_and_requires_confirmation_and_operator(self):
        payload={'tenant':'cliente-nuevo','confirm':True}
        self.assertEqual(self.client.post('/api/tenants',json=payload|{'confirm':False},headers=self.headers).status_code,400)
        self.assertEqual(self.client.post('/api/tenants',json=payload,headers=self.headers).status_code,200)
        self.assertIn('cliente-nuevo',self.client.get('/api/session',headers=self.headers).json()['tenants'])
        clients=self.client.get('/api/clients',headers=self.headers).json()['clients']
        self.assertFalse(next(c for c in clients if c['tenant']=='cliente-nuevo')['active'])
        self.assertEqual(self.client.get('/api/ads?tenant=cliente-nuevo',headers=self.headers).status_code,400)
        self.assertEqual(self.client.post('/api/tenants',json=payload,headers=self.headers).status_code,400)

    def upload(self, **changes):
        csv=b'Day,Campaign,Cost,Clicks,Impressions,Conversions\n2026-11-01,private-demo-campaign,30,4,40,2\n'
        body={'tenant':'nexus','platform':'google','dataset':'demo','currency':'MXN',
              'csv_base64':base64.b64encode(csv).decode(),'confirm':False}
        return self.client.post('/api/ads/import',json=body|changes,headers=self.headers)

    def test_upload_preview_confirmation_and_replay_use_same_engine(self):
        preview=self.upload(); self.assertEqual(preview.status_code,200)
        self.assertNotIn('private-demo-campaign',preview.text)
        report='/api/ads?tenant=nexus&dataset=demo&start_date=2026-11-01&end_date=2026-11-01'
        self.assertEqual(self.client.get(report,headers=self.headers).json()['totals']['spend'],0)
        self.assertEqual(self.upload(confirm=True).status_code,400)
        self.assertEqual(self.upload(confirm=True,preview_fingerprint='0'*64).status_code,400)
        fingerprint=preview.json()['preview_fingerprint']
        saved=self.upload(confirm=True,preview_fingerprint=fingerprint)
        self.assertEqual(saved.status_code,200); self.assertEqual(saved.json()['changed'],1)
        self.assertTrue(self.upload(confirm=True,preview_fingerprint=fingerprint).json()['replayed'])
        self.assertEqual(self.client.get(report,headers=self.headers).json()['totals']['spend'],30)
        self.assertEqual(self.client.get(report.replace('tenant=nexus','tenant=cliente-demo'),headers=self.headers).json()['totals']['spend'],0)

    def test_upload_invalid_content_and_suspended_client(self):
        for changes in ({'csv_base64':'bad!!!'},{'csv_base64':42},{'confirm':'true'},
                        {'currency':'usd'},{'filename':'private.csv'},{'csv_base64':base64.b64encode(b'x'*(5*1024*1024+1)).decode()}):
            self.assertEqual(self.upload(**changes).status_code,400)
        self.post('register',{'confirm':True,'label':'Cliente demo'})
        self.assertEqual(self.upload(tenant='cliente-demo').status_code,400)

    def test_sales_intake_followups_win_and_atomic_rejection(self):
        def save(action,request):
            return self.client.post('/api/sales/'+action,json={'tenant':'nexus','confirm':True,'request':request},headers=self.headers)
        lead={'lead_id':'lead-demo','name':'Cliente demo','email':'demo@example.invalid','dataset':'demo','channel':'paid','evidence_ref':'synthetic-intake'}
        self.assertEqual(save('intake',lead).status_code,200)
        funnel=self.client.get('/api/funnel?tenant=nexus&dataset=demo',headers=self.headers).json()
        self.assertEqual(funnel['followups']['active_leads'],1)
        self.assertNotIn('demo@example.invalid',json.dumps(funnel))
        event={'event_id':'stage-demo','lead_id':'lead-demo','kind':'followup_due','channel':'paid','evidence_ref':'synthetic-followup','followup_due':'2026-11-01'}
        self.assertEqual(save('event',event).status_code,200)
        win={'event_id':'won-demo','lead_id':'lead-demo','payment_id':'payment-demo','dataset':'demo','channel':'organic','evidence_ref':'synthetic-sale','amount_minor':120000,'cost_minor':0,'currency':'MXN'}
        self.assertEqual(save('win',win).status_code,400)
        with closing(Engine(str(self.state),json.loads(self.cfg.read_text()),'nexus')) as e:
            self.assertIsNone(e.record('payment','payment-demo'))
        win['channel']='paid'
        self.assertEqual(save('win',win).status_code,200)
        self.assertTrue(save('win',win).json()['replayed'])
        funnel=self.client.get('/api/funnel?tenant=nexus&dataset=demo',headers=self.headers).json()
        self.assertEqual(funnel['sales']['reported_paid_clients'],1)
        self.assertEqual(funnel['followups']['active_leads'],0)
        self.assertEqual(self.client.get('/api/funnel?tenant=nexus&dataset=real',headers=self.headers).json()['sales']['reported_paid_clients'],0)

    def test_new_routes_reject_viewers_and_cross_origin(self):
        viewer=TestClient(create_app(self.cfg,str(self.state),TOKEN,role='viewer'),base_url='http://127.0.0.1:8766');self.addCleanup(viewer.close)
        for path in ('/api/tenants','/api/ads/import','/api/sales/intake','/api/sales/event','/api/sales/win'):
            self.assertEqual(viewer.post(path,json={},headers=self.headers).status_code,403)
            self.assertEqual(self.client.post(path,json={},headers=self.headers|{'Origin':'https://evil.invalid'}).status_code,403)

    def test_installation_and_complete_backup_require_private_config_and_confirmation(self):
        self.cfg.chmod(0o600)
        before=self.client.get('/api/installation',headers=self.headers)
        self.assertEqual(before.status_code,200)
        self.assertFalse(next(c for c in before.json()['checks'] if c['id']=='recent_backup')['ok'])
        route='/api/maintenance/backup'
        self.assertEqual(self.client.post(route,json={'confirm':False},headers=self.headers).status_code,400)
        self.assertEqual(self.client.post(route,json={'confirm':True,'to':'/tmp/forbidden'},headers=self.headers).status_code,400)
        saved=self.client.post(route,json={'confirm':True},headers=self.headers)
        self.assertEqual(saved.status_code,200,saved.text)
        from verdugo.maintenance import verify_set
        self.assertTrue(verify_set(saved.json()['saved_directory'])['restore_allowed'])
        after=self.client.get('/api/installation',headers=self.headers)
        self.assertTrue(next(c for c in after.json()['checks'] if c['id']=='recent_backup')['ok'])
        self.assertFalse(after.json()['commercial_results_verified'])
        self.assertNotIn('demo@example.invalid',after.text)
        viewer=TestClient(create_app(self.cfg,str(self.state),TOKEN,role='viewer'),base_url='http://127.0.0.1:8766');self.addCleanup(viewer.close)
        self.assertEqual(viewer.post(route,json={'confirm':True},headers=self.headers).status_code,403)
        self.assertEqual(self.client.post(route,json={'confirm':True},headers=self.headers|{'Origin':'https://evil.invalid'}).status_code,403)
        self.assertEqual(self.client.post('/api/maintenance/restore',json={},headers=self.headers).status_code,404)

    def test_closed_loop_intake_phone_and_read_only_status(self):
        lead={'lead_id':'cycle-demo','name':'cliente-demo','email':'demo@example.invalid','dataset':'real',
              'channel':'paid','evidence_ref':'synthetic-intake','ref_code':'ABC234','phone':'+1 (555) 000-0000'}
        def save(action,data):return self.client.post('/api/sales/'+action,json={'tenant':'nexus','confirm':True,'request':data},headers=self.headers)
        self.assertEqual(save('intake',lead|{'ref_code':'bad'}).status_code,400)
        self.assertEqual(save('intake',lead).status_code,200)
        from datetime import datetime,timezone
        paid=datetime.now(timezone.utc).isoformat(timespec='seconds')
        win={'event_id':'cycle-won','lead_id':'cycle-demo','payment_id':'cycle-payment','dataset':'real','channel':'paid',
             'evidence_ref':'synthetic-paid','amount_minor':10000,'cost_minor':0,'currency':'MXN','paid_at':paid}
        self.assertEqual(save('win',win).status_code,200)
        report=self.client.get('/api/closed-loop?tenant=nexus',headers=self.headers)
        self.assertEqual(200,report.status_code);self.assertEqual(1,report.json()['leads_with_reference'])
        self.assertEqual(1,report.json()['won_leads_with_reference']);self.assertIsNone(report.json()['whatsapp_clicks_with_reference'])
        self.assertNotIn('+15550000000',report.text)
        with closing(Engine(str(self.state),json.loads(self.cfg.read_text()),'nexus')) as e:
            import hashlib
            self.assertEqual(hashlib.sha256(b'+15550000000').hexdigest(),e.db.execute('SELECT phone_hash FROM cycle_leads').fetchone()[0])
            for value in ('+15550000000','+1 (555) 000-0000'):self.assertNotIn(value,'\n'.join(e.db.iterdump()))
        self.assertEqual(404,self.client.post('/api/closed-loop/run',json={},headers=self.headers).status_code)
        self.post('register',{'confirm':True,'label':'cliente-demo'})
        self.assertEqual(400,self.client.get('/api/closed-loop?tenant=cliente-demo',headers=self.headers).status_code)
