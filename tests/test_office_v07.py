"""Synthetic-only regression tests for a local first-party sales desk."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import threading
import unittest
from test_core import Base
from verdugo import commercial, office
from verdugo.common import VerdugoError, encode
from verdugo.engine import Engine
from verdugo.mcp import invoke, tool_definitions


class OfficeTests(Base):
    def sample(self, **changes):
        return {'lead_id':'new-001', 'name':'Synthetic Person',
                'email':'never-real@example.invalid', 'dataset':'demo',
                'channel':'referral', 'evidence_ref':'private:source-001'} | changes

    def test_preview_is_safe_and_does_not_write(self):
        result=office.intake(self.engine,self.sample())
        self.assertEqual('planned',result['state'])
        self.assertEqual(['identified'],result['events'])
        self.assertFalse(result['external_calls_made'])
        self.assertIsNone(self.engine.record('lead','new-001'))
        self.assertFalse(self.calls)

    def test_atomic_intake_and_followup(self):
        due=(datetime.now(timezone.utc)+timedelta(days=2)).date().isoformat()
        result=office.intake(self.engine,self.sample(followup_due=due),True)
        self.assertEqual('recorded',result['state'])
        self.assertEqual(['identified','followup_due'],result['events'])
        self.assertEqual('demo',self.engine.record('lead','new-001')['dataset'])
        self.assertEqual(2,self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])
        nxt=commercial.next_actions(self.engine,{'dataset':'demo'})
        self.assertEqual('identified',nxt['items'][0]['last_stage'])
        self.assertEqual(due,nxt['items'][0]['followup_due_utc_date'])

    def test_intake_does_not_falsely_mark_contact_or_sale(self):
        office.intake(self.engine,self.sample(),True)
        report=commercial.report(self.engine,{'dataset':'demo'})
        self.assertEqual(1,report['stage_leads']['identified'])
        self.assertEqual(0,report['stage_leads']['contacted'])
        self.assertEqual(0,report['reported_paid_clients'])
        self.assertIsNone(report['commercial_success_probability'])

    def test_replay_without_duplicate_records(self):
        self.assertFalse(office.intake(self.engine,self.sample(),True)['replayed'])
        self.assertTrue(office.intake(self.engine,self.sample(),True)['replayed'])
        self.assertEqual(1,self.engine.db.execute('SELECT COUNT(*) FROM sales_intakes').fetchone()[0])
        self.assertEqual(1,self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])
        self.assertEqual(2,len(self.engine.events()))

    def test_changed_identity_channel_and_due_rejected(self):
        office.intake(self.engine,self.sample(),True)
        for change in ({'email':'other@example.invalid'},{'channel':'paid'},
                       {'dataset':'real'},{'followup_due':'2026-12-01'}):
            with self.subTest(change=change),self.assertRaises(VerdugoError):
                office.intake(self.engine,self.sample(**change),True)

    def test_bad_input_never_persists_a_lead(self):
        for change in ({'channel':'unknown'},{'email':'not-an-email'}, {'role':'admin'},
                       {'lead_id':'..'}, {'evidence_ref':'https://example.org/token'},
                       {'followup_due':'2026-02-30'}, {'dataset':False}):
            with self.subTest(change=change),self.assertRaises(VerdugoError):
                office.intake(self.engine,self.sample(**change),True)
        self.assertIsNone(self.engine.record('lead','new-001'))

    def test_atomic_rollback_after_second_milestone_failure(self):
        self.engine.db.execute("CREATE TRIGGER stop_due BEFORE INSERT ON commercial_events "
                               "WHEN NEW.kind='followup_due' BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            office.intake(self.engine,self.sample(followup_due='2026-11-17'),True)
        self.assertIsNone(self.engine.record('lead','new-001'))
        self.assertFalse(self.engine.events())
        self.assertEqual(0,self.engine.db.execute('SELECT COUNT(*) FROM sales_intakes').fetchone()[0])

    def test_existing_lead_conflict_not_overwritten(self):
        self.engine.execute(self.command('core','lead.capture',{'lead_id':'new-001',
            'name':'Other Person','email':'other@example.invalid','dataset':'demo'},'seed'),True)
        with self.assertRaises(VerdugoError):office.intake(self.engine,self.sample(),True)
        self.assertEqual('Other Person',self.engine.record('lead','new-001')['name'])

    def test_channel_conflict_with_prior_event_rejected(self):
        self.engine.execute(self.command('core','lead.capture',{'lead_id':'new-001','name':'Synthetic Person',
            'email':'never-real@example.invalid','dataset':'demo'},'seed'),True)
        commercial.record(self.engine,{'event_id':'old','lead_id':'new-001','kind':'contacted',
             'channel':'paid','evidence_ref':'private:old-001'},True)
        with self.assertRaises(VerdugoError):office.intake(self.engine,self.sample(),True)
        self.assertEqual(0,self.engine.db.execute('SELECT COUNT(*) FROM sales_intakes').fetchone()[0])

    def test_desk_aggregates_offline_operations_without_pii(self):
        office.intake(self.engine,self.sample(),True)
        result=office.desk(self.engine,{'dataset':'demo'})
        self.assertEqual('observed_local',result['state'])
        self.assertEqual(1,result['sales']['stage_leads']['identified'])
        self.assertEqual(1,result['followups']['active_leads'])
        self.assertEqual(22,result['adapters_implemented'])
        self.assertEqual(0,result['live_verified'])
        self.assertFalse(result['external_calls_made'])
        for hidden in ('never-real@example.invalid','Synthetic Person','private:source-001'):
            self.assertNotIn(hidden,encode(result))

    def test_real_and_demo_separate(self):
        office.intake(self.engine,self.sample(),True)
        office.intake(self.engine,self.sample(lead_id='real-001',dataset='real'),True)
        self.assertEqual(1,office.desk(self.engine,{'dataset':'real'})['sales']['stage_leads']['identified'])
        self.assertEqual(1,office.desk(self.engine,{'dataset':'demo'})['sales']['stage_leads']['identified'])

    def test_business_milestones_reuse_local_lead_identity(self):
        office.intake(self.engine,self.sample(),True)
        commercial.record(self.engine,{'event_id':'meeting-1','lead_id':'new-001',
            'kind':'meeting_held','channel':'referral','evidence_ref':'private:meeting-1'},True)
        x=commercial.report(self.engine,{'dataset':'demo'})
        self.assertEqual(1,x['stage_leads']['meeting_held'])
        self.assertEqual(0,x['reported_paid_clients'])

    def test_viewer_cannot_create_and_desk_is_read_only(self):
        e=Engine(self.path,self.config,role='viewer')
        try:
            self.assertEqual('planned',office.intake(e,self.sample())['state'])
            with self.assertRaises(VerdugoError):office.intake(e,self.sample(),True)
            self.assertEqual('observed_local',office.desk(e,{'dataset':'demo'})['state'])
        finally:e.close()
        self.assertIsNone(self.engine.record('lead','new-001'))

    def test_tenant_isolation(self):
        office.intake(self.engine,self.sample(),True)
        e=Engine(self.path,self.config,tenant='other')
        try:
            self.assertEqual(0,office.desk(e,{'dataset':'demo'})['sales']['stage_leads']['identified'])
            self.assertEqual('recorded',office.intake(e,self.sample(channel='partner'),True)['state'])
        finally:e.close()
        self.assertEqual('referral',commercial.next_actions(self.engine,{'dataset':'demo'})['items'][0]['channel'])

    def test_concurrent_same_lead_intake_only_once(self):
        barrier=threading.Barrier(2);replayed=[];errors=[]
        def worker():
            e=Engine(self.path,self.config)
            try:
                barrier.wait(timeout=4)
                replayed.append(office.intake(e,self.sample(),True)['replayed'])
            except Exception as exc:errors.append(exc)
            finally:e.close()
        ts=[threading.Thread(target=worker) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(8)
        self.assertFalse(errors)
        self.assertEqual([False,True],sorted(replayed))
        self.assertEqual(1,self.engine.db.execute('SELECT COUNT(*) FROM sales_intakes').fetchone()[0])

    def test_cli_preview_execute_and_desk_share_state(self):
        cfg=Path(self.tmp.name)/'config.json';cfg.write_text(encode(self.config))
        root=[sys.executable,'-m','verdugo','--config',str(cfg),'--state',str(self.path)]
        payload=encode(self.sample())
        preview=subprocess.run(root+['sales-intake',payload],capture_output=True,text=True,timeout=10)
        self.assertEqual('planned',json.loads(preview.stdout)['state'])
        actual=subprocess.run(root+['sales-intake',payload,'--execute'],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,actual.returncode,actual.stderr)
        report=subprocess.run(root+['sales-desk','{"dataset":"demo"}'],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,report.returncode,report.stderr)
        self.assertEqual(1,json.loads(report.stdout)['sales']['stage_leads']['identified'])
        self.assertNotIn('never-real@example.invalid',report.stdout)

    def test_mcp_shares_same_controls(self):
        names={x['name'] for x in tool_definitions()}
        self.assertEqual(21,len(names))
        self.assertIn('verdugo_sales_intake',names)
        self.assertIn('verdugo_sales_desk',names)
        self.assertEqual('planned',invoke(self.engine,'verdugo_sales_intake',{'request':self.sample()})['state'])
        self.assertEqual('recorded',invoke(self.engine,'verdugo_sales_intake',
                         {'request':self.sample(),'execute':True})['state'])
        self.assertEqual(1,invoke(self.engine,'verdugo_sales_desk',
                         {'params':{'dataset':'demo'}})['sales']['stage_leads']['identified'])
        with self.assertRaises(VerdugoError):invoke(self.engine,'verdugo_sales_intake',
             {'request':self.sample(),'tenant':'other'})
