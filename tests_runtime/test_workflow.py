"""End-to-end local composition, using actual libraries and persisted Engine state."""
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
REQUIRED = os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1'
NEEDED = ('trafilatura', 'presidio', 'haystack', 'duckdb', 'or-tools')


class ComposedRuntimeAcceptance(unittest.TestCase):
    def test_marketing_analysis_restarts_without_reexecuting_completed_steps(self):
        selected = os.environ.get('VERDUGO_RUNTIME_SERVICES')
        if selected and not set(NEEDED) <= set(selected.split(',')):
            self.skipTest('This targeted run does not include the full pipeline')
        missing = [s for s in NEEDED if not local_runtime.installed(s)['version_matches']]
        if missing:
            if REQUIRED:
                self.fail('Required pipeline dependencies missing: '+', '.join(missing))
            self.skipTest('Optional pipeline dependencies are not installed')
        config = template('nexus')
        for sid in NEEDED:
            config['tenants']['nexus']['services'][sid].update(
                enabled=True, license_reviewed=True, runtime_reviewed=True, timeout_seconds=90)
        spec = json.loads((ROOT/'examples/local-marketing.synthetic.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)/'state.sqlite3'
            engine = Engine(state, config)
            try:
                preview = workflow.run(engine, spec)
                self.assertEqual('planned', preview['state'])
                self.assertFalse(preview['external_calls_made'])
                result = workflow.run(engine, spec, True)
                self.assertEqual('succeeded', result['state'], json.dumps(result))
                self.assertEqual(5, len(result['steps']))
                self.assertIn('appointment', result['steps']['extract']['result']['text'].lower())
                self.assertEqual('synthetic-article', result['steps']['search']['result']['matches'][0]['id'])
                self.assertEqual(13, result['steps']['budget-selection']['result']['objective_value'])
                self.assertTrue(all(x['dataset']=='demo' for x in result['steps'].values()))
                runs = engine.db.execute("SELECT COUNT(*) FROM runs WHERE state='succeeded'").fetchone()[0]
                self.assertEqual(5, runs)
            finally:
                engine.close()
            restarted = Engine(state, config)
            try:
                with patch('verdugo.local_runtime.execute', side_effect=AssertionError('Duplicate execution')):
                    replay = workflow.run(restarted, spec, True)
                self.assertEqual(result, replay)
            finally:
                restarted.close()
        target = os.environ.get('VERDUGO_RUNTIME_EVIDENCE')
        if target:
            Path(target).with_name('runtime-workflow-evidence.json').write_text(json.dumps({
                'schema':'verdugo.composed-runtime.v1','state':'passed','steps':list(result['steps']),
                'restart_replay':'passed','synthetic_only':True,'provider_calls':0,
                'production_certified':False},indent=2)+'\n')


if __name__ == '__main__': unittest.main()
