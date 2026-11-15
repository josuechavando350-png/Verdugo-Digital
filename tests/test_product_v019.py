"""Product orchestration, real loopback sockets, restart and isolation tests."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from verdugo.__main__ import template
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke, Session
from verdugo import product, readiness_reads, operations_reads, workflow, office
from test_operations_reads_v019 import configured, command, REPLIES, PRIVATE, TOKEN, wire


def request(**changes):
    return {'id':'unified-observation', 'services':list(operations_reads.SPECS),
            'dataset':'real', 'currency':'MXN'} | changes


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state.sqlite3'
        self.config,env=configured()
        other,other_env=configured('client2'); self.config['tenants'].update(other['tenants'])
        self.env=patch.dict(os.environ, env | other_env); self.env.start(); self.addCleanup(self.env.stop)
        self.calls=[]
        self.replies=copy.deepcopy(REPLIES)

    def transport(self, req, cfg):
        sid=req['public']['service']; self.calls.append(sid)
        return copy.deepcopy(self.replies[sid])

    def engine(self, tenant='nexus', role='operator'):
        return Engine(self.path,self.config,tenant=tenant,role=role,transport=self.transport)

    def test_overview_unifies_all_catalog_entries_and_commercial_state_without_network(self):
        with closing(self.engine()) as engine:
            r=product.overview(engine)
        self.assertEqual(322,len(r['services']))
        self.assertEqual({'conectado':241,'pendiente':3,'pieza_de_construccion':56,'excluido':22},r['connection_states'])
        self.assertEqual(68,r['bounded_observation_routes'])
        self.assertEqual(0,r['business']['reported_paid_clients'])
        self.assertFalse(r['external_calls_made']); self.assertFalse(self.calls)

    def test_read_registry_excludes_paid_cloud_raw_reads_and_license_exceptions(self):
        routes=product.read_operations()
        for sid in ('airbyte','twenty','plausible','matomo','mautic','qdrant','unknown'):
            self.assertNotIn(sid,routes)
        self.assertEqual('repositories.summary',routes['dagster'])

    def test_preview_plans_one_workflow_without_runs_or_network(self):
        with closing(self.engine()) as engine:
            r=product.observe(engine,request())
            self.assertEqual('planned',r['state']); self.assertEqual(5,len(r['ordered_steps']))
            self.assertEqual([],r['approval_batch'])
            self.assertEqual(0,engine.db.execute('SELECT count(*) FROM runs').fetchone()[0])
        self.assertFalse(self.calls)

    def test_all_safe_routes_share_one_workflow_and_persisted_steps(self):
        from test_service_reads_v015 import make_config, REPLIES as services
        from test_tanda1_reads_v017 import configured as batch_config, REPLIES as batch_replies
        from test_readiness_reads_v018 import configured as ready_config, REPLIES as readiness
        from test_metadata_providers_v012 import fixture, ROUTES as metadata
        from test_marketing_reads_v013 import reply, GHOST_KEY
        config, env = make_config()
        combined = dict(services)
        for make, replies in ((batch_config,batch_replies),(ready_config,readiness),(configured,REPLIES)):
            cfg, extra_env = make()
            for sid in replies: config['tenants']['nexus']['services'][sid] = cfg['tenants']['nexus']['services'][sid]
            env.update(extra_env); combined.update(replies)
        for sid in metadata: combined[sid] = fixture(sid)
        for sid in ('payload','ghost','saleor'): combined[sid] = reply(sid)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests_runtime'))
        from platform_fixtures import configure as platform_config, REPLIES as platforms
        env.update(platform_config(config)); combined.update(platforms)
        from test_completion_reads_v021 import configure as completion_config, REPLIES as completions, TOKEN as COMPLETION_TOKEN, DEVELOPER
        from test_public_reads_v021 import configure as public_config, REPLIES as public_replies
        completion_config(config); public_config(config)
        combined.update(completions); combined.update(public_replies)
        routes = product.read_operations()
        for sid in routes:
            cfg = config['tenants']['nexus']['services'][sid]
            cfg.update(enabled=True,license_reviewed=True,version='synthetic-product-contract')
            if sid not in services and sid not in batch_replies and sid not in readiness and sid not in REPLIES:
                if cfg.get('token_env'):
                    env[cfg['token_env']] = GHOST_KEY if sid=='ghost' else 'api_synthetic' if sid=='documenso' else TOKEN
        env.update(VERDUGO_COMPLETION_TOKEN=COMPLETION_TOKEN, VERDUGO_COMPLETION_DEVELOPER=DEVELOPER)
        calls=[]
        def transport(req,cfg):
            sid=req['public']['service']; calls.append(sid)
            return copy.deepcopy(combined[sid])
        with patch.dict(os.environ,env), closing(Engine(self.path,config,transport=transport)) as engine:
            r=product.observe(engine,request(services=list(routes)),True)
            self.assertEqual('succeeded',r['state'],r)
            self.assertEqual(68,r['new_observations']); self.assertEqual(set(routes),set(calls))
            self.assertEqual(69,engine.db.execute('SELECT count(*) FROM runs').fetchone()[0])
            dump='\n'.join(engine.db.iterdump())
            for sentinel in ('private-person@example.invalid','private@example.invalid','never-retain-this@example.invalid'):
                self.assertNotIn(sentinel,dump)
        with patch.dict(os.environ,env), closing(Engine(self.path,config,transport=transport)) as engine:
            self.assertEqual(68,product.observe(engine,request(services=list(routes)),True)['reused_observations'])
        self.assertEqual(68,len(calls))

    def test_configuration_failure_blocks_every_selected_service_before_any_effect(self):
        self.config['tenants']['nexus']['services']['seaweedfs']['proxy_auth_reviewed']=False
        with closing(self.engine()) as engine:
            r=product.observe(engine,request(),True)
            self.assertEqual('blocked',r['state'])
            self.assertEqual([{'service':'seaweedfs','state':'configuration_required'}],r['blockers'])
            self.assertEqual(0,engine.db.execute('SELECT count(*) FROM plans').fetchone()[0])
        self.assertFalse(self.calls)

    def test_invalid_url_or_secret_is_not_exposed_in_blocker(self):
        cfg=self.config['tenants']['nexus']['services']['caddy']
        cfg['base_url']='https://'+TOKEN+'@private.invalid'
        with closing(self.engine()) as engine:
            r=product.observe(engine,request(),True)
        self.assertEqual('blocked',r['state']); self.assertNotIn(TOKEN,json.dumps(r)); self.assertFalse(self.calls)

    def test_success_has_separate_counts_and_traceable_persistent_observations(self):
        with closing(self.engine()) as engine:
            r=product.observe(engine,request(),True)
            self.assertEqual('succeeded',r['state']); self.assertEqual(4,r['new_observations'])
            self.assertEqual(0,r['reused_observations'])
            self.assertEqual(0,r['business_snapshot']['reported_paying_customers'])
            for row in r['services']:
                self.assertEqual('succeeded',row['state'])
                self.assertIsInstance(row['evidence']['observed_at'],float)
                self.assertEqual(64,len(row['evidence']['result_digest']))
                saved=engine.db.execute('SELECT hash FROM runs WHERE tenant=? AND key=?',
                    ('nexus',row['evidence']['key'])).fetchone()
                self.assertEqual(saved['hash'],row['evidence']['fingerprint'])
            dump='\n'.join(engine.db.iterdump())
        self.assertEqual(4,len(self.calls))
        for v in (PRIVATE,TOKEN): self.assertNotIn(v,dump); self.assertNotIn(v,json.dumps(r))

    def test_restart_replays_all_steps_preserving_original_observation_timestamps(self):
        with closing(self.engine()) as engine: first=product.observe(engine,request(),True)
        with closing(self.engine()) as engine: again=product.observe(engine,request(),True)
        self.assertEqual(4,len(self.calls)); self.assertEqual(0,again['new_observations'])
        self.assertEqual(4,again['reused_observations'])
        self.assertTrue(again['business_evidence']['replayed'])
        self.assertEqual([r['evidence']['observed_at'] for r in first['services']],
                         [r['evidence']['observed_at'] for r in again['services']])

    def test_new_id_collects_new_observations(self):
        with closing(self.engine()) as engine:
            product.observe(engine,request(),True)
            r=product.observe(engine,request(id='fresh-observation'),True)
        self.assertEqual(8,len(self.calls)); self.assertEqual(4,r['new_observations'])

    def test_failure_preserves_completed_evidence_and_does_not_run_later_steps(self):
        self.replies['caddy']={'bad':True}
        with closing(self.engine()) as engine:
            r=product.observe(engine,request(),True)
            again=product.observe(engine,request(),True)
            rows={x['service']:x for x in r['services']}
            self.assertEqual('paused',r['state']); self.assertEqual('caddy',r['failed_step'])
            self.assertEqual('succeeded',rows['apache-answer']['state'])
            self.assertEqual('failed',rows['caddy']['state'])
            self.assertEqual('not_started',rows['dagster']['state'])
            self.assertIsNone(r['business_snapshot']); self.assertEqual('paused',again['state'])
        self.assertEqual(['apache-answer','caddy'],self.calls)

    def test_fixed_failed_response_does_not_silently_retry_old_id(self):
        self.replies['apache-answer']={}
        with closing(self.engine()) as engine:
            self.assertEqual('paused',product.observe(engine,request(),True)['state'])
            self.replies=copy.deepcopy(REPLIES)
            self.assertEqual('paused',product.observe(engine,request(),True)['state'])
            self.assertEqual(1,len(self.calls))
            self.assertEqual('succeeded',product.observe(engine,request(id='retry-after-review'),True)['state'])

    def test_manifest_binds_services_dataset_and_currency_but_not_selection_order(self):
        with closing(self.engine()) as engine:
            product.observe(engine,request())
            product.observe(engine,request(services=list(reversed(request()['services']))))
            for changes in ({'dataset':'demo'},{'currency':'USD'},{'services':['caddy']}):
                with self.assertRaises(VerdugoError): product.observe(engine,request(**changes),True)
        self.assertFalse(self.calls)

    def test_changed_credentials_version_or_origin_do_not_replay_saved_results(self):
        for key,value in [('version','new'),('base_url','https://different.invalid')]:
            with closing(self.engine()) as engine:
                product.observe(engine,request(id=key),True)
                cfg=self.config['tenants']['nexus']['services']['caddy']; old=cfg[key]; cfg[key]=value
                with self.assertRaises(VerdugoError): product.observe(engine,request(id=key),True)
                cfg[key]=old
        self.assertEqual(8,len(self.calls))

    def test_same_id_in_other_tenant_cannot_reuse_observations(self):
        with closing(self.engine()) as engine: product.observe(engine,request(),True)
        with closing(self.engine('client2')) as engine: r=product.observe(engine,request(),True)
        self.assertEqual('client2',r['tenant']); self.assertEqual(4,r['new_observations'])
        self.assertEqual(8,len(self.calls))

    def test_viewer_can_inspect_preview_but_never_execute(self):
        with closing(self.engine(role='viewer')) as engine:
            self.assertEqual('observed_local',product.overview(engine)['state'])
            self.assertEqual('planned',product.observe(engine,request())['state'])
            with self.assertRaises(VerdugoError): product.observe(engine,request(),True)
        self.assertFalse(self.calls)

    def test_invalid_selections_and_arbitrary_fields_fail_before_network(self):
        with closing(self.engine()) as engine:
            for selected in ([], ['caddy','caddy'], ['twenty'],['airbyte'],['caddy']*50,[{}], 'caddy'):
                with self.assertRaises(VerdugoError): product.observe(engine,request(services=selected),True)
            for changes in ({'id':'x'*43},{'dataset':'fake'},{'currency':'usd'}, {'tenant':'client2'},
                            {'url':'https://evil.invalid'},{'query':'mutation { delete }'}):
                with self.assertRaises(VerdugoError): product.observe(engine,request(**changes),True)
            with self.assertRaises(VerdugoError): product.observe(engine,request(),1)
        self.assertFalse(self.calls)

    def test_local_demo_payments_do_not_become_real_revenue_from_provider_counts(self):
        with closing(self.engine()) as engine:
            office.intake(engine,{'lead_id':'demo-lead','name':'Synthetic','email':'demo@example.invalid',
                'dataset':'demo','channel':'organic','evidence_ref':'synthetic-only'},True)
            engine.execute({'service':'core','operation':'payment.record','key':'demo-payment','params':{
                'payment_id':'demo-payment','lead_id':'demo-lead','dataset':'demo','amount_minor':10000,
                'cost_minor':200,'currency':'MXN','evidence_ref':'synthetic-only'}},True)
            real=product.observe(engine,request(),True)
            demo=product.observe(engine,request(id='demo',dataset='demo'),True)
        self.assertEqual(0,real['business_snapshot']['reported_receipts_minor'])
        self.assertEqual(10000,demo['business_snapshot']['reported_receipts_minor'])
        self.assertIsNone(demo['business_snapshot']['reconciled_receipts_minor'])
        self.assertIsNone(demo['business_snapshot']['commercial_success_probability'])

    def test_cli_mcp_and_restart_use_the_same_six_service_workflow(self):
        replies=copy.deepcopy(REPLIES)
        replies.update({'uptime-kuma':{'ok':True,'monitors':[]},'gotenberg':{'status':'up','details':{}}})
        specs=operations_reads.SPECS | readiness_reads.SPECS
        services=self.config['tenants']['nexus']['services']
        for sid in readiness_reads.SPECS:
            services[sid].update(enabled=True,license_reviewed=True,version='synthetic',
                                 api_access_reviewed=True,proxy_auth_reviewed=True)
        env={services[s]['token_env']:TOKEN for s in readiness_reads.SPECS}
        req=request(services=list(specs))
        with patch.dict(os.environ,env), wire(self.config,replies,specs) as state:
            cfg_path=Path(self.tmp.name)/'config.json'; cfg_path.write_text(json.dumps(self.config))
            args=[sys.executable,'-m','verdugo','--config',str(cfg_path),'--state',str(self.path),
                  'product-run',json.dumps(req),'--execute']
            proc=subprocess.run(args,capture_output=True,text=True,timeout=20)
            self.assertEqual(0,proc.returncode,proc.stderr)
            first=json.loads(proc.stdout); self.assertEqual(6,first['new_observations'])
            with closing(Engine(self.path,self.config)) as engine:
                again=invoke(engine,'verdugo_product_run',{'request':req,'execute':True})
                self.assertEqual(6,again['reused_observations'])
                self.assertEqual(7,engine.db.execute('SELECT count(*) FROM runs').fetchone()[0])
            self.assertEqual(6,len(state['calls']))

    def test_concurrent_call_pauses_without_duplicate_requests_then_resumes(self):
        entered=threading.Event(); release=threading.Event(); errors=[]
        def slow(req,cfg):
            if req['public']['service']=='apache-answer':
                entered.set()
                if not release.wait(10): raise RuntimeError('test timeout')
            return self.transport(req,cfg)
        def first_run():
            try:
                with closing(Engine(self.path,self.config,transport=slow)) as engine:
                    product.observe(engine,request(),True)
            except BaseException as exc: errors.append(exc)
        thread=threading.Thread(target=first_run); thread.start()
        try:
            self.assertTrue(entered.wait(10))
            with closing(self.engine()) as engine:
                r=product.observe(engine,request(),True)
                self.assertEqual('paused',r['state']); self.assertEqual('apache-answer',r['failed_step'])
        finally:
            release.set(); thread.join(10)
        self.assertFalse(thread.is_alive()); self.assertFalse(errors,errors)
        with closing(self.engine()) as engine:
            self.assertEqual('succeeded',product.observe(engine,request(),True)['state'])
        self.assertEqual(4,len(self.calls))

    def test_mcp_blocked_result_is_error_and_status_is_read_only(self):
        with closing(Engine(':memory:')) as engine:
            session=Session(engine)
            session.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}})
            session.handle({'jsonrpc':'2.0','method':'notifications/initialized'})
            reply=session.handle({'jsonrpc':'2.0','id':2,'method':'tools/call',
                'params':{'name':'verdugo_product_run','arguments':{'request':request(),'execute':True}}})
            self.assertTrue(reply['result']['isError'])
            self.assertEqual(0,engine.db.execute('SELECT count(*) FROM runs').fetchone()[0])


if __name__=='__main__': unittest.main()
