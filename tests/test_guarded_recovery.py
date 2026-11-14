"""Regression tests for cooperative local recovery; no real providers or contacts."""
import copy
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from test_core import Base, SECRET
from verdugo import recovery, jobs, readback
from verdugo.common import VerdugoError, encode
from verdugo.engine import Engine
from verdugo.guards import GuardBusy
from verdugo.mcp import invoke, Session, tool_definitions
from verdugo.transport import TransportError


class RecoveryBase(Base):
    def setUp(self):
        super().setUp()
        for sid,path in (('twenty','data.person'),('chatwoot','payload')):
            self.config['tenants']['nexus']['services'][sid].update(readback_reviewed=True,readback_record_path=path)
        self.config['tenants']['other'] = copy.deepcopy(self.config['tenants']['nexus'])

    def approver(self):
        return Engine(self.path, self.config, role='approver', actor='human-reviewer')

    def interrupted(self, service='twenty', running=False, key='interrupted'):
        command = self.command(service, 'people.create' if service=='twenty' else 'contacts.create',
                               {'first_name':'Demo', 'last_name':'Person', 'email':'demo@example.invalid'}, key)
        plan = self.approve(command)
        def fail(req, cfg):
            self.calls.append(req['public'])
            if running: raise KeyboardInterrupt()
            raise TransportError('Synthetic lost write response')
        self.engine.transport = fail
        if running:
            with self.assertRaises(KeyboardInterrupt): self.engine.execute(command, True)
        else: self.assertEqual('uncertain', self.engine.execute(command, True)['state'])
        self.engine.transport = self.read_transport
        return command, {'key':key, 'fingerprint':plan['fingerprint']}

    def body(self, service='twenty', rid=None):
        if service == 'twenty':
            return {'data':{'person':{'id':rid or 'remote-1','emails':{'primaryEmail':'demo@example.invalid'},
                                     'name':{'firstName':'Demo','lastName':'Person'}}}, 'token':SECRET}
        return {'payload':{'id':int(rid or '42'), 'email':'demo@example.invalid', 'name':'Demo Person',
                           'contact_inboxes':[{'inbox':{'id':1}}]}, 'token':SECRET}

    def read_transport(self, req, cfg):
        self.calls.append(req['public'])
        if req['public']['method'] == 'GET': return self.body(req['public']['service'])
        return {'data': {'createPerson': {'id': 'remote-1'}}, 'payload': {'contact': {'id': 42}}}

    def state(self, key='interrupted'):
        return self.engine.db.execute('SELECT state FROM runs WHERE tenant=? AND key=?', ('nexus',key)).fetchone()[0]


