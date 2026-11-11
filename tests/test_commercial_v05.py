"""Synthetic-only 30-day commercial ledger tests; no actual sales or providers."""
import copy
from datetime import datetime, timezone, timedelta
import json
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from test_core import Base
from verdugo import commercial, jobs
from verdugo.common import VerdugoError, encode
from verdugo.engine import Engine
from verdugo.mcp import invoke, tool_definitions
from verdugo.ingress import accept, signature


class CommercialTests(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual('succeeded', self.engine.execute(self.lead(dataset='real'), True)['state'])

    def action(self, kind='contacted', eid='ev-1', lead='lead-1', channel='outbound', **extra):
        return {'event_id': eid, 'lead_id': lead, 'kind': kind,
                'channel': channel, 'evidence_ref': 'crm:event-101'} | extra

    def record(self, **kwargs):
        return commercial.record(self.engine, self.action(**kwargs), True)

    def payment(self, pid='payment-1', dataset='real', amount=3000000):
        command = self.pay(dataset=dataset, payment_id=pid, key='pay-'+pid)
        command['params']['amount_minor'] = amount
        self.assertEqual('succeeded', self.engine.execute(command, True)['state'])

    def test_empty_report_does_not_invent_sales_or_probability(self):
        r = commercial.report(self.engine)
        self.assertEqual(0, r['reported_paid_clients'])
        self.assertEqual(6, r['gap_to_min'])
        self.assertIsNone(r['commercial_success_probability'])
        self.assertFalse(r['bank_reconciled'])
        self.assertEqual({}, r['reported_receipts_by_currency_minor'])

    def test_plan_is_read_only_and_only_operator_can_record(self):
        item = self.action()
        p = commercial.record(self.engine, item)
        self.assertEqual('planned', p['state'])
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])
        viewer = Engine(self.path, self.config, role='viewer')
        try:
            self.assertEqual('planned', commercial.record(viewer, item)['state'])
            with self.assertRaises(VerdugoError): commercial.record(viewer, item, True)
        finally: viewer.close()

    def test_record_and_replay_do_not_double_count(self):
        a = self.record()
        b = self.record()
        self.assertFalse(a['replayed'])
        self.assertTrue(b['replayed'])
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])
        self.assertEqual(1, commercial.report(self.engine)['stage_leads']['contacted'])

    def test_id_cannot_be_changed_to_different_stage(self):
        self.record()
        with self.assertRaises(VerdugoError): self.record(kind='proposal_sent')
        self.assertEqual('contacted', self.engine.db.execute('SELECT kind FROM commercial_events').fetchone()[0])

    def test_channel_cannot_be_reassigned_after_first_event(self):
        self.record(channel='partner')
        with self.assertRaises(VerdugoError): self.record(eid='ev-2', kind='meeting_booked', channel='paid')
        self.assertEqual(1, commercial.report(self.engine)['stage_leads']['contacted'])

    def test_arbitrary_channel_stage_and_extra_fields_rejected(self):
        for change in ({'kind':'payment_verified'}, {'channel':'google_ads_now'},
                       {'tenant':'other'}, {'email':'any@example.com'},
                       {'evidence_ref':'https://example.com?token=abcd'},
                       {'evidence_ref':'synthetic@example.invalid'},
                       {'event_id':'../../bad'}, {'kind':True}, {'channel':5},
                       {'evidence_ref':True}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                commercial.record(self.engine, self.action() | change, True)
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])

    def test_invalid_or_extra_followup_date_rejected(self):
        for value in ('2026-02-30', '2026-01-01T00:00Z', 'tomorrow', True):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                self.record(kind='followup_due', followup_due=value)
        with self.assertRaises(VerdugoError): self.record(followup_due='2026-11-18')
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])

    def test_payment_is_required_and_cannot_reference_other_lead(self):
        with self.assertRaises(VerdugoError): self.record(kind='won')
        with self.assertRaises(VerdugoError): self.record(kind='won', payment_id='not-found')
        self.payment()
        self.record(kind='won', payment_id='payment-1')
        self.assertEqual(1, commercial.report(self.engine)['reported_paid_clients'])
        self.assertEqual({'MXN': 3000000}, commercial.report(self.engine)['reported_receipts_by_currency_minor'])
        self.assertFalse(commercial.report(self.engine)['bank_reconciled'])

    def test_won_event_is_reported_not_bank_verified(self):
        self.payment()
        self.record(kind='won', payment_id='payment-1')
        self.assertEqual('operator-declared events plus local payment declarations; not audited bank receipts',
                         commercial.report(self.engine)['measurement_basis'])
        self.assertIsNone(commercial.report(self.engine)['commercial_success_probability'])

    def test_demo_does_not_count_as_real(self):
        self.engine.execute(self.lead(dataset='demo', lead_id='demo-1', key='demo-lead'), True)
        command = self.command('core', 'payment.record', {'payment_id': 'demo-payment', 'lead_id': 'demo-1',
          'amount_minor': 2000000, 'cost_minor': 1, 'currency': 'MXN',
          'evidence_ref': 'synthetic', 'dataset': 'demo'}, 'demo-payment-key')
        self.engine.execute(command, True)
        self.record(kind='won', eid='demo-won', lead='demo-1', channel='referral', payment_id='demo-payment')
        self.assertEqual(0, commercial.report(self.engine)['reported_paid_clients'])
        self.assertEqual(1, commercial.report(self.engine, {'dataset':'demo'})['reported_paid_clients'])

    def test_cannot_count_same_payment_twice_or_reopen_closed_lead(self):
        self.payment(); self.record(kind='won', payment_id='payment-1')
        with self.assertRaises(VerdugoError): self.record(kind='won', eid='second-win', payment_id='payment-1')
        with self.assertRaises(VerdugoError): self.record(eid='after-win')
        self.assertEqual(1, commercial.report(self.engine)['reported_paid_clients'])

    def test_loss_is_terminal_but_does_not_count_as_paid(self):
        self.record(kind='lost')
        with self.assertRaises(VerdugoError): self.record(kind='proposal_sent', eid='after-loss')
        self.assertEqual(0, commercial.report(self.engine)['reported_paid_clients'])
        self.assertEqual(1, commercial.report(self.engine)['stage_leads']['lost'])

    def test_real_and_demo_and_tenant_are_isolated(self):
        self.record()
        other = Engine(self.path, self.config, tenant='other')
        try:
            self.assertEqual(0, commercial.report(other)['tracked_leads_in_window'])
            with self.assertRaises(VerdugoError): commercial.record(other, self.action(), True)
        finally: other.close()
        self.assertEqual(1, commercial.report(self.engine)['tracked_leads_in_window'])

    def test_overdue_and_untracked_prioritized_without_sending_messages(self):
        self.engine.execute(self.lead(dataset='real', key='lead2', lead_id='lead-2'), True)
        self.engine.execute(self.lead(dataset='real', key='lead3', lead_id='lead-3'), True)
        old=(datetime.now(timezone.utc)-timedelta(days=3)).date().isoformat()
        self.record(kind='followup_due', eid='due-1', lead='lead-1', followup_due=old)
        self.record(kind='contacted', eid='stage-2', lead='lead-2')
        nxt = commercial.next_actions(self.engine)
        self.assertEqual('lead-1', nxt['items'][0]['lead_id'])
        self.assertTrue(nxt['items'][0]['overdue'])
        self.assertEqual('lead-3', nxt['items'][1]['lead_id'])
        self.assertEqual(3, nxt['active_leads'])
        self.assertEqual(2, nxt['untracked_leads'])
        self.assertEqual(0, nxt['contacts_sent'])
        self.assertFalse(nxt['external_call_made'])
        self.assertNotIn('demo@example.invalid', encode(nxt))

    def test_followup_can_be_rescheduled_with_new_event(self):
        yesterday = (datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat()
        later = (datetime.now(timezone.utc)+timedelta(days=3)).date().isoformat()
        self.record(kind='followup_due', eid='one', followup_due=yesterday)
        self.record(kind='followup_due', eid='two', followup_due=later)
        nxt = commercial.next_actions(self.engine)
        self.assertFalse(nxt['items'][0]['overdue'])
        self.assertEqual(later, nxt['items'][0]['followup_due_utc_date'])

    def test_next_excludes_closed_leads(self):
        self.payment(); self.record(kind='won', payment_id='payment-1')
        self.assertEqual(0, commercial.next_actions(self.engine)['active_leads'])

    def test_30_day_window_excludes_old_activities_and_wins(self):
        self.payment(); self.record(kind='won', payment_id='payment-1')
        self.engine.db.execute('UPDATE commercial_events SET created=?', (time.time()-86400*45,))
        self.assertEqual(0, commercial.report(self.engine)['reported_paid_clients'])
        self.assertEqual(1, commercial.report(self.engine, {'dataset':'real','window_days':60})['reported_paid_clients'])

    def test_goal_and_type_validation(self):
        for params in ({'dataset':'real','goal_min':10,'goal_target':9}, {'dataset':'real','goal_min':True},
                       {'dataset':'real','window_days':0}, {'dataset':'real','window_days':366},
                       {'dataset':'real','tenant':'other'}, {'dataset':'unknown'}, {'dataset':True}):
            with self.subTest(params=params),self.assertRaises(VerdugoError): commercial.report(self.engine, params)
        with self.assertRaises(VerdugoError): commercial.next_actions(self.engine, {'dataset':'real','limit':True})
        with self.assertRaises(VerdugoError): commercial.next_actions(self.engine, {'dataset':'real','limit':0})

    def test_audit_failure_rolls_back_record(self):
        self.engine.db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON events WHEN NEW.kind='commercial.recorded' "
                               "BEGIN SELECT RAISE(ABORT, 'synthetic'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.record()
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])

    def test_racing_identical_event_is_recorded_once(self):
        barrier=threading.Barrier(2); outcomes=[]; failures=[]
        def task():
            e=Engine(self.path,self.config)
            try:
                barrier.wait(timeout=5)
                outcomes.append(commercial.record(e,self.action(),True)['replayed'])
            except Exception as ex: failures.append(ex)
            finally: e.close()
        a=threading.Thread(target=task);b=threading.Thread(target=task)
        a.start();b.start();a.join(5);b.join(5)
        self.assertFalse(failures)
        self.assertEqual([False,True],sorted(outcomes))
        self.assertEqual(1,self.engine.db.execute('SELECT COUNT(*) FROM commercial_events').fetchone()[0])

    def test_mcp_preview_and_readout_share_same_data(self):
        tools={x['name'] for x in tool_definitions()}
        self.assertIn('verdugo_commercial_report', tools)
        self.assertIn('verdugo_commercial_next', tools)
        self.assertIn('verdugo_commercial_record', tools)
        plan=invoke(self.engine,'verdugo_commercial_record',{'event':self.action()})
        self.assertEqual('planned',plan['state'])
        self.assertEqual(0,invoke(self.engine,'verdugo_commercial_report',{})['tracked_leads_in_window'])
        invoke(self.engine,'verdugo_commercial_record',{'event':self.action(),'execute':True})
        self.assertEqual(1,invoke(self.engine,'verdugo_commercial_report',{})['tracked_leads_in_window'])
        self.assertEqual(1,invoke(self.engine,'verdugo_commercial_next',{})['active_leads'])

    def test_cli_process_report_and_preview(self):
        config = Path(self.tmp.name) / 'config.json'; config.write_text(encode(self.config))
        prefix=[sys.executable,'-m','verdugo','--config',str(config),'--state',str(self.path)]
        before=subprocess.run(prefix+['commercial-record',encode(self.action())],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,before.returncode,before.stderr)
        self.assertEqual('planned',json.loads(before.stdout)['state'])
        recorded=subprocess.run(prefix+['commercial-record',encode(self.action()),'--execute'],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,recorded.returncode,recorded.stderr)
        result=subprocess.run(prefix+['commercial-report'],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(1,json.loads(result.stdout)['tracked_leads_in_window'])

    def test_signed_intake_to_sales_stage_is_connected_by_lead_id(self):
        from unittest.mock import patch
        cfg={'enabled':True,'secret_env':'VERDUGO_TEST_SALES_KEY','handler':'lead.capture','dataset':'real'}
        self.config['tenants']['nexus']['ingress']={'website':cfg}
        key=b'key-only-for-synthetic-testing-0123456789-abcd'
        body=encode({'id':'evt-website','type':'contact.submitted','data':{
            'external_id':'web-2','first_name':'Synthetic','email':'test2@example.invalid'}}).encode()
        ts=str(int(time.time()))
        with patch.dict('os.environ', {'VERDUGO_TEST_SALES_KEY': key.decode()}):
            accepted=accept(self.engine,'website',body,ts,signature(key,'nexus','website',ts,body))
        self.assertEqual('succeeded',jobs.work(self.engine,True)['state'])
        row=self.engine.db.execute("SELECT id FROM records WHERE kind='lead' AND id!='lead-1'").fetchone()
        self.assertIsNotNone(row)
        self.record(eid='web-stage',lead=row[0],channel='organic',kind='contacted')
        self.assertEqual(1,commercial.report(self.engine)['stage_leads']['contacted'])
        self.assertEqual(2,commercial.next_actions(self.engine)['active_leads'])

    def test_multiple_channels_and_currencies_never_mix_amounts(self):
        self.engine.execute(self.lead(dataset='real', key='newlead', lead_id='lead-2'), True)
        self.payment('one',amount=100000)
        other=self.command('core','payment.record',{
          'payment_id':'two','lead_id':'lead-2','amount_minor':200000,'cost_minor':1,
          'currency':'USD','evidence_ref':'synthetic','dataset':'real'},'pay-two')
        self.engine.execute(other,True)
        self.record(kind='won',eid='win-1',lead='lead-1',channel='referral',payment_id='one')
        self.record(kind='won',eid='win-2',lead='lead-2',channel='partner',payment_id='two')
        report=commercial.report(self.engine)
        self.assertEqual(2, report['reported_paid_clients'])
        self.assertEqual({'MXN':100000,'USD':200000},report['reported_receipts_by_currency_minor'])
        self.assertEqual({'partner':1,'referral':1},report['reported_paid_by_channel'])
