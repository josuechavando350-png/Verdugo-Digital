"""All analytical libraries, composed through product-run and durable Engine state."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_analytics, local_runtime, product
from verdugo.__main__ import template
from verdugo.engine import Engine
from analytics_fixtures import CASES, assert_result


def request_all():
    tasks = [{'id': sid, 'service': sid, 'params': copy.deepcopy(CASES[sid])}
             for sid in local_analytics.SPECS]
    # A real data path: aggregate campaign rows -> render table -> extract its
    # text as Markdown -> segment the text. All stages use existing worker/DB.
    by_id = {t['id']: t for t in tasks}
    by_id['great-tables']['params']['rows'] = {'$ref': 'analysis-arrow.result.channels'}
    by_id['great-tables']['depends_on'] = ['analysis-arrow']
    by_id['markitdown']['params']['html'] = {'$ref': 'analysis-great-tables.result.html'}
    by_id['markitdown']['depends_on'] = ['analysis-great-tables']
    by_id['spacy']['params']['text'] = {'$ref': 'analysis-markitdown.result.markdown'}
    by_id['spacy']['depends_on'] = ['analysis-markitdown']
    return {'id': 'analytics-24', 'services': [], 'dataset': 'demo', 'currency': 'MXN', 'analyses': tasks}


class AnalyticsProduct(unittest.TestCase):
    def test_all_actual_libraries_share_one_restartable_product_run(self):
        selected = os.getenv('VERDUGO_RUNTIME_SERVICES')
        if selected and not set(local_analytics.SPECS) <= set(selected.split(',')):
            self.skipTest('Targeted runtime selection excludes analytical group')
        missing = [sid for sid in local_analytics.SPECS if not local_runtime.installed(sid)['version_matches']]
        if missing:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1': self.fail('Missing analytical runtime: '+','.join(missing))
            self.skipTest('Optional analytical packages absent')
        config = template('nexus')
        for sid in local_analytics.SPECS:
            config['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True, runtime_reviewed=True, timeout_seconds=90)
        request = request_all()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'shared.sqlite3'
            engine = Engine(path, config)
            try:
                self.assertEqual('planned', product.observe(engine, request)['state'])
                result = product.observe(engine, request, True)
                self.assertEqual('succeeded', result['state'], json.dumps(result))
                self.assertEqual(24, result['new_analyses'])
                self.assertEqual(0, result['new_observations'])
                rows = {r['service']: r for r in result['analyses']}
                for sid, row in rows.items():
                    self.assertEqual('demo', row['analysis']['dataset'])
                    if sid not in ('great-tables', 'markitdown', 'spacy'):
                        assert_result(self, sid, row['analysis']['result'])
                self.assertEqual(2, rows['great-tables']['analysis']['result']['rows'])
                self.assertIn('1200', rows['markitdown']['analysis']['result']['markdown'])
                self.assertGreater(rows['spacy']['analysis']['result']['lexical_units'], 10)
                self.assertEqual(25, engine.db.execute("SELECT COUNT(*) FROM runs WHERE state='succeeded'").fetchone()[0])
            finally: engine.close()
            engine = Engine(path, config)
            try:
                with patch('verdugo.local_runtime.execute', side_effect=AssertionError('Unexpected rerun')):
                    replay = product.observe(engine, request, True)
                self.assertEqual('succeeded', replay['state'])
                self.assertEqual(24, replay['reused_analyses']); self.assertEqual(0, replay['new_analyses'])
                for old, new in zip(result['analyses'], replay['analyses']):
                    self.assertEqual(old['analysis'], new['analysis'])
                    self.assertEqual(old['evidence']['observed_at'], new['evidence']['observed_at'])
            finally: engine.close()
        target = os.getenv('VERDUGO_RUNTIME_EVIDENCE')
        if target:
            Path(target).with_name('analytics-product-evidence.json').write_text(json.dumps({
                'schema': 'verdugo.analytics-product.v1', 'state': 'passed',
                'libraries': list(local_analytics.SPECS), 'library_count': 24, 'persisted_steps': 25,
                'data_path': ['arrow', 'great-tables', 'markitdown', 'spacy'],
                'restart_replay': 'passed', 'dataset': 'demo', 'production_certified': False}, indent=2)+'\n')