class GuardTests(RecoveryBase):
    def test_new_run_records_persistent_guard(self):
        self.engine.execute(self.lead(), True)
        row = self.engine.db.execute('SELECT * FROM run_guards').fetchone()
        self.assertEqual('local-flock-v1',row['scheme']); self.assertEqual('nexus',row['tenant'])
        self.assertEqual(self.engine.guards.scope,row['scope'])

    def test_interrupted_contact_requires_explicit_recovery(self):
        command, request = self.interrupted(running=True)
        self.assertEqual('running',self.engine.execute(command,True)['state'])
        a = self.approver()
        try:
            self.assertEqual('planned',recovery.recover_running(a,request)['state'])
            self.assertEqual('running',self.state())
            result = recovery.recover_running(a,request,True)
            self.assertEqual('uncertain',result['state']); self.assertFalse(result['post_retry_authorized'])
        finally: a.close()
        self.assertEqual('uncertain',self.engine.execute(command,True)['state'])
        self.assertEqual(1,len(self.calls))
        self.assertEqual(1,self.engine.db.execute('SELECT used FROM plans WHERE key=?',('interrupted',)).fetchone()[0])

    def test_active_guard_blocks_recovery_preview_and_execution(self):
        _, request = self.interrupted(running=True)
        a = self.approver()
        try:
            with self.engine.guards.hold('nexus','interrupted'):
                with self.assertRaises(GuardBusy): recovery.recover_running(a,request,True)
                with self.assertRaises(GuardBusy): recovery.recover_running(a,request)
            self.assertEqual('running',self.state())
        finally: a.close()

    def test_legacy_running_without_guard_cannot_be_recovered(self):
        _, request = self.interrupted(running=True)
        self.engine.db.execute('DELETE FROM run_guards')
        a = self.approver()
        try:
            with self.assertRaises(VerdugoError): recovery.recover_running(a,request,True)
        finally: a.close()
        self.assertEqual('running',self.state())

    def test_recovery_refuses_different_state_file_scope(self):
        _, request = self.interrupted(running=True)
        self.engine.db.execute("UPDATE run_guards SET scope='not-this-file'")
        a = self.approver()
        try:
            with self.assertRaises(VerdugoError): recovery.recover_running(a,request,True)
        finally: a.close()

    def test_recovery_requires_approver_exact_fingerprint_and_boolean(self):
        _, request = self.interrupted(running=True)
        with self.assertRaises(VerdugoError): recovery.recover_running(self.engine,request,True)
        a = self.approver()
        try:
            for req,execute in ((request|{'fingerprint':'bad'},True),(request,'yes'),(request|{'tenant':'other'},True)):
                with self.assertRaises(VerdugoError): recovery.recover_running(a,req,execute)
        finally: a.close()

    def test_recovery_is_not_a_generic_action_reset(self):
        cmd = self.command(key='read-interrupted')
        plan = self.engine.plan(cmd)
        def stopped(*args): raise KeyboardInterrupt()
        self.engine.transport = stopped
        with self.assertRaises(KeyboardInterrupt): self.engine.execute(cmd,True)
        a = self.approver()
        try:
            with self.assertRaises(VerdugoError): recovery.recover_running(a,{'key':cmd['key'],'fingerprint':plan['fingerprint']},True)
        finally: a.close()

    def test_guard_survives_new_engine_and_symlink_alias(self):
        alias = Path(self.tmp.name)/'alias.sqlite3'; alias.symlink_to(self.path)
        e = Engine(alias,self.config)
        try:
            self.assertEqual(self.engine.guards.scope,e.guards.scope)
            with self.engine.guards.hold('nexus','same-key'):
                with self.assertRaises(GuardBusy):
                    with e.guards.hold('nexus','same-key'): pass
        finally: e.close()

    def test_distinct_tenant_or_key_does_not_share_lock(self):
        with self.engine.guards.hold('nexus','key'):
            with self.engine.guards.hold('other','key'): pass
            with self.engine.guards.hold('nexus','another'): pass

    def test_lock_files_are_private_and_never_deleted_on_release(self):
        with self.engine.guards.hold('nexus','key'):
            files = list(self.engine.guards.root.glob('*.lock'))
            self.assertEqual(1,len(files)); self.assertEqual(0o600,files[0].stat().st_mode & 0o777)
        self.assertTrue(files[0].exists())
        self.assertEqual(0o700,self.engine.guards.root.stat().st_mode & 0o777)

    def test_unsupported_flock_fails_closed_before_effect(self):
        with patch('verdugo.guards.fcntl',None):
            with self.assertRaises(VerdugoError): self.engine.execute(self.lead(),True)
        self.assertIsNone(self.engine.record('lead','lead-1'))

    def test_memory_demo_remains_supported_but_is_not_recoverable(self):
        e = Engine(':memory:')
        try:
            self.assertEqual('succeeded',e.execute(self.lead(),True)['state'])
            with self.assertRaises(VerdugoError): e.guards.require_record(e,'capture')
        finally:e.close()

    def test_recovery_and_audit_update_are_atomic(self):
        _,request = self.interrupted(running=True)
        self.engine.db.execute("CREATE TRIGGER deny_recovery BEFORE INSERT ON events WHEN NEW.kind='action.running_recovered' "
                               "BEGIN SELECT RAISE(ABORT,'fixture'); END")
        a=self.approver()
        try:
            with self.assertRaises(sqlite3.IntegrityError): recovery.recover_running(a,request,True)
        finally:a.close()
        self.assertEqual('running',self.state())

    def test_real_child_process_must_exit_before_guard_recovery(self):
        command=self.write('child-write'); plan=self.approve(command)
        config=Path(self.tmp.name)/'process-config.json'; config.write_text(encode(self.config))
        script='''
import json,sys,time
from verdugo.engine import Engine
cfg=json.load(open(sys.argv[2]))
def held(req,cfg):
 print('write-started',flush=True)
 time.sleep(60)
 return {'data':{'createPerson':{'id':'never-returned'}}}
e=Engine(sys.argv[1],cfg,transport=held)
e.execute(json.loads(sys.argv[3]),True)
'''
        proc=subprocess.Popen([sys.executable,'-c',script,str(self.path),str(config),encode(command)],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        a=self.approver()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout,selectors.EVENT_READ)
                self.assertTrue(selector.select(timeout=8),'child did not enter transport')
            self.assertEqual('write-started',proc.stdout.readline().strip())
            req={'key':command['key'],'fingerprint':plan['fingerprint']}
            with self.assertRaises(GuardBusy): recovery.recover_running(a,req,True)
            proc.kill();proc.wait(timeout=5)
            self.assertEqual('uncertain',recovery.recover_running(a,req,True)['state'])
            self.assertEqual('uncertain',self.engine.execute(command,True)['state'])
            self.assertFalse(self.calls)
        finally:
            if proc.poll() is None: proc.kill();proc.wait(timeout=5)
            proc.stdout.close();proc.stderr.close();a.close()


