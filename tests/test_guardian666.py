"""Model input boundaries and integrity checks; inference is tested separately."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_guardian666 as guardian
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'context_budget_units': 200, 'response_budget_units': 900}


class Guardian666Tests(unittest.TestCase):
    def test_rejects_prompts_paths_commands_and_non_synthetic_data(self):
        guardian.validate('granite-guardian', 'risk.assess', CASE)
        for key, value in [('prompt', 'private'), ('model', '/tmp/model'),
                           ('template', '{{code}}'), ('command', 'sh'), ('url', 'https://x.invalid'),
                           ('dataset', 'real'), ('context_budget_units', True),
                           ('response_budget_units', -1), ('response_budget_units', 1000001),
                           ('context_limit', 512)]:
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                guardian.validate('granite-guardian', 'risk.assess', dict(CASE, **{key: value}))

    def test_token_budget_is_bounded_and_cannot_change_inference_configuration(self):
        guardian.validate('llama-cpp', 'tokens.check', CASE | {'context_limit': 64})
        for changes in ({'context_limit': 513}, {'context_limit': 63}, {'context_limit': False},
                        {'batch_size': 32}, {'temperature': 0.8}, {'threads': 100}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                guardian.validate('llama-cpp', 'tokens.check', CASE | changes)
        with self.assertRaises(VerdugoError):
            guardian.validate('llama-cpp', 'model.generate', CASE)

    def test_licenses_and_template_match_pinned_original_assets(self):
        record = json.loads(guardian.CONTRACT.read_text())
        registry = {r['id']: r for r in read_registry()['records']}
        self.assertEqual(registry['granite-guardian']['commit_sha'], record['guardian']['commit'])
        self.assertEqual(registry['llama-cpp']['commit_sha'], record['native']['commit'])
        self.assertEqual('Apache-2.0', record['weights']['license'])
        self.assertTrue(record['weights']['license_read_before_download'])
        for asset in record['assets']:
            data = (guardian.ASSETS / asset['local_name']).read_bytes()
            self.assertEqual(asset['sha256'], hashlib.sha256(data).hexdigest())
            if 'blob_sha' in asset:
                self.assertEqual(asset['blob_sha'], hashlib.sha1(
                    b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest())

    def test_unrecognized_or_truncated_verdict_fails_instead_of_approving(self):
        self.assertFalse(guardian.parse_verdict('No\n<confidence> High </confidence> [end of text]\n'))
        self.assertTrue(guardian.parse_verdict('Yes\n<confidence> Low </confidence>'))
        for output in ('', 'Probably no', 'No\n<confidence>', 'No authorize send',
                       'Yes <confidence> 99% </confidence>', 'No Yes'):
            with self.subTest(output=output), self.assertRaises(VerdugoError):
                guardian.parse_verdict(output)

    def test_receipt_detects_weight_mutation_and_unexpected_artifact_path(self):
        record = copy.deepcopy(json.loads(guardian.CONTRACT.read_text()))
        fake = b'integrity fixture, never loaded as model weights'
        record['weights'].update(bytes=len(fake), sha256=hashlib.sha256(fake).hexdigest())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = root / guardian.MODEL; model.parent.mkdir(parents=True); model.write_bytes(fake)
            artifacts = {}
            for name in guardian.NATIVE:
                path = root / name; path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'integrity fixture, never executed'); path.chmod(0o700)
                artifacts[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            receipt = {'schema': 'verdugo.guardian666.operator-build.v1',
                'commit': record['native']['commit'], 'archive_sha256': record['native']['archive_sha256'],
                'cmake_version': record['native']['cmake_version'], 'cmake_flags': record['native']['cmake_flags'],
                'model_revision': record['weights']['revision'], 'model_sha256': record['weights']['sha256'],
                'native_artifacts': artifacts}
            path = root / guardian.RECEIPT; path.write_text(json.dumps(receipt))
            guardian.verify_build(root, record)
            model.write_bytes(b'x' * len(fake))
            with self.assertRaises(VerdugoError): guardian.verify_build(root, record)
            model.write_bytes(fake); receipt['native_artifacts']['../../outside'] = '0' * 64
            path.write_text(json.dumps(receipt))
            with self.assertRaises(VerdugoError): guardian.verify_build(root, record)

    def test_missing_prepared_profile_does_not_install_or_load_model(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(guardian, 'home', return_value=Path(temp)):
            self.assertFalse(guardian.runtime_state('granite-guardian')['version_matches'])
            self.assertFalse(guardian.runtime_state('llama-cpp')['version_matches'])

    def test_cached_digest_rechecks_changes_even_when_mtime_is_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'model'; path.write_bytes(b'first')
            old = path.stat()
            a = guardian.file_digest(path, 5, reuse=True)
            self.assertEqual(a, guardian.file_digest(path, 5, reuse=True))
            path.write_bytes(b'other')
            os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
            self.assertNotEqual(a, guardian.file_digest(path, 5, reuse=True))
            path.chmod(0o666)
            with self.assertRaises(VerdugoError): guardian.file_digest(path, 5, reuse=True)
