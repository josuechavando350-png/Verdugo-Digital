"""Candle numeric bounds and native build integrity; execution tested separately."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from verdugo import local_tensor666 as tensor
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE={'dataset':'demo','features':[[1,0],[0,1],[1,1]],'coefficients':[2,-1]}


class Tensor666Tests(unittest.TestCase):
    def test_only_fixed_bounded_numeric_input(self):
        tensor.validate('candle','scores.normalize',CASE)
        for changes in ({'dataset':'real'},{'model':'remote'},{'device':'cuda'},
                        {'features':[]},{'features':[[1,2]]*9},
                        {'coefficients':[1]},{'coefficients':[1]*5}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                tensor.validate('candle','scores.normalize',CASE | changes)
        with self.assertRaises(VerdugoError):tensor.validate('candle','model.load',CASE)

    def test_ragged_coerced_or_extreme_values_rejected(self):
        for value in (True,1.0,'1',101,-101,None):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                tensor.validate('candle','scores.normalize',CASE | {'features':[[value,0],[1,2]]})
        with self.assertRaises(VerdugoError):
            tensor.validate('candle','scores.normalize',CASE | {'features':[[1,2],[1]]})

    def test_original_source_and_operator_lock_have_explicit_provenance(self):
        record=json.loads(tensor.CONTRACT.read_text())
        source=next(r for r in read_registry()['records'] if r['id']=='candle')
        self.assertEqual(source['commit_sha'],record['commit'])
        self.assertEqual(19,sum(bool(f['installed_path']) for f in record['files']))
        lock=tensor.CONTRACT.parent.parent/'requirements/runtime-candle666.Cargo.lock'
        self.assertEqual(record['cargo_lock_sha256'],hashlib.sha256(lock.read_bytes()).hexdigest())
        self.assertEqual('1',record['build_environment']['CARGO_BUILD_JOBS'])

    def test_native_mutation_and_alternate_extension_fail_closed(self):
        record=json.loads(tensor.CONTRACT.read_text()) | {'files':[]}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);native=root/tensor.NATIVE;native.parent.mkdir(parents=True)
            native.write_bytes(b'integrity fixture, never imported')
            receipt={'schema':'verdugo.candle666.operator-build.v1',
                **{k:record[k] for k in ('commit','archive_sha256','cargo_lock_sha256',
                    'rust_version','maturin_version','build_environment')},
                'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest()}
            path=root/tensor.RECEIPT;path.parent.mkdir(parents=True);path.write_text(json.dumps(receipt))
            tensor.verify_build(root,record)
            alternate=native.with_name('candle.cpython-313-x86_64-linux-gnu.so');alternate.write_bytes(b'other')
            with self.assertRaises(VerdugoError):tensor.verify_build(root,record)
            alternate.unlink();native.write_bytes(b'changed')
            with self.assertRaises(VerdugoError):tensor.verify_build(root,record)
