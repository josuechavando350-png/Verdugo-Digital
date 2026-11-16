"""Original Oxigraph paths, independent checks and a joined Engine/CLI/MCP flow."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo.__main__ import template
from verdugo.engine import Engine
from verdugo import local_oxigraph666 as sdk, local_runtime, product
from verdugo.mcp import invoke

CASES = [
    {'edges': [[0,1],[1,2]], 'remove': [[1,2]]},
    {'edges': [], 'remove': []},
    {'edges': [[0,1],[1,0]], 'remove': []},
    {'edges': [[0,0],[0,0]], 'remove': [[0,0],[0,0]]},
    {'edges': [[0,1],[0,1]], 'remove': [[7,7]]},
    {'edges': [[0,1],[0,2],[1,3],[2,3]], 'remove': [[0,1]]},
    {'edges': [[i,(i+j)%8] for i in range(8) for j in range(4)],
     'remove': [[i,i] for i in range(8)]},
]

def accept():
    assert sdk.runtime_state('oxigraph')['version_matches']
    home = sdk.root(); binary = home/sdk.BINARY; receipt = home/sdk.RECEIPT
    original = binary.read_bytes()
    try:
        binary.write_bytes(b'X'+original[1:])
        assert not sdk.runtime_state('oxigraph')['version_matches']
    finally:
        binary.write_bytes(original)
    original = receipt.read_bytes()
    try:
        wrong = json.loads(original); wrong['contract_sha256'] = '0'*64
        receipt.write_text(json.dumps(wrong))
        assert not sdk.runtime_state('oxigraph')['version_matches']
    finally:
        receipt.write_bytes(original)
    assert sdk.runtime_state('oxigraph')['version_matches']
    # Original executable must also fail closed independently of Python validation.
    for raw in (b'', b'33', b'1 8 0 0', b'0 9', b'0 0 extra', b'0'*4097):
        proc = subprocess.run([str(binary)], input=raw, capture_output=True, timeout=10)
        assert proc.returncode != 0 and not proc.stdout
    rng = random.Random(666)
    for _ in range(200):
        case = {'dataset': 'demo',
                'edges': [[rng.randrange(8),rng.randrange(8)] for _ in range(rng.randrange(33))],
                'remove': [[rng.randrange(8),rng.randrange(8)] for _ in range(rng.randrange(9))]}
        sdk.validate('oxigraph', 'paths.check', case)
        raw = subprocess.check_output([str(binary)], input=sdk.wire_input(case), timeout=10)
        sdk.verify_result(case, raw)
    cfg = template('nexus')
    for sid in ('egg', 'oxigraph', 'txtai'):
        assert local_runtime.installed(sid)['version_matches'], sid
        cfg['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True,
                                                      runtime_reviewed=True, timeout_seconds=60)
    outputs, calls = [], []
    with tempfile.TemporaryDirectory(prefix='oxigraph666-accept-') as tmp:
        state = str(Path(tmp)/'state.sqlite'); config = Path(tmp)/'config.json'
        config.write_text(json.dumps(cfg)); config.chmod(0o600)
        request = {'id': 'paths666', 'services': [], 'dataset': 'demo', 'currency': 'MXN',
                   'analyses': [{'id': 'congruence', 'service': 'egg', 'params': {
                                    'dataset': 'demo', 'nodes': [{'op':0,'children':[]}, {'op':1,'children':[]},
                                    {'op':2,'children':[0]}, {'op':2,'children':[1]}], 'equalities': [[0,1]]}},
                                {'id': 'paths', 'service': 'oxigraph', 'depends_on': ['analysis-congruence'],
                                 'params': {'dataset': 'demo',
                                    'edges': [[0, {'$ref': 'analysis-congruence.result.equivalence_classes'}], [2,3]],
                                    'remove': []}},
                                {'id': 'content', 'service': 'txtai', 'depends_on': ['analysis-paths'],
                                 'params': {'dataset': 'demo', 'rows': [[0, {'$ref': 'analysis-paths.result.reachable_pairs_after'}]],
                                            'remove': []}}]}
        with closing(Engine(state, cfg, transport=lambda *a: calls.append(a))) as engine:
            for i, case in enumerate(CASES):
                result = engine.execute({'service': 'oxigraph', 'operation': 'paths.check',
                                         'params': dict(case, dataset='demo'), 'key': 'oxigraph-case-'+str(i)}, True)
                assert result['state'] == 'succeeded', result
                value = result['result']['result']; outputs.append(value)
                assert value['reachable_pairs_after'] == sdk.reference(case)[3].count('1')
                assert value['finite_reference_verified'] and not value['live_verified']
            result = invoke(engine, 'verdugo_product_run', {'request': request, 'execute': True})
            assert result['state'] == 'succeeded' and result['new_analyses'] == 3, result
            analyses = {r['service']: r['analysis']['result'] for r in result['analyses']}
            assert analyses['egg']['equivalence_classes'] == 2
            assert analyses['oxigraph']['unique_edges_before'] == 2
            assert analyses['oxigraph']['reachable_pairs_after'] == 3
            assert analyses['txtai']['before_groups'] == [{'segment': 0,
                    'total': analyses['oxigraph']['reachable_pairs_after'], 'records': 1}]
            dump = '\n'.join(engine.db.iterdump())
            assert 'urn:verdugo:synthetic-' not in dump and '"edges"' not in dump
            plans = [json.loads(row['document']) for row in engine.db.execute('SELECT document FROM plans')]
            plans = [row for row in plans if row.get('service') == 'oxigraph']
            assert len(plans) == len(CASES)+1
            for plan in plans:
                assert set(plan['params']) == {'dataset', 'edge_records', 'remove_records'}
                assert len(plan['input_sha256']) == 64
            overview = invoke(engine, 'verdugo_product_status', {})
            assert overview['integration_audit']['duplicate_identities'] == 0
            assert overview['business']['reported_paid_clients'] == 0
        with closing(Engine(state, cfg)) as engine, patch.object(local_runtime, 'execute', side_effect=AssertionError('reexecuted')):
            replay = product.observe(engine, request, True)
            assert replay['state'] == 'succeeded' and replay['reused_analyses'] == 3, replay
        request_file = Path(tmp)/'request.json'; request_file.write_text(json.dumps(request))
        cli = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config), '--state', state,
                              'product-run', '@'+str(request_file), '--execute'], cwd=ROOT,
                             capture_output=True, text=True, timeout=90)
        assert cli.returncode == 0, cli.stderr
        assert json.loads(cli.stdout)['reused_analyses'] == 3
        assert calls == []
    return {'schema': 'verdugo.oxigraph666.acceptance.v1', 'status': 'passed', 'synthetic': True,
            'original_components': ['egg', 'oxigraph', 'txtai'], 'cases': outputs,
            'deterministic_random_reference_cases': 200, 'native_invalid_inputs_rejected': 6,
            'source_commit': json.loads(sdk.CONTRACT.read_text())['commit'],
            'contract_sha256': hashlib.sha256(sdk.CONTRACT.read_bytes()).hexdigest(),
            'runtime_binding': sdk.runtime_state('oxigraph')['runtime_binding'],
            'product_cli_mcp_restart_verified': True, 'joined_result_reference_verified': True,
            'modified_binary_and_contract_receipt_rejected': True, 'raw_graph_persisted': False,
            'os_network_isolated': os.getenv('VERDUGO_OS_NETWORK_ISOLATED') == '1',
            'live_verified': False, 'all_666_integrated': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(); evidence = accept(); args.out.write_text(json.dumps(evidence, indent=2)+'\n')
    print('Original Oxigraph: seven Engine cases, 200 comparisons, joined Egg/Oxigraph/txtai CLI/MCP/restart passed')
