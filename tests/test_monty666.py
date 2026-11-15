"""Input limits and source/build binding, without pretending to execute Monty."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_monty666 as monty
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry


class Monty666Tests(unittest.TestCase):
    def test_only_bounded_synthetic_numbers_no_code_or_paths(self):
        params = {'dataset':'demo', 'budget_minor':50, 'capacity_contacts':20,
                  'actions':[{'contacts':10,'cost_per_contact_minor':6}]}
        monty.validate('monty', 'budget.evaluate', params)
        for changes in ({'code':'1+1'}, {'binary_path':'/tmp/x'}, {'mount':'/tmp'},
                        {'url':'https://example.invalid'}, {'dataset':'real'},
                        {'budget_minor':True}, {'capacity_contacts':20001},
                        {'actions':[]}, {'actions':params['actions']*5},
                        {'actions':[{'contacts':1,'cost_per_contact_minor':-1}]}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                monty.validate('monty', 'budget.evaluate', params | changes)

    def test_source_contract_matches_registry_and_distinguishes_published_release(self):
        contract = json.loads(monty.CONTRACT.read_text())
        record = next(r for r in read_registry()['records'] if r['id']=='monty')
        self.assertEqual(record['commit_sha'], contract['commit'])
        self.assertNotEqual(contract['commit'], contract['published_version_is_not_pin']['release_commit'])
        self.assertEqual(8, sum(bool(f['installed_path']) for f in contract['files']))
        self.assertIn('crates/monty-python/src/limits.rs', {f['path'] for f in contract['files']})
        self.assertNotIn('exec(', monty.PROGRAM)
        self.assertLessEqual(monty.LIMITS['max_feed_duration_secs'], 1.0)

    def test_native_mutation_is_detected_before_import_or_subprocess(self):
        record = json.loads(monty.CONTRACT.read_text()) | {'files': []}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = {}
            for name in monty.NATIVE:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'checksum fixture, not a native executable'); path.chmod(0o700)
                artifacts[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            receipt = {'schema':'verdugo.monty666.operator-build.v1', 'commit':record['commit'],
                'archive_sha256':record['archive_sha256'], 'rust_version':record['rust_version'],
                'maturin_version':record['maturin_version'], 'native_artifacts':artifacts,
                'build_environment':record['build_environment']}
            path = root / monty.RECEIPT; path.parent.mkdir(parents=True)
            path.write_text(json.dumps(receipt))
            # This is a checksum-unit test; it does not certify the fixture as a build.
            monty.verify_build(root, record)
            (root / monty.NATIVE[0]).write_bytes(b'changed')
            with self.assertRaises(VerdugoError): monty.verify_build(root, record)
            receipt['native_artifacts']['../../outside'] = '0'*64
            path.write_text(json.dumps(receipt))
            with self.assertRaises(VerdugoError): monty.verify_build(root, record)

    def test_runtime_without_receipt_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(monty, 'home', return_value=Path(tmp)):
            self.assertFalse(monty.runtime_state('monty')['version_matches'])