class PersistenceRegressionTests(RecoveryBase):
    def test_new_connections_do_not_open_close_database_outside_sqlite(self):
        real_open=os.open
        def checked(path,*args,**kwargs):
            if Path(path).resolve()==self.path.resolve():
                raise AssertionError('Application must not open/close the live SQLite file')
            return real_open(path,*args,**kwargs)
        with patch('os.open',side_effect=checked):
            e=Engine(self.path,self.config)
            try:self.assertEqual('succeeded',e.execute(self.lead(),True)['state'])
            finally:e.close()

    def test_cross_process_updates_remain_visible_after_sibling_connection_closes(self):
        cfg=Path(self.tmp.name)/'persistent-config.json';cfg.write_text(encode(self.config))
        base=[sys.executable,'-m','verdugo','--state',str(self.path),'--config',str(cfg)]
        for i in range(3):
            a=self.approver();a.close()
            cmd=self.lead(key='child-'+str(i),lead_id='child-'+str(i))
            out=subprocess.run(base+['run',encode(cmd),'--execute'],capture_output=True,text=True,timeout=10)
            self.assertEqual(0,out.returncode,out.stderr)
            self.assertIsNotNone(self.engine.record('lead','child-'+str(i)))
            self.engine.execute(self.lead(key='parent-'+str(i),lead_id='parent-'+str(i)),True)
        e=Engine(self.path,self.config)
        try:
            self.assertEqual(6,e.db.execute("SELECT COUNT(*) FROM records WHERE kind='lead'").fetchone()[0])
            self.assertEqual('ok',e.db.execute('PRAGMA integrity_check').fetchone()[0])
        finally:e.close()

    def test_state_in_shared_directory_is_rejected_before_creation(self):
        parent=Path(self.tmp.name)/'shared';parent.mkdir(mode=0o755);parent.chmod(0o755)
        with self.assertRaises(VerdugoError):Engine(parent/'db.sqlite3',self.config)
        self.assertFalse((parent/'db.sqlite3').exists())

    def test_hard_link_alias_is_rejected(self):
        link = getattr(os, 'link', None)
        if not callable(link): self.skipTest('Python does not expose os.link on this platform')
        alias=Path(self.tmp.name)/'linked.sqlite3'
        try:
            link(self.path, alias)
        except (NotImplementedError, OSError) as exc:
            self.skipTest('Hard links are unsupported by this filesystem: '+str(exc))
        try:
            with self.assertRaises(VerdugoError):Engine(alias,self.config)
        finally:alias.unlink()



