"""Independent finite reference and native build integrity without solver mocks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_logic666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'spend_limit': 8, 'unit_limit': 3, 'minimum_yield': 6}


class Logic666Tests(unittest.TestCase):
    def test_only_bounded_finite_numeric_constraints(self):
        sdk.validate('z3', 'constraints.check', CASE)
        for change in ({'dataset': 'real'}, {'spend_limit': -1}, {'spend_limit': 46},
                       {'unit_limit': -1}, {'unit_limit': 10}, {'minimum_yield': -1},
                       {'minimum_yield': 34}, {'unit_limit': True}, {'spend_limit': 8.0},
                       {'minimum_yield': float('nan')}, {'program': '(check-sat)'},
                       {'path': '/tmp/private'}, {'solver_options': {'timeout': 0}},
                       {'costs': [1,2,3]}, {'model': 'external'}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                sdk.validate('z3', 'constraints.check', CASE | change)

    def test_complete_scalar_reference_at_boundaries(self):
        self.assertEqual([(1, 1, 0)], sdk.scalar_candidates(CASE))
        self.assertEqual(64, len(sdk.scalar_candidates(CASE | {
            'spend_limit': 45, 'unit_limit': 9, 'minimum_yield': 0})))
        self.assertEqual([(3,3,3)], sdk.scalar_candidates(CASE | {
            'spend_limit': 45, 'unit_limit': 9, 'minimum_yield': 33}))
        self.assertEqual([], sdk.scalar_candidates(CASE | {'spend_limit': 0}))

    def test_wrong_verdict_and_noninteger_or_invalid_witness_rejected(self):
        self.assertEqual(1, sdk.verify_verdict(CASE, 'sat', (1,1,0)))
        for status, witness in [('unknown', None), ('unsat', None), ('sat', None),
                                ('sat', (True,1,0)), ('sat', (1.0,1,0)),
                                ('sat', (0,0,0)), ('sat', (1,1))]:
            with self.subTest(status=status, witness=witness), self.assertRaises(VerdugoError):
                sdk.verify_verdict(CASE, status, witness)
        impossible = CASE | {'spend_limit': 0}
        self.assertEqual(0, sdk.verify_verdict(impossible, 'unsat', None))
        with self.assertRaises(VerdugoError): sdk.verify_verdict(impossible, 'unsat', (0,0,0))

    def test_source_commit_and_no_gmp_or_python_runtime_dependencies(self):
        record = json.loads(sdk.CONTRACT.read_text())
        source = next(r for r in read_registry()['records'] if r['id']=='z3')
        self.assertEqual(source['commit_sha'], record['commit'])
        self.assertEqual('OFF', record['cmake_options']['Z3_USE_LIB_GMP'])
        self.assertEqual([], record['runtime_dependencies_python312'])
        self.assertEqual(9, sum(bool(f['installed_path']) for f in record['files']))
        self.assertTrue(record['license_text_read']); self.assertFalse(record['live_verified'])

    def test_changed_generated_native_bytes_and_build_options_rejected(self):
        record = json.loads(sdk.CONTRACT.read_text())
        record['files'] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); artifacts = {}
            for relative in record['native_artifacts'] + record['generated_python']:
                target = root/sdk.PACKAGE/relative
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b'original fixture')
                artifacts[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
            receipt = {'schema': 'verdugo.z3666.operator-build.v1',
                **{k:record[k] for k in ('commit','archive_sha256','build_tools','cmake_options')},
                'artifacts': artifacts}
            path = root/sdk.RECEIPT; path.parent.mkdir(parents=True); path.write_text(json.dumps(receipt))
            sdk.verify_build(root, record)
            target = root/sdk.PACKAGE/record['generated_python'][0]; target.write_bytes(b'changed generated')
            with self.assertRaises(VerdugoError): sdk.verify_build(root, record)
            target.write_bytes(b'original fixture')
            target = root/sdk.PACKAGE/record['native_artifacts'][0]; target.write_bytes(b'changed native')
            with self.assertRaises(VerdugoError): sdk.verify_build(root, record)
            target.write_bytes(b'original fixture')
            receipt['cmake_options'] = record['cmake_options'] | {'Z3_USE_LIB_GMP':'ON'}
            path.write_text(json.dumps(receipt))
            with self.assertRaises(VerdugoError): sdk.verify_build(root, record)
