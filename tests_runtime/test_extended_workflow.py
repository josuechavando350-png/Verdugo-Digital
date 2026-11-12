"""Real composition of ingestion, retrieval, evaluation, routing and tracking."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_runtime, workflow
from verdugo.__main__ import template
from verdugo.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
NEEDED = ('dlt', 'llama-index', 'ragas', 'langgraph', 'mlflow')


class EvidenceWorkflow(unittest.TestCase):
    def test_ingestion_to_tracking_replays_after_restart(self):
        selected = os.getenv('VERDUGO_RUNTIME_SERVICES')
        if selected and not set(NEEDED) <= set(selected.split(',')):
            self.skipTest('Targeted run does not include the evidence pipeline')
        missing = [s for s in NEEDED if not local_runtime.installed(s)['version_matches']]
        if missing:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1':
                self.fail('Missing required extended runtime: ' + ', '.join(missing))
            self.skipTest('Optional extended dependencies absent')
        config = template('nexus')
        for sid in NEEDED:
            config['tenants']['nexus']['services'][sid].update(
                enabled=True, license_reviewed=True, runtime_reviewed=True, timeout_seconds=90)
        spec = json.loads((ROOT/'examples/local-evidence.synthetic.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'state.sqlite3'
            engine = Engine(path, config)
            try:
                self.assertEqual('planned', workflow.run(engine, spec)['state'])
                result = workflow.run(engine, spec, True)
                self.assertEqual('succeeded', result['state'], json.dumps(result))
                self.assertEqual(5, len(result['steps']))
                metrics = result['steps']['record']['result']['metrics']
                self.assertEqual(3, metrics['loaded_rows'])
                self.assertEqual(1, metrics['qualified'])
                self.assertAlmostEqual(1, metrics['context_precision'], places=6)
                self.assertTrue(result['steps']['record']['result']['readback_verified'])
                self.assertTrue(all(s['dataset']=='demo' for s in result['steps'].values()))
                self.assertEqual(5, engine.db.execute("SELECT COUNT(*) FROM runs WHERE state='succeeded'").fetchone()[0])
            finally:
                engine.close()
            restarted = Engine(path, config)
            try:
                with patch('verdugo.local_runtime.execute', side_effect=AssertionError('Unexpected rerun')):
                    self.assertEqual(result, workflow.run(restarted, spec, True))
            finally:
                restarted.close()
        target = os.getenv('VERDUGO_RUNTIME_EVIDENCE')
        if target:
            Path(target).with_name('runtime-extended-workflow-evidence.json').write_text(json.dumps({
                'schema':'verdugo.extended-composition.v1', 'state':'passed',
                'steps':list(result['steps']), 'restart_replay':'passed',
                'synthetic_only':True, 'production_certified':False},indent=2)+'\n')
