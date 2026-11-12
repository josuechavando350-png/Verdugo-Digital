import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from verdugo.adapters import SPECS, build
from verdugo.catalog import catalog, graph
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.__main__ import template
from verdugo.transport import TransportError
from verdugo import workflow

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'synthetic-key:synthetic-secret-not-real'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'state.sqlite3'
        self.config = template('nexus')
        for cfg in self.config['tenants']['nexus']['services'].values():
            cfg.update(enabled=True, license_reviewed=True, version='contract-fixture-only')
        self.config['tenants']['other'] = copy.deepcopy(self.config['tenants']['nexus'])
        self.env = patch.dict(os.environ, {c['token_env']: SECRET for c in
            self.config['tenants']['nexus']['services'].values() if 'token_env' in c})
        self.env.start()
        self.calls = []
        def transport(req, cfg):
            self.calls.append(req['public'])
            return {'data': {'createPerson': {'id': 'fixture'}}, 'payload': {'contact': {'id': 42}}, 'token': SECRET,
                    'echo': 'Bearer '+SECRET}
        self.transport = transport
        self.engine = Engine(self.path, self.config, transport=transport)

    def tearDown(self):
        self.engine.close()
        self.env.stop()
        self.tmp.cleanup()

    def command(self, service='twenty', operation='people.list', params=None, key='test-1'):
        return {'service': service, 'operation': operation, 'params': params or {}, 'key': key}

    def write(self, key='write-1'):
        return self.command(operation='people.create', key=key,
                            params={'first_name':'Demo', 'email':'demo@example.invalid'})

    def approve(self, command):
        plan = self.engine.plan(command)
        a = Engine(self.path, self.config, role='approver', actor='local-human')
        try: a.approve(command['key'], plan['fingerprint'])
        finally: a.close()
        return plan

    def lead(self, dataset='demo', key='capture', lead_id='lead-1'):
        return self.command('core','lead.capture',
            {'lead_id':lead_id,'name':'Ficticio','email':'demo@example.invalid','dataset':dataset}, key)

    def pay(self, dataset='demo', key='pay', payment_id='payment-1', currency='MXN'):
        return self.command('core','payment.record',
            {'payment_id':payment_id,'lead_id':'lead-1','amount_minor':3000000,
             'cost_minor':1200000,'currency':currency,'evidence_ref':'synthetic', 'dataset':dataset}, key)

    def metrics(self, dataset='real', currency='MXN', key='metrics'):
        return self.engine.execute(self.command('core','metrics.summary',
              {'dataset':dataset,'currency':currency}, key), True)['result']


class CatalogTests(Base):
    def test_exact_100_unique(self):
        rows=catalog()
        self.assertEqual(100,len(rows))
        self.assertEqual(100,len({r['id'] for r in rows}))
        self.assertEqual(100,len({r['repository'] for r in rows}))

    def test_no_false_live_status(self):
        s=self.engine.status()
        self.assertEqual(30,s['api_adapters_implemented'])
        self.assertEqual(0,s['live_verified'])
        self.assertFalse(any(r['live_verified'] for r in s['integrations']))

    def test_logical_graph_has_every_project(self):
        g=graph(SPECS)
        self.assertEqual(101,len(g['nodes']))
        self.assertEqual(100,len(g['edges']))
        self.assertEqual(30,sum(e['kind']=='adapter' for e in g['edges']))
        self.assertFalse(any(e['live'] for e in g['edges']))

    def test_template_disabled(self):
        self.assertEqual(100,len(template('nexus')['tenants']['nexus']['services']))
        self.assertFalse(any(c['enabled'] for c in template('nexus')['tenants']['nexus']['services'].values()))

    def test_all_recipes_build(self):
        for sid, ops in SPECS.items():
            for op in ops:
                with self.subTest(service=sid,op=op):
                    params=({'first_name':'Demo','email':'demo@example.invalid'} if op.endswith('create')
                            else {'query':'up'} if sid=='prometheus'
                            else {'remote_id':'42'} if op.endswith('.get') else {})
                    req=build(sid,op,params,self.config['tenants']['nexus']['services'][sid])
                    self.assertTrue(req['public']['url'].startswith('https://example.invalid/'))
                    self.assertNotIn(SECRET,json.dumps(req['public']))


