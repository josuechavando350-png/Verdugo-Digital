"""Counts-only plans retain full-input binding for finite graph/token adapters."""
import copy
import json
import unittest
from unittest.mock import patch

from verdugo.__main__ import template
from verdugo.common import VerdugoError, digest
from verdugo.engine import Engine
from verdugo import local_egg666, local_bm25s666, local_oxigraph666


class FinitePlanPrivacy666Tests(unittest.TestCase):
    def test_plan_projection_hides_inputs_without_weakening_idempotency(self):
        cases = [
            (local_oxigraph666, 'oxigraph', {'dataset': 'demo', 'edges': [[0,1]], 'remove': []},
             {'dataset': 'demo', 'edge_records': 1, 'remove_records': 0},
             lambda p: p['edges'].__setitem__(0, [1,0]), ('"edges"', '"remove"')),
            (local_egg666, 'egg', {'dataset': 'demo', 'nodes': [{'op': 0, 'children': []},
              {'op': 1, 'children': []}], 'equalities': [[0, 1]]},
             {'dataset': 'demo', 'input_nodes': 2, 'supplied_equalities': 1},
             lambda p: p['equalities'].__setitem__(0, [0, 0]), ('"children"', '"equalities"')),
            (local_bm25s666, 'bm25s', {'dataset': 'demo', 'documents': [[0,1], [1]], 'query': [0], 'k': 1},
             {'dataset': 'demo', 'document_count': 2, 'document_tokens': 3, 'query_tokens': 1, 'k': 1},
             lambda p: p['query'].__setitem__(0, 1), ('"documents"', '"query"')),
        ]
        for sdk, sid, params, projection, change, forbidden in cases:
            with self.subTest(service=sid):
                operation, distribution, version = sdk.SPECS[sid]
                state = {'distribution': distribution, 'expected': version, 'installed': version,
                         'version_matches': True, 'extra_distributions': {}, 'operation': operation,
                         'execution_verified': False, 'runtime_binding': 'a'*64}
                cfg = template('nexus')
                cfg['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True, runtime_reviewed=True)
                with patch.object(sdk, 'runtime_state', return_value=state):
                    engine = Engine(':memory:', cfg)
                    try:
                        command = {'service': sid, 'operation': operation, 'params': params, 'key': 'same-counts'}
                        planned = engine.plan(command)
                        self.assertEqual(projection, planned['request']['params'])
                        self.assertEqual(digest(params), planned['request']['input_sha256'])
                        self.assertEqual(planned, engine.plan(command))
                        changed = copy.deepcopy(params); change(changed)
                        with self.assertRaises(VerdugoError): engine.plan(command | {'params': changed})
                        for text in forbidden:
                            self.assertNotIn(text, '\n'.join(engine.db.iterdump()))
                            self.assertNotIn(text, json.dumps(planned))
                        # The executable request remains private in memory and retains exact input.
                        request, _, fingerprint = engine.prepare(command)
                        self.assertEqual(params, request['public']['params'])
                        self.assertEqual(planned['fingerprint'], fingerprint)
                    finally:
                        engine.close()
