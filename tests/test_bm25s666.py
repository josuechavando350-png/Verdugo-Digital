"""Input, reference and provenance boundaries; original execution is separate."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_bm25s666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE={'dataset':'demo','documents':[[0,0,1],[1,2],[3]],'query':[0],'k':2}


class BM25S666Tests(unittest.TestCase):
    def test_only_bounded_synthetic_integers_are_accepted(self):
        sdk.validate('bm25s','retrieval.check',CASE)
        for change in ({'dataset':'real'},{'documents':[]},{'documents':[[0]]*9},
                       {'documents':[[]]},{'documents':[[0]*17]},{'documents':[[True]]},
                       {'documents':[[8]]},{'documents':[['private text']]},{'query':[]},
                       {'query':[0]*9},{'query':[16]},{'query':[False]},{'query':[float('nan')]},
                       {'k':0},{'k':4},{'k':True},{'path':'/tmp/index'},{'model':'remote'},
                       {'backend':'jax'},{'url':'https://example.invalid'}):
            with self.subTest(change=change),self.assertRaises(VerdugoError):
                sdk.validate('bm25s','retrieval.check',CASE|change)

    def test_scalar_formula_preserves_multiplicity_unknown_terms_and_ties(self):
        case={'documents':[[0],[0],[0]],'query':[0],'k':3}
        expected=math.log(8/7)/2.5
        for value in sdk.reference(case):self.assertAlmostEqual(expected,value)
        self.assertEqual([0,0,0],sdk.reference(case|{'query':[15]}))
        for value in sdk.reference(case|{'query':[0,0]}):self.assertAlmostEqual(2*expected,value)
        counts=sdk.verify_results(case,[expected]*3,[2,0,1],[expected]*3)
        self.assertEqual(3,counts['matching_documents'])
        self.assertNotIn('scores',counts)
        self.assertNotIn('documents',counts)
        self.assertTrue(all(type(v) is int for v in counts.values()))

    def test_native_values_cannot_pass_with_invalid_scores_or_top_k(self):
        expected=sdk.reference(CASE)
        sdk.verify_results(CASE,expected,[0,1],[expected[0],0])
        for actual,indices,scores in [([0,0,0],[0,1],[0,0]),
                                     ([float('nan'),0,0],[0,1],[expected[0],0]),
                                     (expected,[0,0],[expected[0]]*2),
                                     (expected,[0,3],[expected[0],0]),
                                     (expected,[True,0],[0,expected[0]]),
                                     (expected,[1,2],[0,0]),
                                     (expected,[0],[expected[0]])]:
            with self.subTest(indices=indices),self.assertRaises(VerdugoError):
                sdk.verify_results(CASE,actual,indices,scores)

    def test_source_contract_uses_original_commit_and_numpy_only_runtime(self):
        record=json.loads(sdk.CONTRACT.read_text())
        row=next(r for r in read_registry()['records'] if r['id']=='bm25s')
        self.assertEqual(row['commit_sha'],record['commit'])
        self.assertEqual({'numpy':'1.26.4'},record['runtime_dependencies'])
        self.assertEqual('none',record['numpy_build_options']['blas'])
        self.assertEqual('none',record['numpy_build_options']['lapack'])
        self.assertEqual(100,len(record['files']))
        self.assertEqual(2111,len(record['numpy']['files']))
        self.assertEqual('0.0.0',record['version'])
        self.assertIn('not a published release',record['version_scope'])
        self.assertFalse(record['live_verified'])
        for item in record['dependency_license_evidence']:
            self.assertEqual(item['sha256'],hashlib.sha256(item['text'].encode()).hexdigest())

    def test_missing_build_receipt_fails_without_importing_the_sdk(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sdk.runtime_profile,'interpreter',return_value=str(Path(tmp)/'bin/python')):
                self.assertFalse(sdk.runtime_state('bm25s')['version_matches'])
                with self.assertRaises(VerdugoError):sdk.run('bm25s',CASE)
