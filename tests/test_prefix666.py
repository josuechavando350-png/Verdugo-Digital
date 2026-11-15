"""Fixed prefix inputs, authentic source pins and fail-closed integrity."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_prefix666 as prefix
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

ROW = {'decision':'review','mode':'dry_run','cut':'complete'}
CASE = {'dataset':'demo','cases':[ROW]}


class Prefix666Tests(unittest.TestCase):
    def test_no_unbounded_text_schema_or_model_inputs(self):
        prefix.validate('lm-format-enforcer','prefix.check',CASE)
        for change in ({'dataset':'real'},{'cases':[]},{'cases':[ROW]*9},
                       {'text':'arbitrary'},{'schema':{}},{'model':'remote'}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                prefix.validate('lm-format-enforcer','prefix.check',CASE | change)
        with self.assertRaises(VerdugoError):prefix.validate('lm-format-enforcer','generate',CASE)

    def test_enum_boundaries(self):
        for change in ({'decision':True},{'decision':'approve'},{'mode':'live'},
                       {'cut':0},{'cut':'arbitrary'},{'extra':1}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                prefix.validate('lm-format-enforcer','prefix.check',{'dataset':'demo','cases':[ROW | change]})

    def test_original_pin_and_dependency_license_evidence(self):
        record=json.loads(prefix.CONTRACT.read_text())
        source=next(r for r in read_registry()['records'] if r['id']=='lm-format-enforcer')
        self.assertEqual(source['commit_sha'],record['commit'])
        self.assertEqual(21,record['installed_source_count'])
        self.assertEqual(7,len(record['dependency_files']))
        self.assertEqual('MIT',record['dependency_artifact']['license'])
        for item in record['dependency_artifact']['license_files']:
            self.assertEqual(item['sha256'],hashlib.sha256(item['text'].encode()).hexdigest())

    def test_installed_source_and_dependency_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.py';source.write_bytes(b'original fixture')
            dep=root/'dependency.py';dep.write_bytes(b'dependency fixture')
            record={'commit':'a'*40,'installed_source_count':1,
                'files':[{'installed_path':'source.py','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}],
                'dependency_files':[{'path':'dependency.py','sha256':hashlib.sha256(dep.read_bytes()).hexdigest()}]}
            contract=root/'contract.json';contract.write_text(json.dumps(record))
            class Dist:
                def __init__(self,name):self.version='0.11.3' if name=='lm-format-enforcer' else '0.3.3'
                def locate_file(self,path):return root/path
            with patch.object(prefix,'CONTRACT',contract), patch.object(prefix.metadata,'distribution',side_effect=Dist):
                prefix.verify_source()
                source.write_bytes(b'mutated')
                with self.assertRaises(VerdugoError):prefix.verify_source()
                source.write_bytes(b'original fixture');dep.write_bytes(b'mutated')
                with self.assertRaises(VerdugoError):prefix.verify_source()