class PolicyTests(Base):
    def test_preview_no_network(self):
        self.assertEqual('planned',self.engine.execute(self.command())['state'])
        self.assertEqual([],self.calls)

    def test_read_executes_once_and_redacts(self):
        out=self.engine.execute(self.command(),True)
        self.assertEqual('succeeded',out['state'])
        self.assertNotIn(SECRET,json.dumps(out))
        self.assertEqual(1,len(self.calls))
        self.assertTrue(self.engine.execute(self.command(),True)['replayed'])
        self.assertEqual(1,len(self.calls))

    def test_disabled_blocks(self):
        self.config['tenants']['nexus']['services']['twenty']['enabled']=False
        with self.assertRaises(VerdugoError): self.engine.execute(self.command(),True)
        self.assertFalse(self.calls)

    def test_license_review_required(self):
        self.config['tenants']['nexus']['services']['twenty']['license_reviewed']=False
        with self.assertRaises(VerdugoError): self.engine.plan(self.command())

    def test_version_cannot_be_latest(self):
        self.config['tenants']['nexus']['services']['twenty']['version']='latest'
        with self.assertRaises(VerdugoError): self.engine.plan(self.command())

    def test_missing_credentials(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(VerdugoError): self.engine.plan(self.command())

    def test_unknown_adapter_fails_closed(self):
        with self.assertRaises(VerdugoError): self.engine.execute(self.command('whisper','transcribe'),True)
        self.assertFalse(self.calls)

    def test_unknown_action_fails_closed(self):
        with self.assertRaises(VerdugoError): self.engine.execute(self.command('chatwoot','message.send'),True)
        self.assertFalse(self.calls)

    def test_write_pauses_without_approval(self):
        self.assertEqual('awaiting_approval',self.engine.execute(self.write(),True)['state'])
        self.assertFalse(self.calls)

    def test_operator_cannot_approve(self):
        p=self.engine.plan(self.write())
        with self.assertRaises(VerdugoError): self.engine.approve('write-1',p['fingerprint'])

    def test_write_after_exact_approval(self):
        self.approve(self.write())
        self.assertEqual('succeeded',self.engine.execute(self.write(),True)['state'])
        self.assertEqual(1,len(self.calls))
        self.engine.execute(self.write(),True)
        self.assertEqual(1,len(self.calls))

    def test_changed_input_invalidates_key(self):
        self.approve(self.write())
        cmd=self.write();cmd['params']['email']='another@example.invalid'
        with self.assertRaises(VerdugoError): self.engine.execute(cmd,True)
        self.assertFalse(self.calls)

    def test_changed_credentials_invalidate_approval(self):
        self.approve(self.write())
        name=self.config['tenants']['nexus']['services']['twenty']['token_env']
        with patch.dict(os.environ,{name:'another-synthetic-credential'}):
            with self.assertRaises(VerdugoError): self.engine.execute(self.write(),True)
        self.assertFalse(self.calls)

    def test_expired_approval(self):
        self.approve(self.write())
        self.engine.db.execute('UPDATE plans SET expires=0')
        self.assertEqual('awaiting_approval',self.engine.execute(self.write(),True)['state'])
        self.assertFalse(self.calls)

    def test_uncertain_write_never_retries(self):
        self.approve(self.write())
        calls=[]
        def fail(req,cfg):
            calls.append(req);raise TransportError('Connection failed')
        self.engine.transport=fail
        self.assertEqual('uncertain',self.engine.execute(self.write(),True)['state'])
        self.assertEqual('uncertain',self.engine.execute(self.write(),True)['state'])
        self.assertEqual(1,len(calls))

    def test_viewer_cannot_execute(self):
        e=Engine(self.path,self.config,role='viewer',transport=self.transport)
        try:
            with self.assertRaises(VerdugoError):e.execute(self.command(),True)
        finally:e.close()

    def test_approver_cannot_execute(self):
        e=Engine(self.path,self.config,role='approver',transport=self.transport)
        try:
            with self.assertRaises(VerdugoError):e.execute(self.command(),True)
        finally:e.close()

    def test_idempotency_survives_restart(self):
        self.engine.execute(self.command(),True)
        e=Engine(self.path,self.config,transport=self.transport)
        try:self.assertTrue(e.execute(self.command(),True)['replayed'])
        finally:e.close()
        self.assertEqual(1,len(self.calls))

    def test_two_workers_claim_once(self):
        barrier=threading.Barrier(2);out=[];lock=threading.Lock();calls=[]
        def transport(req,cfg):
            with lock:calls.append(req)
            time.sleep(.05)
            return {'ok':True}
        def worker():
            e=Engine(self.path,self.config,transport=transport)
            try:
                barrier.wait(timeout=2)
                out.append(e.execute(self.command(),True))
            except Exception as exc:out.append(exc)
            finally:e.close()
        ts=[threading.Thread(target=worker) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(5)
        self.assertEqual(2,len(out));self.assertFalse(any(isinstance(o,Exception) for o in out))
        self.assertEqual(1,len(calls))

    def test_reject_tenant_override_and_arbitrary_params(self):
        cmd=self.command();cmd['tenant']='other'
        with self.assertRaises(VerdugoError):self.engine.plan(cmd)
        with self.assertRaises(VerdugoError):self.engine.plan(self.command(params={'url':'https://evil.invalid'}))

    def test_execute_requires_boolean(self):
        with self.assertRaises(VerdugoError): self.engine.execute(self.command(),'true')

    def test_account_bound_by_configuration(self):
        with self.assertRaises(VerdugoError):
            self.engine.plan(self.command('chatwoot','conversations.list',{'account_id':999}))

    def test_bounded_query_and_pagination(self):
        with self.assertRaises(VerdugoError):
            self.engine.plan(self.command('prometheus','query',{'query':'expensive-expression'}))
        with self.assertRaises(VerdugoError):self.engine.plan(self.command(params={'page':999999}))

    def test_no_public_plaintext_http(self):
        self.config['tenants']['nexus']['services']['twenty']['base_url']='http://example.com'
        with self.assertRaises(VerdugoError):self.engine.plan(self.command())

    def test_no_credentials_in_events_or_database(self):
        self.engine.execute(self.command(),True)
        content='\n'.join(self.engine.db.iterdump())
        self.assertNotIn(SECRET,content)

    def test_unknown_tenant(self):
        with self.assertRaises(VerdugoError):Engine(':memory:',self.config,tenant='absent')

    def test_failed_sqlite_bootstrap_closes_open_connection(self):
        from unittest.mock import patch
        import sqlite3
        from verdugo import engine as module
        original = sqlite3.connect
        connections = []
        def tracked(*args, **kwargs):
            db = original(*args, **kwargs)
            connections.append(db)
            return db
        with patch.object(module.sqlite3, 'connect', side_effect=tracked):
            with patch.object(module.pilot, 'SCHEMA', 'THIS IS NOT VALID SQLITE;'):
                with self.assertRaises(sqlite3.DatabaseError):
                    Engine(self.path, self.config)
        self.assertEqual(1, len(connections))
        with self.assertRaises(sqlite3.ProgrammingError):
            connections[0].execute('SELECT 1')

    def test_invalid_configuration(self):
        with self.assertRaises(VerdugoError):Engine(':memory:',[])


class CommercialTests(Base):
    def test_demo_is_end_to_end_and_offline(self):
        spec=json.loads((ROOT/'examples/demo.json').read_text())
        result=workflow.run(self.engine,spec,True)
        self.assertEqual('succeeded',result['state'])
        self.assertEqual(1800000,result['steps']['summary']['reported_contribution_minor'])
        self.assertFalse(self.calls)
        self.assertEqual(0,self.metrics()['reported_receipts_minor'])

    def test_demo_resume_does_not_double_count(self):
        spec=json.loads((ROOT/'examples/demo.json').read_text())
        workflow.run(self.engine,spec,True);workflow.run(self.engine,spec,True)
        self.assertEqual(3000000,self.metrics('demo')['reported_receipts_minor'])

    def test_tenants_cannot_read_each_others_records(self):
        self.engine.execute(self.lead(),True);self.engine.execute(self.pay(),True)
        e=Engine(self.path,self.config,tenant='other')
        try:
            self.assertIsNone(e.record('lead','lead-1'))
            self.assertEqual([],e.events())
            result=e.execute(self.pay(),True)
            self.assertEqual('failed',result['state'])
        finally:e.close()

    def test_duplicate_payment_different_command_key(self):
        self.engine.execute(self.lead(),True)
        self.engine.execute(self.pay(),True);self.engine.execute(self.pay(key='pay-again'),True)
        self.assertEqual(3000000,self.metrics('demo')['reported_receipts_minor'])

    def test_conflicting_payment_rolls_back(self):
        self.engine.execute(self.lead(),True);self.engine.execute(self.pay(),True)
        cmd=self.pay(key='changed-payment');cmd['params']['amount_minor']=4000000
        self.assertEqual('failed',self.engine.execute(cmd,True)['state'])
        self.assertEqual(3000000,self.metrics('demo')['reported_receipts_minor'])

    def test_currencies_are_not_added_together(self):
        self.engine.execute(self.lead(),True)
        self.engine.execute(self.pay(),True)
        self.engine.execute(self.pay(key='usd-payment',payment_id='usd-1',currency='USD'),True)
        self.assertEqual(3000000,self.metrics('demo')['reported_receipts_minor'])

    def test_money_rejects_float_boolean_negative(self):
        for value in (3.14, True, -1):
            cmd=self.pay();cmd['params']['amount_minor']=value
            with self.assertRaises(VerdugoError):self.engine.plan(cmd)

    def test_no_fake_reconciled_profit_or_probability(self):
        result=self.metrics()
        self.assertIsNone(result['commercial_success_probability'])
        self.assertIsNone(result['reconciled_receipts_minor'])

    def test_missing_evidence_rejected(self):
        cmd=self.pay();del cmd['params']['evidence_ref']
        with self.assertRaises(VerdugoError):self.engine.plan(cmd)

    def test_audit_cursor(self):
        self.engine.execute(self.lead(),True)
        es=self.engine.events()
        self.assertEqual(2,len(es))
        self.assertEqual(1,len(self.engine.events(es[0]['id'])))


class WorkflowTests(Base):
    def spec(self):return json.loads((ROOT/'examples/demo.json').read_text())

    def test_dry_run_has_no_business_records(self):
        self.assertEqual('planned',workflow.run(self.engine,self.spec())['state'])
        self.assertIsNone(self.engine.record('lead','synthetic-1'))

    def test_cycle_blocked_before_execution(self):
        spec=self.spec();spec['steps'][0]['depends_on']=['summary']
        with self.assertRaises(VerdugoError):workflow.run(self.engine,spec,True)
        self.assertIsNone(self.engine.record('lead','synthetic-1'))

    def test_undeclared_reference_blocked(self):
        spec=self.spec();spec['steps'][1]['depends_on']=[]
        with self.assertRaises(VerdugoError):workflow.run(self.engine,spec,True)

    def test_duplicate_nodes_blocked(self):
        spec=self.spec();spec['steps'].append(copy.deepcopy(spec['steps'][0]))
        with self.assertRaises(VerdugoError):workflow.run(self.engine,spec,True)

    def test_missing_adapter_blocks_entire_dag(self):
        spec=self.spec();spec['steps'].append({'id':'missing','service':'whisper','operation':'transcribe','params':{}})
        with self.assertRaises(VerdugoError):workflow.run(self.engine,spec,True)
        self.assertIsNone(self.engine.record('lead','synthetic-1'))

    def test_pause_on_approval_and_resume(self):
        spec=json.loads((ROOT/'examples/contact-bridge.json').read_text())
        paused=workflow.run(self.engine,spec,True)
        self.assertEqual('crm',paused['step'])
        a=Engine(self.path,self.config,role='approver')
        try:a.approve(paused['outcome']['key'],paused['outcome']['fingerprint'])
        finally:a.close()
        paused=workflow.run(self.engine,spec,True)
        self.assertEqual('inbox',paused['step']);self.assertEqual(1,len(self.calls))
        a=Engine(self.path,self.config,role='approver')
        try:a.approve(paused['outcome']['key'],paused['outcome']['fingerprint'])
        finally:a.close()
        self.assertEqual('succeeded',workflow.run(self.engine,spec,True)['state'])
        self.assertEqual(2,len(self.calls))

class BatchTests(Base):
    def test_single_approval_for_entire_static_contact_bridge(self):
        spec=json.loads((ROOT/'examples/contact-bridge.json').read_text())
        plan=workflow.run(self.engine,spec)
        self.assertEqual(2,len(plan['approval_batch']))
        self.assertFalse(self.calls)
        a=Engine(self.path,self.config,role='approver')
        try:a.approve_many(plan['approval_batch'])
        finally:a.close()
        self.assertEqual('succeeded',workflow.run(self.engine,spec,True)['state'])
        self.assertEqual(2,len(self.calls))

    def test_approval_batch_is_atomic(self):
        p=self.engine.plan(self.write())
        a=Engine(self.path,self.config,role='approver')
        try:
            with self.assertRaises(VerdugoError):
                a.approve_many([{'key':p['key'],'fingerprint':p['fingerprint']},
                                {'key':'unknown','fingerprint':'invalid'}])
        finally:a.close()
        row=self.engine.db.execute('SELECT approved_by FROM plans WHERE key=?',('write-1',)).fetchone()
        self.assertIsNone(row['approved_by'])

    def test_static_credentials_checked_before_first_business_effect(self):
        spec=json.loads((ROOT/'examples/demo.json').read_text())
        spec['steps'].append({'id':'read','service':'twenty','operation':'people.list','params':{}})
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(VerdugoError):workflow.run(self.engine,spec,True)
        self.assertIsNone(self.engine.record('lead','synthetic-1'))
