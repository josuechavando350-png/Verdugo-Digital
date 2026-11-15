"""Native source integrity, synthetic scope, and independent-neighbor rejection."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from verdugo import local_usearch666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'case': 'plane'}


class USearch666Tests(unittest.TestCase):
    def test_only_fixed_synthetic_cases(self):
        for case in ('line', 'plane'):
            sdk.validate('usearch', 'neighbors.check', CASE | {'case': case})
        for changes in ({'dataset': 'real'}, {'case': 'remote'}, {'case': []},
                        {'vectors': [[1, 2]]}, {'model': 'remote'}, {'path': '/tmp/input'},
                        {'device': 'cuda'}, {'callback': 'eval'}, {'wanted': 10}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                sdk.validate('usearch', 'neighbors.check', CASE | changes)
        with self.assertRaises(VerdugoError): sdk.validate('usearch', 'index.load', CASE)

    def test_original_sources_and_real_native_build_options(self):
        record = json.loads(sdk.CONTRACT.read_text())
        reg = next(r for r in read_registry()['records'] if r['id'] == 'usearch')
        self.assertEqual(reg['commit_sha'], record['commit'])
        self.assertEqual(6, len(record['sources']))
        self.assertEqual('OFF', record['cmake_options']['USEARCH_BUILD_STUB'])
        self.assertEqual('1', record['cmake_options']['USEARCH_DENSE_DTYPES'])
        self.assertEqual('OFF', record['cmake_options']['USEARCH_MULTIVERSIONED'])
        self.assertEqual('3.0.0rc1', record['version'])
        self.assertEqual(6, sum(bool(f['installed_path']) for f in record['sources'][0]['files']))
        for source in record['sources']:
            self.assertTrue(source['license_text_read'])
            self.assertIn(source['license'], ('Apache-2.0', 'MIT'))
            for f in source['files']:
                self.assertRegex(f['blob_sha'], '^[a-f0-9]{40}$')
                self.assertRegex(f['sha256'], '^[a-f0-9]{64}$')

    def test_scalar_reference_ties_and_wrong_neighbors(self):
        rows, queries = [[0, 0], [2, 0], [0, 3], [9, 9]], [[1, 0]]
        good = [[(1, 1.0), (0, 1.0), (2, 10**.5)]]
        self.assertEqual(0, sdk.verify_neighbors(rows, queries, good))
        for bad in ([], [[(1, 1.0)]], [[(1, 1.0), (1, 1.0), (2, 10**.5)]],
                    [[(1, 2.0), (0, 1.0), (2, 10**.5)]],
                    [[(1, 1.0), (0, 1.0), (3, 145**.5)]],
                    [[(2, 10**.5), (0, 1.0), (1, 1.0)]],
                    [[(1, float('nan')), (0, 1.0), (2, 10**.5)]]):
            with self.subTest(bad=bad), self.assertRaises(VerdugoError):
                sdk.verify_neighbors(rows, queries, bad)

    def test_receipt_mutation_stub_and_alternate_extension_fail_closed(self):
        record = json.loads(sdk.CONTRACT.read_text())
        record['sources'][0]['files'] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); native = root / sdk.NATIVE; native.parent.mkdir(parents=True)
            native.write_bytes(b'integrity fixture, never executed')
            receipt = {'schema': 'verdugo.usearch666.operator-build.v1',
                       **{k: record[k] for k in ('commit', 'build_tools', 'build_environment', 'cmake_options')},
                       'source_archives': {r['id']: r['archive_sha256'] for r in record['sources']},
                       'native_sha256': hashlib.sha256(native.read_bytes()).hexdigest()}
            path = root / sdk.RECEIPT; path.parent.mkdir(parents=True); path.write_text(json.dumps(receipt))
            sdk.verify_build(root, record)
            alternate = native.with_name('stub.so'); alternate.write_bytes(b'other')
            with self.assertRaises(VerdugoError): sdk.verify_build(root, record)
            alternate.unlink()
            bad = json.loads(json.dumps(receipt)); bad['cmake_options']['USEARCH_BUILD_STUB'] = 'ON'
            path.write_text(json.dumps(bad))
            with self.assertRaises(VerdugoError): sdk.verify_build(root, record)
            path.write_text(json.dumps(receipt)); native.write_bytes(b'changed')
            with self.assertRaises(VerdugoError): sdk.verify_build(root, record)
