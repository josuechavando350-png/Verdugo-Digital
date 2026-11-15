"""Boundaries and pinned native artifacts; original execution is separate."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from verdugo import local_encoding666 as encoding
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset':'demo','word_sequences':[['plan','unknown'],['review']],'max_length':4}


class Encoding666Tests(unittest.TestCase):
    def test_only_bounded_enumerated_input(self):
        encoding.validate('tokenizers','sequence.encode',CASE)
        for changes in ({'dataset':'real'},{'text':'private'},{'model':'remote'},
                        {'word_sequences':[]},{'word_sequences':[['plan']]*5},
                        {'word_sequences':[[]]},{'word_sequences':[['plan']*13]},
                        {'max_length':1},{'max_length':9}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                encoding.validate('tokenizers','sequence.encode',CASE | changes)

    def test_no_coercion_or_free_text(self):
        for word in (True, 1, None, 'plan send', 'PLAN', '[PAD]', {}, ['plan']):
            with self.subTest(word=word), self.assertRaises(VerdugoError):
                encoding.validate('tokenizers','sequence.encode',CASE | {'word_sequences':[[word]]})
        for length in (True, 4.0, '4'):
            with self.assertRaises(VerdugoError):
                encoding.validate('tokenizers','sequence.encode',CASE | {'max_length':length})

    def test_original_lock_and_source_pin(self):
        record=json.loads(encoding.CONTRACT.read_text())
        source=next(r for r in read_registry()['records'] if r['id']=='tokenizers')
        self.assertEqual(source['commit_sha'], record['commit'])
        lock=encoding.CONTRACT.parent.parent/'requirements/runtime-encoding666.Cargo.lock'
        self.assertEqual(record['cargo_lock_sha256'], hashlib.sha256(lock.read_bytes()).hexdigest())
        original=next(f for f in record['files'] if f['path']=='bindings/python/Cargo.lock')
        self.assertEqual(original['sha256'], record['cargo_lock_sha256'])
        self.assertEqual(13, sum(bool(f['installed_path']) for f in record['files']))

    def test_tampered_native_or_alternate_extension_fails(self):
        record=json.loads(encoding.CONTRACT.read_text()) | {'files':[]}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); native=root/encoding.NATIVE; native.parent.mkdir(parents=True)
            native.write_bytes(b'integrity fixture, never imported')
            receipt={'schema':'verdugo.tokenizers666.operator-build.v1',
                **{k:record[k] for k in ('commit','archive_sha256','cargo_lock_sha256',
                    'rust_version','maturin_version','build_environment')},
                'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest()}
            path=root/encoding.RECEIPT;path.parent.mkdir(parents=True);path.write_text(json.dumps(receipt))
            encoding.verify_build(root,record)
            alternate=native.with_name('tokenizers.cpython-312-x86_64-linux-gnu.so');alternate.write_bytes(b'other')
            with self.assertRaises(VerdugoError): encoding.verify_build(root,record)
            alternate.unlink(); native.write_bytes(b'mutated')
            with self.assertRaises(VerdugoError): encoding.verify_build(root,record)
