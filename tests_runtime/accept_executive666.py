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
    services=('semantic-kernel','agno','ag2','langroid','griptape','beeai-framework')
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
            assert set(result['steps'])=={'kernel','agno','check','simulate','measure','claims','scenarios','review'}
            r=result['steps']['check']['result']
            assert r['planned_contacts']==200 and r['planned_cost_minor']==0
            assert r['feasible_under_declared_limits'] and not r['external_execution_authorized']
            assert result['steps']['agno']['result']['budget_checked']
            for step,sid in zip(('kernel','agno','check','claims','scenarios','review'),services):
                actual=result['steps'][step]['result']
                assert actual['original_sdk']==sid and actual['llm_calls']==0
                assert not actual['autonomous_agent']
            assert all(c['verdict']=='contradicted' for c in result['steps']['claims']['result']['claims'])
            assert result['steps']['scenarios']['result']['pareto_nondominated_indices']==[0]
            assert result['steps']['review']['result']['recommendation']=='revise_strategy'
            assert e.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==8
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
    assert not calls
    return {'schema':'verdugo.executive666.acceptance.v1','services':list(services),
            'original_sdks_executed':True,'mocked_sdks':False,'dataset':'demo',
            'joint_workflow':result,'budget_rejection':data,
            'approval_gate_verified':True,'sqlite_restart_replay_verified':True,
            'cli_mcp_shared_engine_verified':True,'live_verified':False,
            'models_used':0,'external_effects':0,'batch_1_complete':False,
            'os_network_namespace':os.getenv('VERDUGO_OS_NETWORK_ISOLATED')=='1'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    evidence=accept();Path(args.out).write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('joint_workflow','budget_rejection')}))
