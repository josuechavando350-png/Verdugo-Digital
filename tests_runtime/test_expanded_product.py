"""One durable product run, with original libraries and explicitly synthetic HTTP."""
import copy
from contextlib import closing, nullcontext
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_analytics, local_research, local_interop, local_knowledge, local_data, local_runtime, platform_reads, product
from verdugo.__main__ import template
from verdugo.engine import Engine
from fixtures import CASES
from analytics_fixtures import assert_result as assert_analytics
from research_fixtures import assert_result as assert_research
from interop_fixtures import assert_result as assert_interop
from knowledge_fixtures import assert_result as assert_knowledge
from platform_fixtures import configure, wire, EXPECTED
from test_analytics_product import request_all as analytics_request
from test_research_product import request_all as research_request

GROUPS = {'interop': set(local_interop.SPECS), 'knowledge': set(local_knowledge.SPECS) | {'ipranges','the-great-gpt-firewall'}}
ALL = set(local_analytics.SPECS) | set(local_research.SPECS) | GROUPS['interop'] | GROUPS['knowledge']


class ExpandedProduct(unittest.TestCase):
    def execute_group(self, name, selected, http=False):
        selected_env = set(filter(None, os.getenv('VERDUGO_RUNTIME_SERVICES', '').split(',')))
        if selected_env and not selected <= selected_env: self.skipTest('Targeted group excludes this composition')
        missing = [sid for sid in selected if not local_runtime.installed(sid)['version_matches']]
        if missing:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1': self.fail('Missing original runtimes: '+','.join(missing))
            self.skipTest('Optional original runtime profiles are not installed')
        config = template('nexus')
        for sid in selected: config['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True, runtime_reviewed=True, timeout_seconds=90)
        env = configure(config) if http else {}
        tasks = {sid: {'id': sid, 'service': sid, 'params': copy.deepcopy(CASES[sid])} for sid in sorted(selected)}
        if http:
            for task in analytics_request()['analyses']+research_request()['analyses']: tasks[task['service']] = task
        if 'langgraph-supervisor' in tasks:
            source = 'markitdown' if http else 'mem0'
            field = 'markdown' if http else 'latest'
            tasks['langgraph-supervisor'].update(depends_on=['analysis-'+source])
            tasks['langgraph-supervisor']['params']['text'] = {'$ref': 'analysis-'+source+'.result.'+field}
        request = {'id': 'v020-'+name, 'dataset': 'demo', 'currency': 'MXN',
                   'services': list(platform_reads.SPECS) if http else [], 'analyses': list(tasks.values())}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, env), (wire(config) if http else nullcontext()) as remote:
            state = Path(temp)/'product.db'
            with closing(Engine(state, config)) as engine:
                self.assertEqual('planned', product.observe(engine, request)['state'])
                result = product.observe(engine, request, True)
                self.assertEqual('succeeded', result['state'], json.dumps(result))
                self.assertEqual(len(selected), result['new_analyses'])
                self.assertEqual(9 if http else 0, result['new_observations'])
                rows = {row['service']: row['analysis']['result'] for row in result['analyses']}
                changed = {'great-tables', 'markitdown', 'spacy', 'pipecat', 'langchain', 'a2a-python', 'mcp-python-sdk'} if http else set()
                for sid in selected-changed:
                    checker = (assert_analytics if sid in local_analytics.SPECS else assert_research if sid in local_research.SPECS else assert_interop if sid in local_interop.SPECS else assert_knowledge)
                    checker(self, sid, rows[sid])
                if http:
                    self.assertEqual(2, rows['great-tables']['rows']); self.assertIn('1200', rows['markitdown']['markdown'])
                    self.assertGreater(rows['spacy']['lexical_units'], 10); self.assertEqual(800, rows['pipecat']['sample_count'])
                    text = rows['docling']['markdown']
                    self.assertEqual(text, rows['langchain']['chunks'][0]['text'])
                    self.assertEqual(text, rows['a2a-python']['artifact']['parts'][0]['text'])
                    self.assertEqual(text, rows['mcp-python-sdk']['envelope']['content'][0]['text'])
                    for row in result['services']:
                        for key, value in EXPECTED[row['service']].items(): self.assertEqual(value, row['observation'][key])
                    self.assertEqual(9, len(remote['calls']))
                expected_steps = len(selected)+(9 if http else 0)+1
                self.assertEqual(expected_steps, engine.db.execute("SELECT count(*) FROM runs WHERE state='succeeded'").fetchone()[0])
                self.assertEqual(0, result['business_snapshot']['reported_paying_customers'])
            with closing(Engine(state, config, transport=lambda *_: self.fail('HTTP replay attempted'))) as engine:
                with patch('verdugo.local_runtime.execute', side_effect=AssertionError('Library replay attempted')):
                    replay = product.observe(engine, request, True)
                self.assertEqual('succeeded', replay['state']); self.assertEqual(len(selected), replay['reused_analyses'])
                self.assertEqual(9 if http else 0, replay['reused_observations'])
                for old, new in zip(result['analyses'], replay['analyses']):
                    self.assertEqual(old['analysis'], new['analysis']); self.assertEqual(old['evidence']['observed_at'], new['evidence']['observed_at'])
        evidence = os.getenv('VERDUGO_RUNTIME_EVIDENCE')
        if evidence:
            Path(evidence).with_name(name+'-product-evidence.json').write_text(json.dumps({
                'schema': 'verdugo.expanded-product.v1', 'state': 'passed', 'dataset': 'demo',
                'operations': len(selected)+(9 if http else 0), 'persisted_steps': expected_steps,
                'original_libraries': len(selected-set(local_data.SPECS)), 'bundled_original_datasets': len(selected & set(local_data.SPECS)),
                'http_contract_fixtures': 9 if http else 0, 'original_http_servers_tested': 0,
                'services': sorted(selected | (set(platform_reads.SPECS) if http else set())),
                'restart_replay': 'passed', 'implementation_sha256': local_runtime.implementation_digest(),
                'production_certified': False}, indent=2)+'\n')

    def test_twenty_sdk_and_content_operations(self):
        self.execute_group('interop', GROUPS['interop'])

    def test_eight_libraries_and_two_datasets(self):
        self.execute_group('knowledge', GROUPS['knowledge'])

    @unittest.skipUnless(os.getenv('VERDUGO_RUNTIME_ALL') == '1', 'Complete 87-operation composition is explicitly selected')
    def test_all_87_share_one_engine_and_database(self):
        self.execute_group('batch87', ALL, http=True)