class IntegrationTests(RecoveryBase):
    def test_queue_recovery_uses_current_readback_without_duplicate_creation(self):
        from verdugo.ingress import accept, signature
        self.config['tenants']['nexus']['ingress']={'website':{
            'enabled':True,'secret_env':'VERDUGO_TEST_INGRESS','handler':'contact.bridge',
            'dataset':'demo','max_pending':10,'max_attempts':3}}
        signing=b'synthetic-signing-key-not-production-0123456789'
        body=encode({'id':'queued-event','type':'contact.submitted','data':{'external_id':'queued-person',
                     'first_name':'Demo','last_name':'Person','email':'demo@example.invalid'}}).encode()
        timestamp=str(int(time.time()))
        with patch.dict(os.environ,{'VERDUGO_TEST_INGRESS':signing.decode()}):
            reply=accept(self.engine,'website',body,timestamp,signature(signing,'nexus','website',timestamp,body))
        jid=reply['job_id'];plan=jobs.plan(self.engine,jid)['plan'];a=self.approver()
        try:a.approve_many(plan['approval_batch'])
        finally:a.close()
        def interrupted(req,cfg):
            self.calls.append(req['public']);raise KeyboardInterrupt()
        self.engine.transport=interrupted
        with self.assertRaises(KeyboardInterrupt):jobs.work(self.engine,True)
        source=self.engine.db.execute("SELECT key,hash FROM runs WHERE state='running'").fetchone()
        request={'key':source['key'],'fingerprint':source['hash']}
        a=self.approver()
        try:self.assertEqual('uncertain',recovery.recover_running(a,request,True)['state'])
        finally:a.close()
        self.engine.transport=self.read_transport
        checked=readback.verify(self.engine,request|{'remote_id':'remote-1','check_id':'queued-check'},True)
        self.assertEqual('matched',checked['state'])
        self.assertFalse(checked['creation_proven'])
        a=self.approver()
        try:
            readback.confirm(a,{'check_id':'queued-check','fingerprint':checked['fingerprint'],
                                'evidence_ref':'synthetic-local-review'})
        finally:a.close()
        # The crashed queue lease must expire independently; do not reset the run or job keys.
        self.engine.db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(jid,))
        self.assertEqual('succeeded',jobs.work(self.engine,True)['state'])
        self.assertEqual(['POST','GET','POST'],[c['method'] for c in self.calls])
        self.assertEqual(2,self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])
        self.assertEqual('idle',jobs.work(self.engine,True)['state'])

    def test_recovery_cli_preview_then_execute_and_no_auto_success(self):
        _,request=self.interrupted(running=True)
        config=Path(self.tmp.name)/'cli-config.json';config.write_text(encode(self.config))
        command=[sys.executable,'-m','verdugo','--config',str(config),'--state',str(self.path),
                 '--role','approver','recover-running',encode(request)]
        preview=subprocess.run(command,capture_output=True,text=True,timeout=10)
        self.assertEqual(0,preview.returncode,preview.stderr)
        self.assertEqual('planned',json.loads(preview.stdout)['state']);self.assertEqual('running',self.state())
        done=subprocess.run(command+['--execute'],capture_output=True,text=True,timeout=10)
        self.assertEqual(1,done.returncode,done.stderr)
        self.assertEqual('uncertain',json.loads(done.stdout)['state']);self.assertEqual('uncertain',self.state())
        self.assertEqual(1,len(self.calls))

    def test_no_mcp_self_recovery_or_new_tool_count(self):
        names={x['name'] for x in tool_definitions()}
        self.assertEqual(23,len(names));self.assertNotIn('verdugo_recover_running',names)
        with self.assertRaises(VerdugoError):invoke(self.engine,'verdugo_recover_running',{})

    def test_mcp_running_is_not_reported_as_completed(self):
        command,_=self.interrupted(running=True)
        session=Session(self.engine)
        session.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}})
        session.handle({'jsonrpc':'2.0','method':'notifications/initialized'})
        out=session.handle({'jsonrpc':'2.0','id':2,'method':'tools/call',
            'params':{'name':'verdugo_execute','arguments':{'command':command,'execute':True}}})
        self.assertTrue(out['result']['isError'])
        self.assertEqual('running',json.loads(out['result']['content'][0]['text'])['state'])
        self.assertEqual(1,len(self.calls))

    def test_tenant_and_stored_plan_integrity_are_checked(self):
        _,request=self.interrupted(running=True)
        a=Engine(self.path,self.config,tenant='other',role='approver')
        try:
            with self.assertRaises(VerdugoError):recovery.recover_running(a,request,True)
        finally:a.close()
        row=self.engine.db.execute('SELECT document FROM plans WHERE key=?',(request['key'],)).fetchone()
        doc=json.loads(row[0]);doc['body']['emails']['primaryEmail']='changed@example.invalid'
        self.engine.db.execute('UPDATE plans SET document=? WHERE key=?',(encode(doc),request['key']))
        a=self.approver()
        try:
            with self.assertRaises(VerdugoError):recovery.recover_running(a,request,True)
        finally:a.close()
        self.assertEqual('running',self.state())

    def test_existing_uncertain_source_is_not_reset(self):
        _,request=self.interrupted()
        a=self.approver()
        try:
            with self.assertRaises(VerdugoError):recovery.recover_running(a,request,True)
        finally:a.close()
        self.assertEqual('uncertain',self.state());self.assertEqual(1,len(self.calls))
