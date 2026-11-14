"""Cross-profile product composition; libraries keep sharing Engine and SQLite."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_research, local_runtime, product
from verdugo.__main__ import template
from verdugo.engine import Engine
from research_fixtures import CASES, assert_result


def request_all():
    tasks = [{'id': sid, 'service': sid, 'params': copy.deepcopy(CASES[sid])} for sid in local_research.SPECS]
    by_id = {t['id']: t for t in tasks}
    by_id['pipecat']['params'].update(left=[0]*800, right=[0]*800)
    by_id['whisper']['params']['samples'] = {'$ref': 'analysis-pipecat.result.samples'}
    by_id['whisper']['depends_on'] = ['analysis-pipecat']
    for sid in ('langchain', 'a2a-python', 'mcp-python-sdk'):
        by_id[sid]['params']['text'] = {'$ref': 'analysis-docling.result.markdown'}
        by_id[sid]['depends_on'] = ['analysis-docling']
    return {'id': 'research-24', 'services': [], 'dataset': 'demo', 'currency': 'MXN', 'analyses': tasks}


class ResearchProduct(unittest.TestCase):
    def test_cross_profile_operations_share_one_product_and_database(self):
        selected = os.getenv('VERDUGO_RUNTIME_SERVICES')
        if selected and not set(local_research.SPECS) <= set(selected.split(',')):
            self.skipTest('Targeted runtime selection excludes research group')
        missing = [sid for sid in local_research.SPECS if not local_runtime.installed(sid)['version_matches']]
        if missing:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1': self.fail('Missing research runtime: '+','.join(missing))
            self.skipTest('Optional research packages absent')
        config = template('nexus')
        for sid in local_research.SPECS:
            config['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True, runtime_reviewed=True, timeout_seconds=90)
        request = request_all()
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)/'state.sqlite3'
            engine = Engine(state, config)
            try:
                result = product.observe(engine, request, True)
                self.assertEqual('succeeded', result['state'], json.dumps(result))
                self.assertEqual(24, result['new_analyses'])
                rows = {r['service']: r['analysis']['result'] for r in result['analyses']}
                for sid in local_research.SPECS:
                    if sid not in ('pipecat', 'langchain', 'a2a-python', 'mcp-python-sdk'): assert_result(self, sid, rows[sid])
                self.assertEqual(800, rows['pipecat']['sample_count'])
                self.assertEqual(rows['docling']['markdown'], rows['a2a-python']['artifact']['parts'][0]['text'])
                self.assertEqual(rows['docling']['markdown'], rows['mcp-python-sdk']['envelope']['content'][0]['text'])
                self.assertEqual(rows['docling']['markdown'], rows['langchain']['chunks'][0]['text'])
                self.assertEqual(25, engine.db.execute("SELECT COUNT(*) FROM runs WHERE state='succeeded'").fetchone()[0])
            finally: engine.close()
            engine = Engine(state, config)
            try:
                with patch('verdugo.local_runtime.execute', side_effect=AssertionError('Unexpected repeat')):
                    replay = product.observe(engine, request, True)
                self.assertEqual('succeeded', replay['state']); self.assertEqual(24, replay['reused_analyses'])
                for old, new in zip(result['analyses'], replay['analyses']):
                    self.assertEqual(old['analysis'], new['analysis'])
                    self.assertEqual(old['evidence']['observed_at'], new['evidence']['observed_at'])
            finally: engine.close()
        target = os.getenv('VERDUGO_RUNTIME_EVIDENCE')
        if target:
            Path(target).with_name('research-product-evidence.json').write_text(json.dumps({
                'schema': 'verdugo.research-product.v1', 'state': 'passed', 'libraries': list(local_research.SPECS),
                'library_count': 24, 'persisted_steps': 25, 'restart_replay': 'passed',
                'data_paths': [['pipecat', 'whisper'], ['docling', 'langchain'],
                               ['docling', 'a2a-python'], ['docling', 'mcp-python-sdk']],
                'dataset': 'demo', 'production_certified': False}, indent=2)+'\n')
