"""Bounded native CPU quantization and artifact integrity contracts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from verdugo import local_quant666 as quant
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE={'dataset':'demo','values':[-2,0,2]}


class Quant666Tests(unittest.TestCase):
    def test_fixed_bounded_numeric_inputs(self):
        quant.validate('bitsandbytes','quantization.check',CASE)
        for changes in ({'dataset':'real'},{'values':[]},{'values':[0]*513},
                        {'model':'remote'},{'device':'cuda'},{'blocksize':128}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                quant.validate('bitsandbytes','quantization.check',CASE | changes)

    def test_no_coercion_or_overflow(self):
        for value in (True,0.0,'1',None,[],1001,-1001):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                quant.validate('bitsandbytes','quantization.check',CASE | {'values':[value]})
        with self.assertRaises(VerdugoError):quant.validate('bitsandbytes','model.load',CASE)

    def test_original_source_and_explicit_cpu_build(self):
        record=json.loads(quant.CONTRACT.read_text())
        original=next(r for r in read_registry()['records'] if r['id']=='bitsandbytes')
        self.assertEqual(original['commit_sha'],record['commit'])
        self.assertEqual(48,sum(bool(f['installed_path']) for f in record['files']))
        self.assertIn('-DCOMPUTE_BACKEND=cpu',record['build_environment']['CMAKE_ARGS'])
        self.assertIn('-DHAS_AVX512F_FLAG=FALSE',record['build_environment']['CMAKE_ARGS'])
        self.assertEqual('2.9.1+cpu',record['torch_version'])

    def test_native_mutation_and_alternate_backend_rejected(self):
        record=json.loads(quant.CONTRACT.read_text()) | {'files':[]}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);native=root/quant.NATIVE;native.parent.mkdir(parents=True)
            native.write_bytes(b'integrity fixture, never loaded')
            receipt={'schema':'verdugo.bitsandbytes666.operator-build.v1',
                **{k:record[k] for k in ('commit','archive_sha256','build_tools','torch_version','build_environment')},
                'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest()}
            path=root/quant.RECEIPT;path.parent.mkdir(parents=True);path.write_text(json.dumps(receipt))
            quant.verify_build(root,record)
            alternate=native.with_name('libbitsandbytes_cuda130.so');alternate.write_bytes(b'other')
            with self.assertRaises(VerdugoError):quant.verify_build(root,record)
            alternate.unlink();native.write_bytes(b'changed')
            with self.assertRaises(VerdugoError):quant.verify_build(root,record)
