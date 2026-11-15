"""Finite input, independent semantics and source/build integrity boundaries."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_egg666 as sdk
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'nodes': [{'op': 0, 'children': []}, {'op': 1, 'children': []},
        {'op': 2, 'children': [0]}, {'op': 2, 'children': [1]}], 'equalities': [[0, 1]]}


class Egg666Tests(unittest.TestCase):
    def test_only_bounded_acyclic_synthetic_graphs_are_accepted(self):
        sdk.validate('egg', 'congruence.check', CASE)
        for change in ({'dataset': 'real'}, {'nodes': []}, {'nodes': CASE['nodes']*5},
                       {'nodes': [{'op': 0, 'children': [0]}]},
                       {'nodes': [{'op': True, 'children': []}]},
                       {'nodes': [{'op': 8, 'children': []}]},
                       {'nodes': [{'op': 0, 'children': [], 'code': 'private'}]},
                       {'nodes': [{'op': 0, 'children': []}, {'op': 1, 'children': [False]}]},
                       {'equalities': [[0, 4]]}, {'equalities': [[0, True]]},
                       {'equalities': [[0, 1]]*17}, {'equalities': [[0]]},
                       {'nodes': [{'op': float('nan'), 'children': []}]},
                       {'rules': ['x=y']}, {'path': '/tmp/file'}, {'command': 'anything'},
                       {'url': 'https://example.invalid'}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                sdk.validate('egg', 'congruence.check', CASE | change)

    def test_congruence_propagates_without_assuming_injectivity_or_commutativity(self):
        classes = sdk.reference(CASE)
        self.assertEqual(classes[0], classes[1]); self.assertEqual(classes[2], classes[3])
        self.assertNotEqual(classes[0], classes[2])
        reverse = sdk.reference(CASE | {'equalities': [[2, 3]]})
        self.assertNotEqual(reverse[0], reverse[1])
        arity = {'nodes': [{'op': 0, 'children': []}, {'op': 1, 'children': []},
                          {'op': 2, 'children': [0, 1]}, {'op': 2, 'children': [1, 0]},
                          {'op': 2, 'children': [0]}], 'equalities': []}
        self.assertEqual(5, len(set(sdk.reference(arity))))
        chain = copy.deepcopy(CASE)
        chain['nodes'] += [{'op': 3, 'children': [2]}, {'op': 3, 'children': [3]}]
        self.assertEqual(3, len(set(sdk.reference(chain))))
        self.assertEqual(1, len(set(sdk.reference(CASE | {'equalities': [[0,1],[1,2],[2,3]]}))))

    def test_every_native_pair_and_class_count_is_verified(self):
        valid = b'4 2\n1100110000110011\n'
        value = sdk.verify_result(CASE, valid)
        self.assertEqual({'input_nodes': 4, 'equivalence_classes': 2, 'equivalent_pairs': 2,
                          'supplied_equalities': 1, 'pairwise_checks': 16}, value)
        self.assertTrue(all(type(v) is int for v in value.values()))
        for raw in (b'4 2\n1100110000110010', b'4 1\n1100110000110011', valid+b' extra',
                    b'4 2\nTrue', b'\xff'):
            with self.assertRaises(VerdugoError): sdk.verify_result(CASE, raw)

    def test_contract_matches_original_and_hashes_all_selected_license_texts(self):
        record = json.loads(sdk.CONTRACT.read_text())
        row = next(r for r in read_registry()['records'] if r['id'] == 'egg')
        self.assertEqual(row['commit_sha'], record['commit'])
        self.assertEqual(40, len(record['files']))
        self.assertEqual(21, len(record['registry_dependencies']))
        self.assertFalse(record['default_features'])
        self.assertFalse(record['distribution_license_closure_verified'])
        selected = record['root_license_evidence'] + [f for d in record['registry_dependencies']
                                                     for f in d['selected_license_files']]
        for f in selected:
            b = f['text'].encode()
            self.assertEqual(f['sha256'], hashlib.sha256(b).hexdigest())
            self.assertEqual(f['blob_sha'], hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest())
        driver = sdk.CONTRACT.parents[1]/'tests_runtime/egg666-driver'
        for path, expected in record['driver_files'].items():
            self.assertEqual(expected, hashlib.sha256((driver/path).read_bytes()).hexdigest())
        self.assertEqual([], next(x for x in record['resolved_graph'] if x['id']=='egg@0.11.0')['features'])

    def test_missing_unsafe_or_modified_receipt_cannot_authorize_a_binary(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {sdk.ENV: tmp}):
            self.assertFalse(sdk.runtime_state('egg')['version_matches'])
            with self.assertRaises(VerdugoError): sdk.run('egg', CASE)
            receipt = Path(tmp)/sdk.RECEIPT; receipt.parent.mkdir(parents=True)
            receipt.write_text('{}')
            self.assertFalse(sdk.runtime_state('egg')['version_matches'])
        for value in ('relative', '/tmp/../usr', '/tmp\nother'):
            with patch.dict(os.environ, {sdk.ENV: value}):
                self.assertFalse(sdk.runtime_state('egg')['version_matches'])
