"""Original txtai runtime, independent aggregates, product entry and replay."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo.__main__ import template
from verdugo.engine import Engine
from verdugo import local_content666 as sdk, local_runtime, product
from verdugo import runtime_profile
from verdugo.mcp import invoke


def accept():
    assert sdk.runtime_state('txtai')['version_matches']
    site = Path(runtime_profile.interpreter('txtai')).parent.parent/sdk.PACKAGE
    added_distribution = site/'unexpected_dependency-0.0.dist-info'
    added_module = site/'txtai'/'unexpected_module.py'
    assert not added_distribution.exists() and not added_module.exists()
    try:
        added_distribution.mkdir()
        assert not sdk.runtime_state('txtai')['version_matches']
    finally:
        added_distribution.rmdir()
    try:
        added_module.write_text('raise RuntimeError("must never be imported")\n')
        assert not sdk.runtime_state('txtai')['version_matches']
    finally:
        added_module.unlink()
    assert sdk.runtime_state('txtai')['version_matches']
    cfg = template('nexus')
    cfg['tenants']['nexus']['services']['txtai'].update(
        enabled=True, license_reviewed=True, runtime_reviewed=True, timeout_seconds=30)
    cases = [
        {'dataset': 'demo', 'rows': [[0,10],[1,-5],[0,20]], 'remove': [0]},
        {'dataset': 'demo', 'rows': [[0,0]], 'remove': []},
        {'dataset': 'demo', 'rows': [[0,1],[0,-1]], 'remove': [0,1]},
        {'dataset': 'demo', 'rows': [[i%8,1000000 if i%2 else -1000000] for i in range(32)], 'remove': [0,31]},
    ]
    outputs = []
    with tempfile.TemporaryDirectory(prefix='content666-accept-') as tmp:
        state = str(Path(tmp)/'state.sqlite')
        config = Path(tmp)/'config.json'
        config.write_text(json.dumps(cfg)); config.chmod(0o600)
        request = {'id':'content666', 'services':[], 'dataset':'demo', 'currency':'MXN',
                   'analyses':[{'id':'content', 'service':'txtai', 'params':cases[0]}]}
        calls = []
        with closing(Engine(state, cfg, transport=lambda *a:calls.append(a))) as engine:
            for i, case in enumerate(cases):
                result = engine.execute({'service':'txtai', 'operation':'content.reconcile',
                                         'params':case, 'key':'content-case-'+str(i)}, True)
                assert result['state']=='succeeded', result
                value = result['result']['result']; outputs.append(value)
                assert value['before_groups']==sdk.reference(case['rows'])
                assert value['after_groups']==sdk.reference(case['rows'],case['remove'])
                assert value['remaining_count']==len(case['rows'])-len(case['remove'])
                assert value['independent_aggregates_verified'] and value['repeated_deletion_verified']
            result = product.observe(engine, request, True)
            assert result['state']=='succeeded' and result['new_analyses']==1, result
            dump = '\n'.join(engine.db.iterdump())
            assert 'fixed_synthetic_content' not in dump and 'fixed_content_' not in dump
            overview = invoke(engine,'verdugo_product_status',{})
            assert overview['integration_audit']['duplicate_identities']==0
            assert not overview['integration_audit']['all_666_integrated']
        with closing(Engine(state, cfg)) as engine, patch.object(local_runtime,'execute',side_effect=AssertionError('reexecuted')):
            replay = product.observe(engine,request,True)
            assert replay['state']=='succeeded' and replay['reused_analyses']==1
        request_file = Path(tmp)/'request.json';request_file.write_text(json.dumps(request))
        cli = subprocess.run([sys.executable,'-m','verdugo','--config',str(config),'--state',state,
                              'product-run','@'+str(request_file),'--execute'],cwd=ROOT,
                             capture_output=True,text=True,timeout=60)
        assert cli.returncode==0,cli.stderr
        assert json.loads(cli.stdout)['reused_analyses']==1
        assert calls==[]
    return {'schema':'verdugo.content666.acceptance.v1','status':'passed','synthetic':True,
            'original_sdk':'txtai','profile':'upstream_MINIMAL','cases':outputs,
            'source_commit':json.loads(sdk.CONTRACT.read_text())['commit'],
            'contract_sha256':hashlib.sha256(sdk.CONTRACT.read_bytes()).hexdigest(),
            'runtime_binding':sdk.runtime_state('txtai')['runtime_binding'],
            'product_cli_mcp_restart_verified':True,'raw_text_persisted':False,
            'unexpected_module_and_dependency_rejected':True,
            'os_network_isolated':os.getenv('VERDUGO_OS_NETWORK_ISOLATED')=='1',
            'live_verified':False,'all_666_integrated':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path)
    evidence=accept();parser.parse_args().out.write_text(json.dumps(evidence,indent=2)+'\n')
    print('Original minimal txtai: four cases and product CLI/MCP/restart passed')
