"""Synthetic contract/behavior tests; never call Google or real accounts."""
from contextlib import closing
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
from test_core import Base
from verdugo import closed_loop as cycle, office, subscriptions, maintenance
from verdugo.common import VerdugoError, encode
from verdugo.engine import Engine
from verdugo.mcp import invoke, tool_definitions


class ClosedLoopTests(Base):
    def setUp(self):
        super().setUp()
        self.cfg=self.config['tenants']['nexus']['services']['google-ads']
        self.cfg['closed_loop']={'customer_id':'1234567890','conversion_action_id':'123',
            'conversion_name':'Cliente que pagó','account_timezone':'UTC','privacy_reviewed':True,'upload_access_reviewed':True}
        self.now=datetime.now(timezone.utc).replace(microsecond=0)
        self.day=(self.now-timedelta(days=1)).date().isoformat()
        self.gclid='synthetic-click-001'

    def intake(self,n=1,**changes):
        data={'lead_id':f'lead-{n}','name':'cliente-demo','email':'demo@example.invalid','dataset':'real',
              'channel':'paid','evidence_ref':f'private:lead-{n}','ref_code':cycle.ref_code(self.gclid)}|changes
        office.intake(self.engine,data,True)
        return data

    def win(self,n=1,**changes):
        data={'event_id':f'won-{n}','lead_id':f'lead-{n}','payment_id':f'payment-{n}','dataset':'real',
              'channel':'paid','evidence_ref':f'private:paid-{n}','amount_minor':12345,'cost_minor':0,
              'currency':'MXN','paid_at':self.now.isoformat()}|changes
        office.win(self.engine,data,True)
        return data

    def clicks(self,ids=None):
        ids=[self.gclid,'synthetic-unrelated'] if ids is None else ids
        def transport(req,cfg):
            self.calls.append(req)
            return {'results':[{'clickView':{'gclid':g},'segments':{'date':self.day}} for g in ids]}
        self.engine.transport=transport
        return cycle.match(self.engine,self.day,True)

    def ready(self,n=1,**changes):
        self.intake(n,**changes);self.win(n);self.clicks()

    def approval(self,key='cycle-1'):
        p=cycle.plan(self.engine,key)
        with closing(Engine(self.path,self.config,role='approver',actor='independent-reviewer')) as e:
            e.approve(key,p['fingerprint'])
        return p

    def success(self,req,cfg):
        self.calls.append(req)
        return {'results':[{k:r[k] for k in ('gclid','conversionAction','conversionDateTime')} for r in req['public']['body']['conversions']]}

    def test_reference_known_vector_and_phone_normalization(self):
        self.assertEqual('FTZE3O',cycle.ref_code('hello'))
        self.intake(phone='+1 (555) 000-0000',ads_user_data_consent=True)
        row=self.engine.db.execute('SELECT * FROM cycle_leads').fetchone()
        self.assertEqual(hashlib.sha256(b'+15550000000').hexdigest(),row['phone_hash'])
        dumped='\n'.join(self.engine.db.iterdump())
        for plain in ('+15550000000','+1 (555) 000-0000'):
            self.assertNotIn(plain,dumped)
            self.assertNotIn(plain.encode(),self.path.read_bytes())
        self.assertNotIn('phone',encode(office.desk(self.engine)))

    def test_invalid_reference_and_phone_rejected_atomically(self):
        for extra in ({'ref_code':'abcdef'},{'ref_code':'ABC018'},{'ref_code':'ABCDEF7'},{'phone':'5550000000'},
                      {'phone':'+0123'},{'phone':123},{'ads_user_data_consent':'yes'}):
            with self.subTest(extra=extra),self.assertRaises(VerdugoError):self.intake(**extra)
        self.assertIsNone(self.engine.record('lead','lead-1'))

    def test_intake_replay_matches_normalized_phone_and_rejects_changed_reference(self):
        self.intake(phone='+1 (555) 000-0000');self.intake(phone='+15550000000')
        with self.assertRaises(VerdugoError):self.intake(ref_code='ABCDEF')
        self.assertEqual(1,self.engine.db.execute('SELECT COUNT(*) FROM cycle_leads').fetchone()[0])

    def test_fixed_daily_search_auth_and_only_matches_saved(self):
        self.intake();result=self.clicks();self.assertEqual(1,result['matched'])
        req=self.calls[0];self.assertEqual('https://googleads.googleapis.com/v26/customers/1234567890/googleAds:search',req['public']['url'])
        self.assertEqual({'query':"SELECT click_view.gclid, segments.date FROM click_view WHERE segments.date = '"+self.day+"'"},req['public']['body'])
        self.assertIn('Bearer ',req['headers']['Authorization']);self.assertIn('developer-token',req['headers'])
        dump='\n'.join(self.engine.db.iterdump());self.assertNotIn('synthetic-unrelated',dump)
        self.assertEqual(1,self.engine.db.execute('SELECT COUNT(*) FROM cycle_matches').fetchone()[0])
        for bad in ("2026-01-01' OR 1=1",(self.now-timedelta(days=91)).date().isoformat(),'tomorrow'):
            with self.assertRaises(VerdugoError):cycle.match(self.engine,bad,True)

    def test_pagination_collision_is_ambiguous_and_sticky(self):
        self.intake();ref=cycle.ref_code(self.gclid);pages=iter([
            {'results':[{'clickView':{'gclid':'synthetic-a'},'segments':{'date':self.day}}],'nextPageToken':'page2'},
            {'results':[{'clickView':{'gclid':'synthetic-b'},'segments':{'date':self.day}}]}])
        self.engine.transport=lambda req,cfg:next(pages)
        with patch.object(cycle,'ref_code',return_value=ref):
            result=cycle.match(self.engine,self.day,True)
            self.assertEqual(1,result['ambiguous']);self.assertEqual(0,result['matched'])
            self.assertIsNone(self.engine.db.execute('SELECT gclid FROM cycle_matches').fetchone()[0])
            self.assertEqual(1,self.clicks(['synthetic-a'])['ambiguous'])
        self.win();self.assertEqual({'ambiguous':1},cycle.plan(self.engine)['excluded'])

    def test_incomplete_or_malformed_click_scan_never_persists(self):
        self.intake()
        for response in ({'results':[{'clickView':{'gclid':self.gclid},'segments':{'date':self.day}}],'nextPageToken':'same'},
                         {'results':[{'clickView':{'gclid':'bad?value'},'segments':{'date':self.day}}]}):
            self.engine.transport=lambda r,c:response
            with self.assertRaises(VerdugoError):cycle.match(self.engine,self.day,True)
            self.assertEqual(0,self.engine.db.execute('SELECT COUNT(*) FROM cycle_matches').fetchone()[0])

    def test_duplicate_click_rows_are_not_ambiguous(self):
        self.intake();self.assertEqual(1,self.clicks([self.gclid,self.gclid])['matched'])

    def test_upload_contract_pinned_to_sdk_and_paid_value(self):
        self.ready(phone='+15550000000',ads_user_data_consent=True);self.approval()
        self.engine.transport=self.success;result=cycle.run(self.engine,'cycle-1',True)
        self.assertEqual('succeeded',result['state'])
        req=self.calls[-1];self.assertEqual('https://googleads.googleapis.com/v26/customers/1234567890:uploadClickConversions',req['public']['url'])
        self.assertTrue(req['mutates']);self.assertTrue(req['public']['body']['partialFailure'])
        row=req['public']['body']['conversions'][0]
        self.assertEqual({'gclid','conversionAction','conversionDateTime','conversionValue','currencyCode','orderId','userIdentifiers','consent'},set(row))
        self.assertEqual('customers/1234567890/conversionActions/123',row['conversionAction'])
        self.assertEqual(123.45,row['conversionValue']);self.assertEqual('won-1',row['orderId'])
        self.assertEqual(self.now.isoformat().replace('T',' '),row['conversionDateTime'])
        self.assertEqual([{'hashedPhoneNumber':hashlib.sha256(b'+15550000000').hexdigest(),'userIdentifierSource':'FIRST_PARTY'}],row['userIdentifiers'])
        self.assertEqual({'adUserData':'GRANTED'},row['consent'])
        evidence=json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/ciclo-cerrado-contract.json').read_text())
        self.assertEqual(cycle.PIN,evidence['source_commit'])

    def test_consent_required_for_phone_upload(self):
        self.ready(phone='+15550000000');row=cycle.plan(self.engine)['rows'][0]['wire']
        self.assertNotIn('userIdentifiers',row);self.assertNotIn('consent',row)

    def test_enhanced_identifier_older_than_63_days_excluded_but_click_eligible(self):
        self.day=(self.now-timedelta(days=64)).date().isoformat()
        self.ready(phone='+15550000000',ads_user_data_consent=True)
        self.assertNotIn('userIdentifiers',cycle.plan(self.engine)['rows'][0]['wire'])

    def test_missing_payment_time_is_not_invented(self):
        self.intake();self.win(paid_at=None);self.clicks()
        self.assertEqual({'payment_time_required':1},cycle.plan(self.engine)['excluded'])
        with self.assertRaises(VerdugoError):self.win(paid_at='2035-01-01T12:00:00+00:00')

    def test_payment_time_replay_is_immutable(self):
        self.ready()
        with self.assertRaises(VerdugoError):self.win(paid_at=(self.now-timedelta(hours=1)).isoformat())

    def test_more_than_90_days_and_payment_before_click_excluded(self):
        self.ready()
        self.engine.db.execute('UPDATE cycle_matches SET day=?',((self.now-timedelta(days=91)).date().isoformat(),));self.engine.db.commit()
        self.assertEqual({'expired':1},cycle.plan(self.engine)['excluded'])
        self.engine.db.execute('UPDATE cycle_matches SET day=?',((self.now+timedelta(days=1)).date().isoformat(),));self.engine.db.commit()
        self.assertEqual({'payment_before_click_day':1},cycle.plan(self.engine)['excluded'])

    def test_prior_approval_and_exact_configuration_are_required(self):
        self.ready();cycle.plan(self.engine,'cycle-1');self.engine.transport=self.success
        count=len(self.calls);self.assertEqual('awaiting_approval',cycle.run(self.engine,'cycle-1',True)['state']);self.assertEqual(count,len(self.calls))
        self.approval();self.cfg['closed_loop']['conversion_action_id']='456'
        with self.assertRaises(VerdugoError):cycle.run(self.engine,'cycle-1',True)
        self.assertEqual(count,len(self.calls))

    def test_google_upload_access_must_be_explicit(self):
        self.ready();self.approval();self.cfg['closed_loop']['upload_access_reviewed']=False
        with self.assertRaises(VerdugoError):cycle.run(self.engine,'cycle-1',True)

    def test_event_id_idempotent_across_batches_and_replays(self):
        self.ready();self.approval();cycle.plan(self.engine,'second-batch');self.engine.transport=self.success
        cycle.run(self.engine,'cycle-1',True);count=len(self.calls)
        self.assertTrue(cycle.run(self.engine,'cycle-1',True)['replayed'])
        with self.assertRaises(VerdugoError):cycle.run(self.engine,'second-batch',True)
        self.assertEqual(count,len(self.calls));self.assertEqual([],cycle.plan(self.engine)['rows'])

    def test_partial_failure_preserves_success_and_requires_reconciliation(self):
        self.ready();self.ready(2);self.approval()
        def partial(req,cfg):
            result=self.success(req,cfg);result['results'][1]={}
            result['partialFailureError']={'code':3,'details':[{'@type':'type.googleapis.com/google.ads.googleads.v26.errors.GoogleAdsFailure','errors':[{'location':{'fieldPathElements':[{'fieldName':'conversions','index':1}]},'message':'synthetic private response'}]}]}
            return result
        self.engine.transport=partial
        result=cycle.run(self.engine,'cycle-1',True)
        self.assertEqual({'uploaded':1,'reconciliation_required':1,'provider_payload_stored':False},result['result'])
        self.assertEqual([],cycle.plan(self.engine)['rows'])
        self.assertNotIn('synthetic private response','\n'.join(self.engine.db.iterdump()))
        with closing(Engine(self.path,self.config,role='approver',actor='independent-reviewer')) as a:
            cycle.reconcile(a,'won-2','not_uploaded','private:verified-failure',True)
        self.assertEqual(0,maintenance.pending(self.engine.db)['unresolved_runs'])
        self.assertEqual('won-2',cycle.plan(self.engine)['rows'][0]['event_id'])
        self.assertEqual('reconciled',cycle.run(self.engine,'cycle-1',True)['state'])

    def test_timeout_and_invalid_responses_never_auto_retry(self):
        self.ready();self.approval()
        def timeout(r,c):raise TimeoutError('private-secret')
        self.engine.transport=timeout;self.assertEqual('uncertain',cycle.run(self.engine,'cycle-1',True)['state'])
        self.assertTrue(cycle.run(self.engine,'cycle-1',True)['replayed']);self.assertEqual([],cycle.plan(self.engine)['rows'])
        self.assertNotIn('private-secret','\n'.join(self.engine.db.iterdump()))

    def test_failed_index_zero_and_unindexed_errors_fail_closed(self):
        self.ready();rows=cycle.plan(self.engine)['rows']
        reply={'results':[{}],'partialFailureError':{'code':3,'details':[{'errors':[{'location':{'fieldPathElements':[{'fieldName':'conversions','index':0}]}}]}]}}
        self.assertEqual(['uncertain'],cycle._outcomes(reply,rows))
        for bad in ({'results':[{}]}, {'results':[{}],'partialFailureError':{'code':3,'details':[]}}, {'results':[]}):
            with self.assertRaises(VerdugoError):cycle._outcomes(bad,rows)

    def test_viewer_cannot_plan_match_export_run_or_reconcile(self):
        self.ready()
        with closing(Engine(self.path,self.config,role='viewer')) as v:
            for call in (lambda:cycle.plan(v),lambda:cycle.match(v,self.day),lambda:cycle.export(v,Path(self.tmp.name)/'x.csv'),lambda:cycle.run(v,'x',True),lambda:cycle.reconcile(v,'won-1','uploaded','private:proof',True)):
                with self.assertRaises(VerdugoError):call()
            self.assertEqual(1,cycle.report(v)['leads_with_reference'])

    def test_off_tenant_blocks_plan_export_run_and_match(self):
        self.ready();self.approval();subscriptions.register(self.engine,'cliente-demo',execute=True)
        for call in (lambda:cycle.plan(self.engine),lambda:cycle.export(self.engine,Path(self.tmp.name)/'x.csv'),lambda:cycle.run(self.engine,'cycle-1',True),lambda:cycle.match(self.engine,self.day,True)):
            with self.assertRaisesRegex(VerdugoError,'Servicio apagado'):call()

    def test_csv_official_columns_private_file_and_no_fake_upload(self):
        self.ready();path=Path(self.tmp.name)/'conversions.csv';result=cycle.export(self.engine,path)
        self.assertFalse(result['uploaded']);self.assertEqual(0o600,path.stat().st_mode&0o777)
        rows=list(csv.reader(path.read_text().splitlines()))
        self.assertEqual(['Google Click ID','Conversion Name','Conversion Time','Conversion Value','Conversion Currency'],rows[0])
        self.assertEqual([self.gclid,'Cliente que pagó',self.now.isoformat().replace('T',' '),'123.45','MXN'],rows[1])
        self.assertEqual([],cycle.plan(self.engine)['rows']);self.assertEqual(0,cycle.report(self.engine)['uploaded'])
        self.assertEqual(1,maintenance.pending(self.engine.db)['unresolved_conversions'])
        with self.assertRaises(VerdugoError):cycle.export(self.engine,path)
        with closing(Engine(self.path,self.config,role='approver',actor='independent-reviewer')) as a:
            cycle.reconcile(a,'won-1','uploaded','private:google-receipt',True)
        self.assertEqual(1,cycle.report(self.engine)['uploaded'])

    def test_export_failure_reserved_for_review(self):
        self.ready();path=Path(self.tmp.name)/'exists.csv';path.write_text('existing')
        with self.assertRaises(FileExistsError):cycle.export(self.engine,path)
        self.assertEqual('existing',path.read_text());self.assertEqual([],cycle.plan(self.engine)['rows'])
        self.assertEqual('uncertain',self.engine.db.execute('SELECT state FROM cycle_uploads').fetchone()[0])

    def test_report_is_read_only_honest_and_tenant_scoped(self):
        self.ready();self.approval();self.engine.transport=self.success;cycle.run(self.engine,'cycle-1',True)
        count=len(self.calls);report=cycle.report(self.engine)
        self.assertEqual((1,1,1,1),(report['leads_with_reference'],report['matched_leads'],report['won_leads_with_reference'],report['uploaded']))
        self.assertIsNone(report['whatsapp_clicks_with_reference']);self.assertEqual({'MXN':12345},report['uploaded_value_minor_by_currency'])
        self.assertNotIn(self.gclid,encode(report));self.assertEqual(count,len(self.calls));self.assertFalse(report['bank_reconciled'])
        with closing(Engine(self.path,self.config,tenant='other')) as other:self.assertEqual(0,cycle.report(other)['uploaded'])

    def test_mcp_exposes_only_read_status_for_closed_loop(self):
        definitions=[t for t in tool_definitions() if 'closed_loop' in t['name']]
        self.assertEqual(['verdugo_closed_loop_status'],[t['name'] for t in definitions]);self.assertTrue(definitions[0]['annotations']['readOnlyHint'])
        self.assertEqual(0,invoke(self.engine,'verdugo_closed_loop_status',{})['uploaded'])
        for args in ({'execute':True},{'params':{'tenant':'other'}},{'params':{'conversion_name':'Override'}}):
            with self.assertRaises(VerdugoError):invoke(self.engine,'verdugo_closed_loop_status',args)

    def test_cli_accepts_tenant_after_command_and_preview_no_network(self):
        self.ready();cfg=Path(self.tmp.name)/'config.json';cfg.write_text(encode(self.config))
        result=subprocess.run([sys.executable,'-m','verdugo','--config',str(cfg),'--state',str(self.path),'closed-loop-plan','--tenant','nexus'],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,result.returncode,result.stderr);self.assertEqual('won-1',json.loads(result.stdout)['rows'][0]['event_id'])

    def test_demo_never_uploaded(self):
        self.intake(dataset='demo');self.win(dataset='demo');self.clicks()
        self.assertEqual([],cycle.plan(self.engine)['rows']);self.assertEqual(0,cycle.report(self.engine)['leads_with_reference'])

    def test_cost_uses_payment_period_same_currency_and_missing_data_is_unknown(self):
        from verdugo import ads
        self.ready();self.assertIsNone(cycle.report(self.engine)['cost_per_paid_client_by_currency']['MXN'])
        raw=('Day,Campaign,Cost,Clicks,Impressions,Conversions\n'+self.now.date().isoformat()+',synthetic,250,20,100,4\n').encode()
        ads.import_bytes(self.engine,raw,'google',True,'real','MXN')
        ads.import_bytes(self.engine,raw,'meta',True,'real','USD')
        report=cycle.report(self.engine)
        self.assertEqual({'MXN':250,'USD':None},report['cost_per_paid_client_by_currency'])
        self.assertEqual({'MXN':1},report['paid_clients_with_payment_time_by_currency'])
        future=(self.now+timedelta(days=1)).date().isoformat()
        self.assertEqual(0,cycle.report(self.engine,future,future)['won_leads_with_reference'])

    def test_reconciliation_cannot_release_an_active_upload(self):
        from verdugo.guards import GuardBusy
        self.ready();self.approval()
        def busy(req,cfg):
            with closing(Engine(self.path,self.config,role='approver')) as reviewer:
                with self.assertRaises(GuardBusy):cycle.reconcile(reviewer,'won-1','not_uploaded','private:proof',True)
            return self.success(req,cfg)
        self.engine.transport=busy
        self.assertEqual('succeeded',cycle.run(self.engine,'cycle-1',True)['state'])

    def test_parallel_batches_cannot_send_one_event_twice(self):
        self.ready();self.approval('first');self.approval('second')
        def during_upload(req,cfg):
            with closing(Engine(self.path,self.config,transport=self.success)) as other:
                with self.assertRaises(VerdugoError):cycle.run(other,'second',True)
            return self.success(req,cfg)
        self.engine.transport=during_upload
        self.assertEqual('succeeded',cycle.run(self.engine,'first',True)['state'])
        self.assertEqual(1,sum(r['mutates'] for r in self.calls))

    def test_backup_blocks_pending_exports_and_restores_confirmed_deduplication(self):
        self.ready();cycle.export(self.engine,Path(self.tmp.name)/'out.csv')
        cfg=Path(self.tmp.name)/'config.json';cfg.write_text(encode(self.config));cfg.chmod(0o600)
        saved=maintenance.create_set(self.engine,cfg)
        self.assertFalse(saved['restore_allowed'])
        with self.assertRaises(VerdugoError):maintenance.restore_set(saved['saved_directory'],Path(self.tmp.name)/'blocked',execute=True)
        with closing(Engine(self.path,self.config,role='approver')) as a:
            cycle.reconcile(a,'won-1','uploaded','private:receipt',True)
        saved=maintenance.create_set(self.engine,cfg);target=Path(self.tmp.name)/'restored'
        maintenance.restore_set(saved['saved_directory'],target,execute=True)
        with closing(Engine(target/'estado.sqlite',json.loads((target/'config.json').read_text()))) as restored:
            self.assertEqual('uploaded',restored.db.execute('SELECT state FROM cycle_uploads').fetchone()[0])
            self.assertEqual(cycle.ref_code(self.gclid),restored.db.execute('SELECT ref_code FROM cycle_leads').fetchone()[0])
            with self.assertRaises(VerdugoError):cycle.plan(restored)

    def test_privacy_review_and_approval_expiry_fail_closed(self):
        self.ready();self.approval()
        self.engine.db.execute('UPDATE plans SET expires=1');self.engine.db.commit()
        self.assertEqual('awaiting_approval',cycle.run(self.engine,'cycle-1',True)['state'])
        self.cfg['closed_loop']['privacy_reviewed']=False
        with self.assertRaises(VerdugoError):cycle.plan(self.engine)

    def test_rotated_credentials_or_version_invalidate_approval_without_exposure(self):
        import os
        self.ready();self.approval()
        with patch.dict(os.environ,{self.cfg['token_env']:'rotated-synthetic-oauth'}):
            with self.assertRaises(VerdugoError):cycle.run(self.engine,'cycle-1',True)
        self.cfg['version']='changed-contract'
        with self.assertRaises(VerdugoError):cycle.run(self.engine,'cycle-1',True)
        self.assertNotIn('rotated-synthetic-oauth','\n'.join(self.engine.db.iterdump()))
