"""Bounded schema cases and original source/dependency integrity."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_schema666 as schema
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

ROW={'decision':'review','approved':False,'item_count':2,'variant':'canonical'}
CASE={'dataset':'demo','cases':[ROW]}


class Schema666Tests(unittest.TestCase):
    def test_fixed_bounded_cases_no_schema_or_text_input(self):
        schema.validate('guidance','schema.check',CASE)
        for changes in ({'dataset':'real'},{'cases':[]},{'cases':[ROW]*9},
                        {'schema':{}},{'text':'free text'},{'model':'remote'}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                schema.validate('guidance','schema.check',CASE | changes)
        with self.assertRaises(VerdugoError):schema.validate('guidance','model.run',CASE)

    def test_strict_types_and_enum_boundaries(self):
        for changes in ({'approved':1},{'approved':'false'},{'decision':'publish'},
                        {'item_count':True},{'item_count':2.0},{'item_count':-1},
                        {'item_count':7},{'variant':'arbitrary'},{'extra':0}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                schema.validate('guidance','schema.check',{'dataset':'demo','cases':[ROW | changes]})

    def test_source_pin_and_published_dependency_scope(self):
        record=json.loads(schema.CONTRACT.read_text())
        source=next(r for r in read_registry()['records'] if r['id']=='guidance')
        self.assertEqual(source['commit_sha'],record['commit'])
        self.assertEqual(78,record['installed_source_count'])
        self.assertEqual({'llguidance':'1.6.1','guidance-stitch':'0.1.5'},record['runtime_versions'])
        self.assertEqual(1,sum(f['path'].endswith('.so') for f in record['dependency_files']))
        for dep in record['dependency_artifacts']:
            for license_file in dep['license_files']:
                self.assertEqual(license_file['sha256'],hashlib.sha256(license_file['text'].encode()).hexdigest())

    def test_source_and_native_dependency_mutation_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'original.py';source.write_bytes(b'original fixture')
            native=root/'llguidance/_lib.abi3.so';native.parent.mkdir();native.write_bytes(b'never imported fixture')
            record={'commit':'a'*40,'runtime_versions':{},'installed_source_count':1,
                'files':[{'installed_path':'original.py','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}],
                'dependency_files':[{'distribution':'llguidance','path':'llguidance/_lib.abi3.so',
                    'sha256':hashlib.sha256(native.read_bytes()).hexdigest()}]}
            contract=root/'contract.json';contract.write_text(json.dumps(record))
            class Dist:
                version='0.3.2'
                def locate_file(self,path):return root/path
            with patch.object(schema,'CONTRACT',contract), patch.object(schema.metadata,'distribution',return_value=Dist()):
                schema.verify_source()
                native.write_bytes(b'mutated')
                with self.assertRaises(VerdugoError):schema.verify_source()
                native.write_bytes(b'never imported fixture');source.write_bytes(b'mutated')
                with self.assertRaises(VerdugoError):schema.verify_source()
