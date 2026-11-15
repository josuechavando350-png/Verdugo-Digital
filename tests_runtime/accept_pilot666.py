"""Original SDK acceptance with approved synthetic simulation and SQLite replay.

Run with the isolated SDK interpreter. CI additionally removes OS networking.
This proves this bounded SDK operation, not autonomous reasoning or sales.
"""
import argparse
from contextlib import closing
import hashlib
from importlib import metadata
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
from verdugo.mcp import invoke
from verdugo import local_runtime, objectives, workflow


def accept():
    assert metadata.version('semantic-kernel') == '1.47.0'
    spec = json.loads((ROOT/'examples/kernel666.synthetic.json').read_text())
    cfg = template('nexus')
    cfg['tenants']['nexus']['services']['semantic-kernel'].update(
        enabled=True, license_reviewed=True, runtime_reviewed=True,
        version='1.47.0', timeout_seconds=60)
    calls = []
    with tempfile.TemporaryDirectory(prefix='verdugo-666-accept-') as tmp:
        state = str(Path(tmp)/'engine.sqlite3')
        config_path = Path(tmp)/'config.json'
        config_path.write_text(json.dumps(cfg))
        config_path.chmod(0o600)
        def engine(**kw):
            return Engine(state, cfg, transport=lambda *a: calls.append(a), **kw)
        with closing(engine()) as e:
            preview = invoke(e, 'verdugo_workflow', {'workflow': spec})
            assert len(preview['approval_batch']) == 1
            assert e.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0
            paused = workflow.run(e, spec, True)
            assert paused['state'] == 'paused' and paused['step'] == 'simulate', paused
            assert paused['outcome']['state'] == 'awaiting_approval'
        with closing(engine(role='approver', actor='synthetic-reviewer')) as e:
            e.approve_many(preview['approval_batch'])
        with closing(engine()) as e:
            result = invoke(e, 'verdugo_workflow', {'workflow': spec, 'execute': True})
            assert result['state'] == 'succeeded', result
            sdk = result['steps']['plan']['result']
            assert sdk['original_sdk'] == 'semantic-kernel'
            assert sdk['registered_ai_services'] == 0 and sdk['llm_calls'] == 0
            assert sdk['planned_contacts'] == 200 and sdk['dry_run']
            assert not sdk['autonomous_agent'] and not sdk['calibrated_to_real_market']
            assert result['steps']['measure']['real_clients_verified'] == 0
            rows_before = e.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
            assert rows_before == 3
        with closing(engine()) as e, \
                patch.object(local_runtime, 'execute', side_effect=AssertionError('SDK replayed')), \
                patch.object(objectives, 'simulate', side_effect=AssertionError('simulation replayed')):
            again = workflow.run(e, spec, True)
            assert again['state'] == 'succeeded'
            assert result['steps'] == again['steps']
            assert e.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == rows_before
        cli = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config_path),
                              '--state', state, 'workflow', '@'+str(ROOT/'examples/kernel666.synthetic.json'),
                              '--execute'], cwd=ROOT, capture_output=True, text=True, timeout=30)
        assert cli.returncode == 0, cli.stderr
        assert json.loads(cli.stdout)['state'] == 'succeeded'
    assert not calls
    import semantic_kernel
    package = Path(semantic_kernel.__file__).parent
    contract = json.loads((ROOT/'sources/contracts-kernel666.json').read_text())
    hashes = []
    for source in contract['source_files']:
        if not source['path'].startswith('python/semantic_kernel/'):
            continue
        path = package / source['path'].removeprefix('python/semantic_kernel/')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.append({'path': source['path'], 'installed_sha256': actual,
                       'source_sha256': source['sha256'], 'matches_source': actual == source['sha256']})
    assert len(hashes) == 5 and all(row['matches_source'] for row in hashes), hashes
    return {'scope': 'one original SDK native operation plus synthetic goal workflow',
            'service': 'semantic-kernel', 'version': metadata.version('semantic-kernel'),
            'source_commit': contract['source_commit'], 'installed_source_files': hashes,
            'original_sdk_executed': True, 'mocked_sdk': False, 'dataset': 'demo',
            'approval_gate_verified': True, 'sqlite_restart_replay_verified': True,
            'cli_mcp_shared_engine_verified': True, 'simulation': result['steps']['simulate'],
            'measurement': result['steps']['measure'], 'external_effects': 0,
            'models_used': 0, 'live_verified': False, 'batch_1_complete': False,
            'os_network_namespace': os.environ.get('VERDUGO_OS_NETWORK_ISOLATED') == '1'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    evidence = accept()
    Path(args.out).write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('simulation','measurement','installed_source_files')}))
