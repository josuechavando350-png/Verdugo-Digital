import copy
import importlib.metadata
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from verdugo import local_runtime, local_extended
from verdugo.common import VerdugoError
from verdugo.__main__ import template
from verdugo.engine import Engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests_runtime'))
from extended_fixtures import CASES


class ExtendedContracts(unittest.TestCase):
    def test_seven_new_distinct_catalog_operations(self):
        self.assertEqual(7, len(local_extended.SPECS))
        self.assertEqual(19, len(local_runtime.SPECS))
        for sid, (operation, _, _) in local_extended.SPECS.items():
            with self.subTest(sid=sid):
                local_runtime.validate(sid, operation, CASES[sid])

    def test_remote_code_paths_and_secret_parameters_rejected(self):
        for sid, (operation, _, _) in local_extended.SPECS.items():
            for field in ('shell', 'url', 'path', 'model', 'token', 'callback', 'sql', 'tenant'):
                with self.subTest(service=sid, field=field), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, operation, dict(CASES[sid], **{field: 'forbidden'}))

    def test_assumptions_are_not_implicitly_accepted(self):
        for sid in ('dowhy', 'econml'):
            for value in (False, 1, 'true', None):
                p = dict(CASES[sid], assumptions_acknowledged=value)
                with self.subTest(sid=sid, value=value), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, 'effect.estimate', p)

    def test_missing_group_and_ragged_causal_data_rejected(self):
        for sid in ('dowhy', 'econml'):
            for change in ({'treatment': [0]*240}, {'outcome': [3]*240},
                           {'outcome': [0, 1]}, {'covariates': [[1, 2], [3]]}):
                with self.subTest(sid=sid, keys=list(change)), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, 'effect.estimate', dict(CASES[sid], **change))

    def test_nonfinite_metrics_and_invalid_names_rejected(self):
        for metrics in ({'test': float('nan')}, {'test': True}, {'test': float('inf')}, {'../bad': 1}, {}):
            with self.subTest(metrics=metrics), self.assertRaises(VerdugoError):
                local_runtime.validate('mlflow', 'experiment.record', {'dataset': 'demo', 'metrics': metrics})

    def test_duplicate_contexts_are_not_counted_as_extra_evidence(self):
        p = dict(CASES['ragas'], retrieved_contexts=['same', 'same'])
        with self.assertRaises(VerdugoError):
            local_runtime.validate('ragas', 'retrieval.evaluate', p)

    def test_routing_does_not_accept_ids_as_execution_commands(self):
        p = copy.deepcopy(CASES['langgraph']); p['leads'][0]['id'] = '../bad'
        with self.assertRaises(VerdugoError): local_runtime.validate('langgraph', 'leads.route', p)
        p = copy.deepcopy(CASES['langgraph']); p['leads'][0]['need_confirmed'] = 'yes'
        with self.assertRaises(VerdugoError): local_runtime.validate('langgraph', 'leads.route', p)
        p = copy.deepcopy(CASES['langgraph']); p['leads'][0]['id'] = p['leads'][1]['id']
        with self.assertRaises(VerdugoError): local_runtime.validate('langgraph', 'leads.route', p)

    def test_unsearchable_query_and_documents_are_rejected(self):
        for change in ({'query': '!!!'}, {'documents': [{'id': 'bad', 'content': '???'}]}):
            with self.assertRaises(VerdugoError):
                local_runtime.validate('llama-index', 'documents.rank', dict(CASES['llama-index'], **change))

    def test_missing_optional_libraries_fail_closed(self):
        with patch('verdugo.local_runtime.metadata.version', side_effect=importlib.metadata.PackageNotFoundError):
            for sid, (operation, _, version) in local_extended.SPECS.items():
                with self.subTest(sid=sid), self.assertRaises(VerdugoError):
                    local_runtime.preflight(sid, operation, {'version': version, 'runtime_reviewed': True})

    def test_every_new_recipe_is_disabled_in_default_configuration(self):
        config = template('nexus')
        for sid in local_extended.SPECS:
            cfg = config['tenants']['nexus']['services'][sid]
            self.assertIs(cfg['enabled'], False)
            self.assertIs(cfg['license_reviewed'], False)
            self.assertIs(cfg['runtime_reviewed'], False)

    def test_new_code_participates_in_execution_fingerprint(self):
        original = Path.read_bytes
        def changed(path):
            content = original(path)
            return content + b'\n# modified' if path.name == 'local_extended.py' else content
        before = local_runtime.implementation_digest()
        with patch.object(Path, 'read_bytes', changed):
            self.assertNotEqual(before, local_runtime.implementation_digest())

    def test_counts_do_not_claim_source_or_production_success(self):
        engine = Engine(':memory:')
        try: status = engine.status()
        finally: engine.close()
        self.assertEqual(62, status['total_adapters_implemented'])
        self.assertEqual(260, status['projects_without_any_adapter'])
        self.assertEqual(43, status['adapters_usable_under_policy'])
        self.assertEqual(0, status['live_verified'])


if __name__ == '__main__': unittest.main()
