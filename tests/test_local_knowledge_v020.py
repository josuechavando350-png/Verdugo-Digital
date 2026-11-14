import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from verdugo import local_data, local_knowledge, local_runtime, workflow
from verdugo.common import VerdugoError
from verdugo.source_evidence import read_sources

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from knowledge_fixtures import CASES


class KnowledgeContracts(unittest.TestCase):
    def test_source_pins_cover_libraries_and_bundled_data(self):
        sources = {r['id']: r for r in read_sources()}
        rows = json.loads((Path(__file__).resolve().parents[1]/'sources/contracts-v020-knowledge.json').read_text())['files']
        self.assertEqual(set(CASES), {row['service'] for row in rows})
        for row in rows:
            self.assertEqual(40, len(row['blob_sha'])); self.assertEqual(sources[row['service']]['commit_sha'], row['commit'])

    def test_modified_bundled_data_fails_closed(self):
        for sid, (name, _) in local_data.FILES.items():
            self.assertTrue(local_runtime.installed(sid)['version_matches'])
            with patch.dict(local_data.FILES, {sid: (name, '0'*40)}):
                self.assertFalse(local_runtime.installed(sid)['version_matches'])
                with self.assertRaises(ValueError): local_data.source_bytes(sid)

    def test_invalid_curves_entities_domains_and_links_rejected(self):
        changes = {'pysd': {'queries': [-1]}, 'pymc-marketing': {'alpha': 1},
            'graphrag': {'edges': [{'source': 'a', 'target': 'a', 'weight': 1}]*2},
            'forecasting-tools': {'targets': [2]}, 'mem0': {'versions': []},
            'indexnow-for-python': {'xml': '<!DOCTYPE x SYSTEM "https://example.invalid"><x/>'},
            'waybackpy': {'original_url': 'https://user:secret@example.invalid/'},
            'ipranges': {'addresses': ['example.invalid']}, 'the-great-gpt-firewall': {'domains': ['a.invalid/path']}}
        for sid, diff in changes.items():
            with self.subTest(service=sid), self.assertRaises(VerdugoError):
                local_runtime.validate(sid, local_runtime.SPECS[sid][0], dict(CASES[sid], **diff))

    def test_expanded_workflow_is_still_bounded(self):
        class Preflight:
            def preflight(self, *_): pass
        steps = [{'id': 's'+str(i), 'service': 'core', 'operation': 'metrics.summary', 'params': {'text': 'x'*400}} for i in range(128)]
        self.assertEqual(128, len(workflow.order({'id': 'bounded', 'steps': steps}, Preflight())))
        with self.assertRaises(VerdugoError): workflow.order({'id': 'bounded', 'steps': steps+[dict(steps[0], id='overflow')]}, Preflight())
        with self.assertRaises(VerdugoError): workflow.order({'id': 'bounded', 'steps': [dict(steps[0], params={'text': 'x'*33000})]}, Preflight())

    def test_mcp_large_manifest_budget_does_not_relax_single_commands(self):
        from verdugo.mcp import invoke, Session
        payload = {'id': 'large', 'analyses': [{'text': 'x'*1000} for _ in range(40)]}
        with patch('verdugo.product.observe', return_value={'state': 'planned'}) as observe:
            self.assertEqual('planned', invoke(None, 'verdugo_product_run', {'request': payload})['state'])
            session = Session(None); session.initialized = session.ready = True
            result = session.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'verdugo_product_run', 'arguments': {'request': payload}}})
            self.assertFalse(result['result']['isError']); self.assertEqual(2, observe.call_count)
        with self.assertRaises(VerdugoError): invoke(None, 'verdugo_execute', {'command': payload})
        with self.assertRaises(VerdugoError): invoke(None, 'verdugo_product_run', {'request': {'text': 'x'*(1024*1024)}})


def contract_case(sid):
    def test(self):
        operation = local_runtime.SPECS[sid][0]
        local_runtime.validate(sid, operation, CASES[sid])
        for key in ('url', 'path', 'sql', 'token', 'tenant', 'shell', 'python', 'callback', 'model'):
            with self.assertRaises(VerdugoError): local_runtime.validate(sid, operation, dict(CASES[sid], **{key: 'forbidden'}))
        with self.assertRaises(VerdugoError): local_runtime.validate(sid, operation, dict(CASES[sid], dataset='production'))
    return test


for _sid in CASES:
    setattr(KnowledgeContracts, 'test_contract_'+_sid.replace('-', '_'), contract_case(_sid))
