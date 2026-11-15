"""Original Egg congruence, independent checks and a joined Engine/CLI/MCP flow."""
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
from verdugo import local_egg666 as sdk, local_runtime, product
from verdugo.mcp import invoke

BASE = [{'op': 0, 'children': []}, {'op': 1, 'children': []},
        {'op': 2, 'children': [0]}, {'op': 2, 'children': [1]}]
CASES = [
    {'nodes': BASE, 'equalities': [[0, 1]]},
    {'nodes': BASE, 'equalities': []},
    {'nodes': BASE, 'equalities': [[2, 3]]},
    {'nodes': BASE+[{'op': 3, 'children': [2]}, {'op': 3, 'children': [3]}], 'equalities': [[0, 1]]},
    {'nodes': BASE, 'equalities': [[0, 1], [1, 2], [2, 3]]},
    {'nodes': [{'op': 0, 'children': []}]*16, 'equalities': [[0, 0]]*16},
    {'nodes': [{'op': 7, 'children': []}], 'equalities': []},
]


def accept():
    assert sdk.runtime_state('egg')['version_matches']
    home = sdk.root(); binary = home/sdk.BINARY; receipt = home/sdk.RECEIPT
    original = binary.read_bytes()
    try:
        binary.write_bytes(b'X'+original[1:])
        assert not sdk.runtime_state('egg')['version_matches']
    finally:
        binary.write_bytes(original)
    original = receipt.read_bytes()
    try:
        wrong = json.loads(original); wrong['contract_sha256'] = '0'*64
        receipt.write_text(json.dumps(wrong))
        assert not sdk.runtime_state('egg')['version_matches']
    finally:
        receipt.write_bytes(original)
    assert sdk.runtime_state('egg')['version_matches']
    # Original executable must also fail closed independently of Python validation.
    for raw in (b'', b'17', b'1 8 0 0', b'1 0 1 0 0', b'1 0 0 0 extra', b'0'*4097):
        proc = subprocess.run([str(binary)], input=raw, capture_output=True, timeout=10)
        assert proc.returncode != 0 and not proc.stdout
    rng = random.Random(666)
    for _ in range(200):
        n = rng.randint(1,16)
        case = {'dataset': 'demo',
                'nodes': [{'op': rng.randrange(8),
                           'children': [rng.randrange(i) for _ in range(rng.randrange(3))] if i else []}
                          for i in range(n)],
                'equalities': [[rng.randrange(n), rng.randrange(n)] for _ in range(rng.randrange(17))]}
        sdk.validate('egg', 'congruence.check', case)
        raw = subprocess.check_output([str(binary)], input=sdk.wire_input(case), timeout=10)
        sdk.verify_result(case, raw)
    cfg = template('nexus')
    for sid in ('egg', 'txtai'):
        assert local_runtime.installed(sid)['version_matches'], sid
        cfg['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True,
                                                      runtime_reviewed=True, timeout_seconds=60)
    outputs, calls = [], []
    with tempfile.TemporaryDirectory(prefix='egg666-accept-') as tmp:
        state = str(Path(tmp)/'state.sqlite'); config = Path(tmp)/'config.json'
        config.write_text(json.dumps(cfg)); config.chmod(0o600)
        request = {'id': 'congruence666', 'services': [], 'dataset': 'demo', 'currency': 'MXN',
                   'analyses': [{'id': 'congruence', 'service': 'egg', 'params': dict(CASES[0], dataset='demo')},
                                {'id': 'content', 'service': 'txtai', 'depends_on': ['analysis-congruence'],
                                 'params': {'dataset': 'demo', 'rows': [[0, {'$ref': 'analysis-congruence.result.equivalence_classes'}]],
                                            'remove': []}}]}
        with closing(Engine(state, cfg, transport=lambda *a: calls.append(a))) as engine:
            for i, case in enumerate(CASES):
                result = engine.execute({'service': 'egg', 'operation': 'congruence.check',
                                         'params': dict(case, dataset='demo'), 'key': 'egg-case-'+str(i)}, True)
                assert result['state'] == 'succeeded', result
                value = result['result']['result']; outputs.append(value)
                assert value['equivalence_classes'] == len(set(sdk.reference(case)))
                assert value['finite_reference_verified'] and not value['live_verified']
            result = invoke(engine, 'verdugo_product_run', {'request': request, 'execute': True})
            assert result['state'] == 'succeeded' and result['new_analyses'] == 2, result
            analyses = {r['service']: r['analysis']['result'] for r in result['analyses']}
            assert analyses['txtai']['before_groups'] == [{'segment': 0,
                    'total': analyses['egg']['equivalence_classes'], 'records': 1}]
            dump = '\n'.join(engine.db.iterdump())
            assert 'synthetic_op_' not in dump and '"children"' not in dump and '"equalities"' not in dump
            overview = invoke(engine, 'verdugo_product_status', {})
            assert overview['integration_audit']['duplicate_identities'] == 0
            assert overview['business']['reported_paid_clients'] == 0
        with closing(Engine(state, cfg)) as engine, patch.object(local_runtime, 'execute', side_effect=AssertionError('reexecuted')):
            replay = product.observe(engine, request, True)
            assert replay['state'] == 'succeeded' and replay['reused_analyses'] == 2, replay
        request_file = Path(tmp)/'request.json'; request_file.write_text(json.dumps(request))
        cli = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config), '--state', state,
                              'product-run', '@'+str(request_file), '--execute'], cwd=ROOT,
                             capture_output=True, text=True, timeout=90)
        assert cli.returncode == 0, cli.stderr
        assert json.loads(cli.stdout)['reused_analyses'] == 2
        assert calls == []
    return {'schema': 'verdugo.egg666.acceptance.v1', 'status': 'passed', 'synthetic': True,
            'original_components': ['egg', 'txtai'], 'cases': outputs,
            'deterministic_random_reference_cases': 200, 'native_invalid_inputs_rejected': 6,
            'source_commit': json.loads(sdk.CONTRACT.read_text())['commit'],
            'contract_sha256': hashlib.sha256(sdk.CONTRACT.read_bytes()).hexdigest(),
            'runtime_binding': sdk.runtime_state('egg')['runtime_binding'],
            'product_cli_mcp_restart_verified': True, 'joined_result_reference_verified': True,
            'modified_binary_and_contract_receipt_rejected': True, 'raw_expressions_persisted': False,
            'os_network_isolated': os.getenv('VERDUGO_OS_NETWORK_ISOLATED') == '1',
            'live_verified': False, 'all_666_integrated': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(); evidence = accept(); args.out.write_text(json.dumps(evidence, indent=2)+'\n')
    print('Original Egg: seven Engine cases, 200 comparisons, joined txtai CLI/MCP/restart passed')
