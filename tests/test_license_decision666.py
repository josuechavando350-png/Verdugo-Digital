"""The three owner-approved licenses only resolve the evidenced findings."""
import hashlib
import json
from pathlib import Path
import tomllib
import unittest

from verdugo import connections, license_policy
from verdugo.registry666 import read_registry

ROOT = Path(__file__).resolve().parents[1]


class LicenseDecision666Tests(unittest.TestCase):
    def test_clingo_native_review_preserves_unresolved_parser_notice(self):
        row = json.loads((ROOT/'sources/review-clingo-dependencies666.json').read_text())['records'][0]
        self.assertEqual('pending_generated_parser_license_scope', row['status'])
        self.assertEqual(9, len(row['submodules']))
        for module in row['submodules']:
            original = module['license']
            raw = original['text'].encode()
            self.assertIn(original['spdx'], license_policy.PERMISSIVE)
            self.assertEqual(original['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(original['blob_sha'],
                             hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
        self.assertEqual(2, len(row['generated_parser_notices']))
        files = {f['path']: f for f in row['files']}
        for notice in row['generated_parser_notices']:
            self.assertEqual(files[notice['path']]['blob_sha'], notice['blob_sha'])
            self.assertEqual(notice['notice_sha256'],
                             hashlib.sha256(notice['license_notice'].encode()).hexdigest())
            self.assertIn('GNU General Public License', notice['license_notice'])
            self.assertIn('special exception', notice['license_notice'])
        self.assertFalse(row['full_dependency_closure_verified'])
        self.assertFalse(row['sdk_built_this_session'])
        self.assertFalse(row['counted_as_connected'])

    def test_candle_additional_build_dependency_is_not_silently_approved(self):
        row = json.loads((ROOT/'sources/review-candle-dependencies666.json').read_text())['records'][0]
        lock_path = ROOT/'requirements/runtime-candle666.Cargo.lock'
        self.assertEqual(row['cargo_lock_sha256'], hashlib.sha256(lock_path.read_bytes()).hexdigest())
        lock = tomllib.loads(lock_path.read_text())
        packages = {(p['name'], p['version']): p for p in lock['package']}
        self.assertEqual(136, len(row['inventory']))
        for item in row['inventory']:
            self.assertEqual(packages[item['name'], item['version']]['checksum'], item['crate_sha256'])
        self.assertEqual(row['cargo_tree_sha256'], hashlib.sha256(row['cargo_tree'].encode()).hexdigest())
        target = next(r for r in row['inventory'] if r['name'] == 'target-lexicon')
        self.assertEqual('0.13.6', target['version'])
        self.assertNotIn(target['declared_license'], license_policy.PERMISSIVE)
        self.assertIn('pyo3-build-config v0.29.3', row['dependency_chain'])
        for original in row['original_license_files']:
            raw = original['license_text'].encode()
            self.assertEqual(original['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(original['blob_sha'],
                             hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
        self.assertFalse(row['complete_dependency_closure_verified'])
        self.assertFalse(row['runtime_executed_this_session'])
        self.assertFalse(row['counted_as_connected'])

    def test_reassessment_is_bound_to_original_license_bytes_and_review_files(self):
        decision = json.loads((ROOT/'sources/review-license-decision666.json').read_text())
        self.assertEqual(['Zlib', 'BSL-1.0', 'Unicode-3.0'], decision['approved_additions'])
        sources = {r['id']: r for r in read_registry()['records']}
        self.assertEqual({'bm25s', 'rustworkx', 'clingo', 'candle', 'tokenizers'},
                         {r['id'] for r in decision['records']})
        for row in decision['records']:
            with self.subTest(service=row['id']):
                self.assertEqual(sources[row['id']]['commit_sha'], row['commit'])
                self.assertEqual(sources[row['id']]['license_evidence'], row['root_license_evidence'])
                raw = (ROOT/row['source_review']).read_bytes()
                self.assertEqual(row['source_review_sha256'], hashlib.sha256(raw).hexdigest())
                reviewed = next(r for r in json.loads(raw)['records'] if r['id'] == row['id'])
                # Extract only license texts (not arbitrary source strings) from
                # the preserved original evidence and verify the selected digest.
                if row['id'] == 'bm25s':
                    texts = [f['text'] for f in reviewed['dependency_artifact']['license_files']]
                elif row['id'] == 'rustworkx':
                    texts = [reviewed['artifact_review']['files']['foldhash-0.1.5/LICENSE']]
                elif row['id'] == 'clingo':
                    texts = [f['license_text'] for f in reviewed['dependency_licenses']]
                else:
                    texts = [f['license_text'] for f in reviewed['inspected_dependencies']]
                digests = {hashlib.sha256(text.encode()).hexdigest() for text in texts}
                for dep in row['reviewed_dependencies']:
                    self.assertIn(dep['license_sha256'], digests)
                    self.assertEqual(dep['spdx'] in license_policy.PERMISSIVE,
                                     dep['allowed_by_current_policy'])
                self.assertEqual(row['id'] != 'tokenizers',
                                 all(d['allowed_by_current_policy'] for d in row['reviewed_dependencies']))
                self.assertFalse(reviewed['policy_reassessment']['complete_dependency_closure_verified'])
                self.assertFalse(row['counted_as_connected'])
                self.assertFalse(row['live_verified'])
                self.assertEqual('pendiente', connections.summary(row['id'])['state'])

