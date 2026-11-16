"""Finite graph semantics, strict input and original source/license boundaries."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_oxigraph666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'edges': [[0, 1], [1, 2]], 'remove': [[1, 2]]}


class Oxigraph666Tests(unittest.TestCase):
    def test_only_bounded_synthetic_integer_edges_are_accepted(self):
        sdk.validate('oxigraph', 'paths.check', CASE)
        sdk.validate('oxigraph', 'paths.check', {'dataset': 'demo', 'edges': [], 'remove': []})
        for change in ({'dataset': 'real'}, {'edges': [[0,1]]*33}, {'remove': [[0,1]]*9},
                       {'edges': [[0]]}, {'edges': [[0,1,2]]}, {'edges': [[0,8]]},
                       {'edges': [[-1,0]]}, {'edges': [[False,0]]}, {'remove': [[0,True]]},
                       {'edges': [[0,float('nan')]]}, {'edges': [['private',0]]},
                       {'query': 'SERVICE <https://example.invalid> {}'}, {'path': '/tmp/store'},
                       {'url': 'https://example.invalid'}, {'backend': 'rocksdb'}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                sdk.validate('oxigraph', 'paths.check', CASE | change)

    def test_positive_paths_preserve_direction_cycles_duplicates_and_removal(self):
        before_count, after_count, before, after = sdk.reference(CASE)
        self.assertEqual((2,1), (before_count,after_count))
        self.assertEqual({1,2,10}, {i for i, v in enumerate(before) if v == '1'})
        self.assertEqual({1}, {i for i, v in enumerate(after) if v == '1'})
        self.assertEqual('0'*64, sdk.reachability([]))
        cycle = sdk.reference({'edges': [[0,1],[1,0],[3,4]], 'remove': []})
        self.assertEqual({0,1,8,9,28}, {i for i,v in enumerate(cycle[2]) if v == '1'})
        duplicate = sdk.reference({'edges': [[0,0],[0,0]], 'remove': [[0,0],[0,0],[7,7]]})
        self.assertEqual((1,0), duplicate[:2]); self.assertEqual('1'+'0'*63, duplicate[2])
        self.assertEqual('0'*64, duplicate[3])

    def test_full_native_matrices_and_edge_counts_are_checked(self):
        before = ''.join('1' if i in (1,2,10) else '0' for i in range(64))
        after = '01'+'0'*62
        raw = ('2 1\n'+before+'\n'+after+'\n').encode()
        result = sdk.verify_result(CASE, raw)
        self.assertEqual(3, result['reachable_pairs_before'])
        self.assertEqual(1, result['reachable_pairs_after'])
        self.assertEqual(2, result['lost_reachability_pairs'])
        self.assertTrue(all(type(v) is int for v in result.values()))
        for wrong in (raw.replace(b'2 1',b'2 2'), raw.replace(before.encode(), b'0'*64),
                      raw+b' extra', b'\xff', b'2 1 true'):
            with self.assertRaises(VerdugoError): sdk.verify_result(CASE, wrong)

    def test_original_contract_preserves_compatible_pin_and_license_provenance(self):
        record = json.loads(sdk.CONTRACT.read_text())
        row = next(r for r in read_registry()['records'] if r['id'] == 'oxigraph')
        self.assertEqual(row['commit_sha'], record['commit'])
        self.assertEqual(913, len(record['files']))
        self.assertEqual(91, len(record['registry_dependencies']))
        self.assertEqual(5, len(record['inactive_registry_dependencies']))
        self.assertEqual('x86_64-unknown-linux-gnu', record['target'])
        self.assertFalse(record['default_features']); self.assertFalse(record['distribution_license_closure_verified'])
        self.assertFalse(record['compatible_psm_pin']['source_modified'])
        names = {x['id'] for x in record['resolved_graph']}
        self.assertIn('psm@0.1.24', names)
        self.assertFalse(any(name.startswith(('ar_archive_writer@','oxrocksdb-sys@','oxhttp@')) for name in names))
        self.assertEqual([], next(x['features'] for x in record['resolved_graph'] if x['id']=='oxigraph@0.6.0-dev'))
        for item in record['root_license_evidence'] + [f for d in record['registry_dependencies'] for f in d['selected_license_files']]:
            b = item['text'].encode()
            self.assertEqual(item['sha256'], hashlib.sha256(b).hexdigest())
            self.assertEqual(item['blob_sha'], hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest())
        driver = sdk.CONTRACT.parents[1]/'tests_runtime/oxigraph666-driver'
        for path, expected in record['driver_files'].items():
            self.assertEqual(expected, hashlib.sha256((driver/path).read_bytes()).hexdigest())

    def test_missing_or_modified_receipt_cannot_authorize_native_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {sdk.ENV: tmp}):
            self.assertFalse(sdk.runtime_state('oxigraph')['version_matches'])
            with self.assertRaises(VerdugoError): sdk.run('oxigraph', CASE)
            receipt = Path(tmp)/sdk.RECEIPT; receipt.parent.mkdir(parents=True); receipt.write_text('{}')
            self.assertFalse(sdk.runtime_state('oxigraph')['version_matches'])
