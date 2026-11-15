"""Bounded result ordering and original-source integrity, without model mocks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_ranking666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'mode': 'score', 'values': [2, 5, 5, None], 'limit': 3}


class Ranking666Tests(unittest.TestCase):
    def test_only_bounded_numeric_results(self):
        sdk.validate('rerankers', 'results.rank', CASE)
        sdk.validate('rerankers', 'results.rank', CASE | {'mode': 'rank'})
        for change in ({'dataset': 'real'}, {'mode': 'model'}, {'values': []}, {'values': [0]*17},
                       {'values': [True]}, {'values': [float('nan')]}, {'values': [1.5]},
                       {'values': ['private']}, {'values': [1001]}, {'values': [-1001]},
                       {'limit': 0}, {'limit': 5}, {'limit': True}, {'query': 'private'},
                       {'model': 'remote'}, {'image_path': '/tmp/private'}, {'api_key': 'private'}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                sdk.validate('rerankers', 'results.rank', CASE | change)
        with self.assertRaises(VerdugoError): sdk.validate('rerankers', 'model.rank', CASE)

    def test_missing_values_and_rank_bounds(self):
        for mode in ('score', 'rank'):
            sdk.validate('rerankers', 'results.rank', CASE | {'mode': mode, 'values': [None], 'limit': 1})
        for value in (0, -1):
            with self.assertRaises(VerdugoError):
                sdk.validate('rerankers', 'results.rank', CASE | {'mode': 'rank', 'values': [value], 'limit': 1})
        sdk.validate('rerankers', 'results.rank', CASE | {'values': [-1000, 1000], 'limit': 2})

    def test_pinned_original_core_without_model_dependencies(self):
        r = json.loads(sdk.CONTRACT.read_text())
        reg = next(x for x in read_registry()['records'] if x['id'] == 'rerankers')
        self.assertEqual(reg['commit_sha'], r['commit']); self.assertEqual([], r['runtime_dependencies'])
        self.assertEqual(22, sum(bool(f['installed_path']) for f in r['files']))
        self.assertTrue(r['license_text_read']); self.assertFalse(r['live_verified'])

    def test_source_tamper_rejected_before_original_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class Distribution:
                version = '0.10.0'
                def locate_file(self, path): return root/path
            record = json.loads(sdk.CONTRACT.read_text())
            f = next(x for x in record['files'] if x['installed_path'])
            p = root/f['installed_path']; p.parent.mkdir(parents=True); p.write_text('changed source')
            with patch.object(sdk.metadata, 'distribution', return_value=Distribution()):
                with self.assertRaises(VerdugoError): sdk.verify_source()

    def test_parent_worker_binding_parity_and_changed_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = root/'bin/python'; python.parent.mkdir(); python.write_bytes(b'fixture interpreter')
            (root/'pyvenv.cfg').write_text('fixture venv configuration')
            module = root/sdk.PACKAGE/'rerankers/results.py'
            module.parent.mkdir(parents=True); module.write_bytes(b'fixture source')
            contract = root/'contract.json'
            contract.write_text(json.dumps({'files': [{'installed_path': 'rerankers/results.py',
                'sha256': hashlib.sha256(module.read_bytes()).hexdigest()}]}))
            with patch.object(sdk, 'CONTRACT', contract), \
                 patch.object(sdk.runtime_profile, 'interpreter', return_value=str(python)), \
                 patch.object(sdk.runtime_profile, 'versions', return_value={'rerankers': '0.10.0'}):
                parent = sdk.runtime_state('rerankers')
                with patch.object(sdk.runtime_profile.sys, 'executable', str(python)):
                    worker = sdk.runtime_state('rerankers')
                self.assertTrue(parent['version_matches'])
                self.assertEqual(parent['runtime_binding'], worker['runtime_binding'])
                python.write_bytes(b'changed interpreter')
                self.assertNotEqual(parent['runtime_binding'], sdk.runtime_state('rerankers')['runtime_binding'])
                module.write_bytes(b'changed source')
                self.assertFalse(sdk.runtime_state('rerankers')['version_matches'])
