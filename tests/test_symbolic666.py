"""Finite numeric inputs, independent algebra/graph references and provenance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_symbolic666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

POLY = {'dataset':'demo','coefficients':[1,-2,1],'points':[0,1,3]}
GRAPH = {'dataset':'demo','node_count':4,'edges':[[0,1],[1,2],[2,0],[0,1]],'start':0}


class Symbolic666Tests(unittest.TestCase):
    def test_polynomial_bounds_and_no_expression_evaluation(self):
        sdk.validate('sympy','polynomial.check',POLY)
        for change in ({'coefficients':[]},{'coefficients':[1]*7},{'coefficients':[21]},
                       {'coefficients':[True]},{'coefficients':[1.0]},
                       {'coefficients':[float('nan')]},{'coefficients':['x**2']},
                       {'points':[]},{'points':[0]*9},{'points':[-11]},
                       {'dataset':'real'},{'expression':'__import__("os")'},
                       {'domain':'EX'},{'path':'/tmp/private'}):
            with self.subTest(change=change),self.assertRaises(VerdugoError):
                sdk.validate('sympy','polynomial.check',POLY|change)

    def test_graph_bounds_and_no_external_rdf_or_queries(self):
        sdk.validate('rdflib','reachability.check',GRAPH)
        for change in ({'node_count':0},{'node_count':9},{'node_count':True},
                       {'edges':[[0,1]]*17},{'edges':[[0,4]]},{'edges':[[0,True]]},
                       {'edges':[[0,1,2]]},{'edges':[['private',1]]},
                       {'start':-1},{'start':4},{'source':'https://example.invalid'},
                       {'sparql':'SELECT * WHERE {}'},{'store':'remote'},{'dataset':'real'}):
            with self.subTest(change=change),self.assertRaises(VerdugoError):
                sdk.validate('rdflib','reachability.check',GRAPH|change)

    def test_scalar_algebra_zero_constant_sign_and_multiplicity(self):
        self.assertEqual([0],sdk.normalize([0,0]))
        self.assertEqual([1,-2,1],sdk.multiply([1,-1],[1,-1]))
        self.assertEqual([-2,0,2],sdk.multiply([-2],sdk.multiply([1,-1],[1,1])))
        self.assertEqual(4,sdk.evaluate([1,-2,1],3))
        self.assertEqual(7,sdk.evaluate([7],-10))
        self.assertEqual(0,sdk.evaluate([0],5))

    def test_graph_reference_direction_cycle_duplicates_and_isolation(self):
        self.assertEqual([0,1,2],sdk.scalar_reachable(GRAPH))
        self.assertEqual([3],sdk.scalar_reachable(GRAPH|{'start':3}))
        self.assertEqual([2],sdk.scalar_reachable(GRAPH|{'edges':[[0,1],[1,2]],'start':2}))
        self.assertEqual([0,1,2,3],sdk.scalar_reachable(GRAPH|{'edges':[[0,1],[0,2],[1,3],[2,3]]}))
        self.assertEqual([0],sdk.scalar_reachable(GRAPH|{'edges':[]}))

    def test_original_commits_versions_and_dependency_licenses(self):
        records=json.loads(sdk.CONTRACT.read_text())['records']; registry=read_registry()['records']
        for r in records:
            self.assertEqual(next(x['commit_sha'] for x in registry if x['id']==r['id']),r['commit'])
            self.assertEqual(sdk.SPECS[r['id']][2],r['version'])
            self.assertTrue(r['license_text_read']);self.assertFalse(r['live_verified'])
            self.assertEqual(1,len(r['dependencies']))
            self.assertTrue(r['dependencies'][0]['license_texts_read'])
        sympy=next(r for r in records if r['id']=='sympy')
        self.assertEqual(1572,sum(bool(f['installed_path']) for f in sympy['files']))
        self.assertEqual('sympy/release.py',sympy['generated_files'][0]['path'])
        self.assertTrue(sympy['version_evidence']['not_a_published_release'])

    def test_tampered_installed_source_rejected_before_sdk_import(self):
        record=json.loads(sdk.CONTRACT.read_text())['records'][0]
        first=next(f for f in record['files'] if f['installed_path'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/sdk.PACKAGE/first['installed_path']
            p.parent.mkdir(parents=True);p.write_bytes(b'changed source')
            with patch.object(sdk.runtime_profile,'interpreter',return_value=str(root/'bin/python')):
                self.assertFalse(sdk.runtime_state(record['id'])['version_matches'])
