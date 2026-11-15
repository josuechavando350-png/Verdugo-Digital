"""Content input boundaries and original-source integrity, without fake SDK success."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_content666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'rows': [[0, 10], [1, -5], [0, 20]], 'remove': [0]}


class Content666Tests(unittest.TestCase):
    def test_numeric_inputs_reject_text_queries_models_paths_and_excessive_data(self):
        sdk.validate('txtai', 'content.reconcile', CASE)
        for change in ({'rows': []}, {'rows': [[0, 1]]*33}, {'rows': [[8, 1]]},
                       {'rows': [[True, 1]]}, {'rows': [[0, 1.0]]}, {'rows': [[0, 1000001]]},
                       {'rows': [[0, 'private text']]}, {'remove': [0, 0]}, {'remove': [3]},
                       {'remove': [False]}, {'dataset': 'real'}, {'query': 'DROP TABLE sections'},
                       {'path': '/tmp/other.sqlite'}, {'model': 'remote'}, {'rows': [[0, float('nan')]]}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                sdk.validate('txtai', 'content.reconcile', CASE | change)

    def test_independent_aggregate_reference_handles_zero_negative_and_empty(self):
        self.assertEqual([{'segment': 0, 'total': 30, 'records': 2},
                          {'segment': 1, 'total': -5, 'records': 1}], sdk.reference(CASE['rows']))
        self.assertEqual([], sdk.reference(CASE['rows'], [0, 1, 2]))
        self.assertEqual([{'segment': 0, 'total': 0, 'records': 2}], sdk.reference([[0, 1], [0, -1]]))

    def test_minimal_profile_is_upstream_and_has_no_required_runtime_dependencies(self):
        record = json.loads(sdk.CONTRACT.read_text())
        entry = next(r for r in read_registry()['records'] if r['id'] == 'txtai')
        self.assertEqual(entry['commit_sha'], record['commit'])
        self.assertEqual([], record['runtime_dependencies'])
        self.assertEqual('upstream MINIMAL=1; no extras', record['profile'])
        self.assertIn('setup.py', {r['path'] for r in record['files']})
        self.assertTrue(record['license_text_read'])
        self.assertFalse(record['live_verified'])

    def test_tampered_source_is_rejected_without_importing_original_sdk(self):
        record = json.loads(sdk.CONTRACT.read_text())
        first = next(r for r in record['files'] if r['installed_path'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root/sdk.PACKAGE/first['installed_path']
            target.parent.mkdir(parents=True)
            target.write_bytes(b'altered source')
            with patch.object(sdk.runtime_profile, 'interpreter', return_value=str(root/'bin/python')):
                self.assertFalse(sdk.runtime_state('txtai')['version_matches'])
