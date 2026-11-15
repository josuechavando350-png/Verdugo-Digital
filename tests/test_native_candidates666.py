"""Functional experiments do not override unresolved dependency licenses."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from verdugo import local_tensor666, local_encoding666, local_runtime, connections
from verdugo.common import VerdugoError


class QuarantinedNativeCandidatesTests(unittest.TestCase):
    def test_candidates_fail_before_any_sdk_or_profile_access(self):
        for sid,module in [('candle',local_tensor666),('tokenizers',local_encoding666)]:
            with self.subTest(service=sid), patch.object(module,'home',side_effect=AssertionError('profile access')):
                self.assertEqual({},module.SPECS)
                self.assertNotIn(sid,local_runtime.SPECS)
                self.assertEqual('pendiente',connections.summary(sid)['state'])
                with self.assertRaises(VerdugoError):module.run(sid,{})
                with self.assertRaises(VerdugoError):module._historical_unregistered_recipe(sid,{})

    def test_license_bytes_and_pending_source_records_are_preserved(self):
        records=json.loads((Path(__file__).parents[1]/'sources/contracts-executive-blockers666.json').read_text())['records']
        for sid,module in [('candle',local_tensor666),('tokenizers',local_encoding666)]:
            row=next(r for r in records if r['id']==sid)
            self.assertFalse(row['counted_as_operational'])
            self.assertTrue(row['historical_source_build_and_numeric_probe_succeeded'])
            for dep in row['inspected_dependencies']:
                self.assertEqual(dep['license_sha256'],hashlib.sha256(dep['license_text'].encode()).hexdigest())
            self.assertFalse(json.loads(module.CONTRACT.read_text())['registered_adapter'])
