"""Run the original executive SDKs together and resume through the same CLI/MCP/SQLite."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verdugo.__main__ import template
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo import local_runtime, objectives, workflow


def accept():
    services=('semantic-kernel','agno','ag2','langroid','griptape','beeai-framework','harness-sdk','unified-planning','voltagent','openmanus','servers')
    spec=json.loads((ROOT/'examples/executive666.synthetic.json').read_text())
    cfg=template('nexus')
    for sid in services:
        assert local_runtime.installed(sid)['version_matches'],sid
        cfg['tenants']['nexus']['services'][sid].update(
            enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=60)
    calls=[]
    with tempfile.TemporaryDirectory(prefix='verdugo-executive666-') as tmp:
        state=str(Path(tmp)/'state.sqlite3')
        config=Path(tmp)/'config.json';config.write_text(json.dumps(cfg));config.chmod(0o600)
        def engine(**kw):return Engine(state,cfg,transport=lambda *a:calls.append(a),**kw)
        with closing(engine()) as e:
            preview=invoke(e,'verdugo_workflow',{'workflow':spec})
            assert len(preview['approval_batch'])==1
            paused=workflow.run(e,spec,True)
            assert paused['state']=='paused' and paused['step']=='simulate',paused
            assert paused['outcome']['state']=='awaiting_approval'
        with closing(engine(role='approver',actor='synthetic-reviewer')) as e:
            e.approve_many(preview['approval_batch'])
        with closing(engine()) as e:
            result=invoke(e,'verdugo_workflow',{'workflow':spec,'execute':True})
            assert result['state']=='succeeded',result
            assert set(result['steps'])=={'kernel','agno','check','simulate','measure','claims','scenarios','review','parallel','sequence','measurement_review','stages','memory'}
            r=result['steps']['check']['result']
            assert r['planned_contacts']==200 and r['planned_cost_minor']==0
            assert r['feasible_under_declared_limits'] and not r['external_execution_authorized']
            assert result['steps']['agno']['result']['budget_checked']
            for step,sid in zip(('kernel','agno','check','claims','scenarios','review','parallel','sequence','measurement_review','stages','memory'),services):
                actual=result['steps'][step]['result']
                assert actual['original_sdk']==sid and actual['llm_calls']==0
                assert not actual['autonomous_agent']
            assert all(c['verdict']=='contradicted' for c in result['steps']['claims']['result']['claims'])
            assert result['steps']['scenarios']['result']['pareto_nondominated_indices']==[0]
            assert result['steps']['review']['result']['recommendation']=='revise_strategy'
            assert result['steps']['parallel']['result']['recommendation']=='request_operator_review'
            assert result['steps']['sequence']['result']['sequence_valid']
            assert result['steps']['measurement_review']['result']['review_recommendation']=='review_shortfall'
            assert result['steps']['stages']['result']['status_counts']['blocked']==1
            assert result['steps']['stages']['result']['first_incomplete_stage']=='simulate'
            assert result['steps']['stages']['result']['sdk_plan_deleted']
            assert result['steps']['memory']['result']['matching_incident_relation_count']==2
            assert result['steps']['memory']['result']['duplicate_relations_skipped']==1
            assert result['steps']['memory']['result']['temporary_server_restart_verified']
            assert result['steps']['memory']['result']['sdk_graph_deleted']
            assert 'stage_0' not in '\n'.join(e.db.iterdump())
            assert e.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==13
        with closing(engine()) as e, \
                patch.object(local_runtime,'execute',side_effect=AssertionError('SDK re-executed')), \
                patch.object(objectives,'simulate',side_effect=AssertionError('simulation re-executed')):
            replay=workflow.run(e,spec,True)
            assert replay['state']=='succeeded' and replay['steps']==result['steps']
        proc=subprocess.run([sys.executable,'-m','verdugo','--config',str(config),'--state',state,
                             'workflow','@'+str(ROOT/'examples/executive666.synthetic.json'),'--execute'],
                            cwd=ROOT,capture_output=True,text=True,timeout=60)
        assert proc.returncode==0,proc.stderr
        assert json.loads(proc.stdout)['state']=='succeeded'
        with closing(engine()) as e:
            rejected=e.execute({'service':'ag2','operation':'actions.check','key':'over-budget',
                'params':{'dataset':'demo','currency':'MXN','budget_minor':50,
                          'actions':[{'channel':'referral','contacts':10,'cost_per_contact_minor':6}]}},True)
            assert rejected['state']=='succeeded',rejected
            data=rejected['result']['result']
            assert data['planned_cost_minor']==60 and not data['within_budget']
            assert not data['feasible_under_declared_limits'] and not data['external_execution_authorized']
            for key,changes,wanted in [('limits',{'budget_ok':False},'revise_limits'),
                                      ('capacity',{'capacity_ok':False},'revise_limits'),
                                      ('ready',{'observed_clients':20},'request_operator_review')]:
                params={'dataset':'demo','budget_ok':True,'capacity_ok':True,'observed_clients':17,'target_clients':20}|changes
                branch=e.execute({'service':'beeai-framework','operation':'review.route','key':'branch-'+key,'params':params},True)
                assert branch['state']=='succeeded',branch
                b=branch['result']['result']
                assert b['recommendation']==wanted and b['operator_approval_required']
                assert not b['external_execution_authorized']
            from planning666_fixtures import CASES
            negative_process_cases = []
            for key, changes, reason, failed in [
                ('skip-review', {'sequence':['plan','limits','simulate','measure']}, 'inapplicable_action', 'simulate'),
                ('repeat-plan', {'sequence':['plan','plan']}, 'inapplicable_action', 'plan'),
                ('empty', {'sequence':[]}, 'unsatisfied_goals', None),
                ('limits-false', {'limits_satisfied':False}, 'inapplicable_action', 'limits'),
                ('review-unavailable', {'hypothetical_review_available':False}, 'inapplicable_action', 'operator_review')]:
                check=e.execute({'service':'unified-planning','operation':'sequence.validate','key':'formal-'+key,
                                 'params':dict(CASES['unified-planning'],**changes)},True)
                assert check['state']=='succeeded',check
                checked=check['result']['result']
                assert not checked['sequence_valid'] and checked['reason']==reason
                assert checked['first_inapplicable_stage']==failed
                assert checked['approvals_granted']==0 and not checked['operator_approval_verified']
                negative_process_cases.append({'case':key,'reason':reason,'failed_stage':failed})
            for key,capacity,budget,wanted in [('over-budget',20,50,'revise_limits'),
                                             ('over-capacity',5,100,'revise_limits'),
                                             ('within-limits',20,100,'request_operator_review')]:
                check=e.execute({'service':'harness-sdk','operation':'limits.parallel','key':'graph-'+key,
                                 'params':dict(CASES['harness-sdk'],capacity_contacts=capacity,budget_minor=budget)},True)
                assert check['state']=='succeeded',check
                checked=check['result']['result']
                assert checked['recommendation']==wanted and checked['approvals_granted']==0
            check=e.execute({'service':'voltagent','operation':'measurement.review','key':'review-target-met',
                             'params':dict(CASES['voltagent'],observed_clients=20)},True)
            assert check['state']=='succeeded',check
            assert check['result']['result']['review_recommendation']=='review_before_execution'
            assert not check['result']['result']['external_execution_authorized']
            for key, statuses, complete, disorder in [
                ('complete',['completed']*5,True,False),
                ('out-of-order',['not_started','completed','not_started','blocked','not_started'],False,True)]:
                check=e.execute({'service':'openmanus','operation':'stages.track','key':'stages-'+key,
                                 'params':{'dataset':'demo','statuses':statuses}},True)
                assert check['state']=='succeeded',check
                tracked=check['result']['result']
                assert tracked['synthetic_plan_complete']==complete
                assert tracked['reported_out_of_order_completion']==disorder
                assert not tracked['operator_approval_verified'] and tracked['approvals_granted']==0
                assert tracked['original_source_files_verified']==82 and tracked['sdk_plan_deleted']
            check=e.execute({'service':'servers','operation':'graph.audit','key':'memory-no-matches',
                             'params':{'dataset':'demo','statuses':['completed'],'edges':[],'query':'blocked'}},True)
            assert check['state']=='succeeded',check
            graph=check['result']['result']
            assert graph['entity_count']==1 and graph['matching_entity_count']==0
            assert graph['unique_relation_count']==0 and graph['matching_incident_relation_count']==0
            assert graph['sdk_graph_deleted'] and not graph['durable_agent_memory']
    assert not calls
    return {'schema':'verdugo.executive666.acceptance.v1','services':list(services),
            'original_sdks_executed':True,'mocked_sdks':False,'dataset':'demo',
            'joint_workflow':result,'budget_rejection':data,'negative_process_cases':negative_process_cases,
            'approval_gate_verified':True,'sqlite_restart_replay_verified':True,
            'cli_mcp_shared_engine_verified':True,'live_verified':False,
            'models_used':0,'external_effects':0,'batch_1_complete':False,
            'os_network_namespace':os.getenv('VERDUGO_OS_NETWORK_ISOLATED')=='1'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    evidence=accept();Path(args.out).write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('joint_workflow','budget_rejection')}))
