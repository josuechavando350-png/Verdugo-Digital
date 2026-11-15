"""Original BM25S and txtai together, with counts, CLI/MCP and restart replay."""
import argparse
from contextlib import closing
import hashlib
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
from verdugo import local_bm25s666 as sdk, local_runtime, product, runtime_profile
from verdugo.mcp import invoke

CASES=[
 {'documents':[[0,0,1],[1,2],[3]],'query':[0],'k':2},
 {'documents':[[0],[0],[0]],'query':[0],'k':3},
 {'documents':[[0],[1]],'query':[15],'k':1},
 {'documents':[[0,1],[0,0],[1,1]],'query':[0,0,1],'k':2},
 {'documents':[[i%8 for i in range(16)] for _ in range(8)],'query':list(range(8)),'k':8},
 {'documents':[[7]],'query':[7],'k':1},
]


def accept():
    assert sdk.runtime_state('bm25s')['version_matches']
    site=Path(runtime_profile.interpreter('bm25s')).parent.parent/sdk.PACKAGE
    for injected in (site/'unexpected-0.0.dist-info',site/'scipy',site/'bm25s/unreviewed.py'):
        assert not injected.exists()
        try:
            if injected.suffix=='.py':injected.write_text('raise RuntimeError("must not be imported")\n')
            else:injected.mkdir()
            assert not sdk.runtime_state('bm25s')['version_matches']
        finally:
            if injected.is_dir():injected.rmdir()
            else:injected.unlink()
    assert sdk.runtime_state('bm25s')['version_matches']
    cfg=template('nexus')
    for sid in ('bm25s','txtai'):
        assert local_runtime.installed(sid)['version_matches'],sid
        cfg['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=60)
    outputs=[]; calls=[]
    with tempfile.TemporaryDirectory(prefix='bm25s666-accept-') as tmp:
        state=str(Path(tmp)/'state.sqlite');config=Path(tmp)/'config.json'
        config.write_text(json.dumps(cfg));config.chmod(0o600)
        request={'id':'lexical666','services':[],'dataset':'demo','currency':'MXN',
                 'analyses':[{'id':'retrieval','service':'bm25s','params':dict(CASES[0],dataset='demo')},
                             {'id':'content','service':'txtai','depends_on':['analysis-retrieval'],
                              'params':{'dataset':'demo','rows':[[0,{'$ref':'analysis-retrieval.result.matching_documents'}]],'remove':[]}}]}
        with closing(Engine(state,cfg,transport=lambda *a:calls.append(a))) as engine:
            for i,case in enumerate(CASES):
                result=engine.execute({'service':'bm25s','operation':'retrieval.check','params':dict(case,dataset='demo'),'key':'bm25s-case-'+str(i)},True)
                assert result['state']=='succeeded',result
                value=result['result']['result'];outputs.append(value)
                assert value['matching_documents']==sum(v>0 for v in sdk.reference(case))
                assert value['retrieved_count']==case['k']
                assert value['independent_scores_verified'] and value['independent_top_k_verified']
                assert not value['raw_text_retained'] and not value['live_verified']
            result=invoke(engine,'verdugo_product_run',{'request':request,'execute':True})
            assert result['state']=='succeeded' and result['new_analyses']==2,result
            analyses={r['service']:r['analysis']['result'] for r in result['analyses']}
            assert analyses['txtai']['before_groups']==[{'segment':0,'total':analyses['bm25s']['matching_documents'],'records':1}]
            dump='\n'.join(engine.db.iterdump())
            assert 'synthetic_term_' not in dump and 'fixed_synthetic_content' not in dump
            assert '"documents"' not in dump and '"query"' not in dump
            overview=invoke(engine,'verdugo_product_status',{})
            assert overview['integration_audit']['duplicate_identities']==0
            assert overview['business']['reported_paid_clients']==0
        with closing(Engine(state,cfg)) as engine, patch.object(local_runtime,'execute',side_effect=AssertionError('reexecuted')):
            replay=product.observe(engine,request,True)
            assert replay['state']=='succeeded' and replay['reused_analyses']==2,replay
        request_file=Path(tmp)/'request.json';request_file.write_text(json.dumps(request))
        cli=subprocess.run([sys.executable,'-m','verdugo','--config',str(config),'--state',state,
                            'product-run','@'+str(request_file),'--execute'],cwd=ROOT,capture_output=True,text=True,timeout=90)
        assert cli.returncode==0,cli.stderr
        assert json.loads(cli.stdout)['reused_analyses']==2
        assert calls==[]
    return {'schema':'verdugo.bm25s666.acceptance.v1','status':'passed','synthetic':True,
            'original_components':['bm25s','txtai'],'cases':outputs,
            'source_commit':json.loads(sdk.CONTRACT.read_text())['commit'],
            'contract_sha256':hashlib.sha256(sdk.CONTRACT.read_bytes()).hexdigest(),
            'runtime_binding':sdk.runtime_state('bm25s')['runtime_binding'],
            'product_cli_mcp_restart_verified':True,'joined_result_reference_verified':True,
            'unexpected_module_and_dependency_rejected':True,'raw_text_persisted':False,
            'os_network_isolated':os.getenv('VERDUGO_OS_NETWORK_ISOLATED')=='1',
            'live_verified':False,'all_666_integrated':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();evidence=accept();args.out.write_text(json.dumps(evidence,indent=2)+'\n')
    print('Original BM25S: six cases and joined txtai product CLI/MCP/restart passed')
