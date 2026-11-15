import copy
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from verdugo import local_runtime, local_analytics, product
from verdugo.__main__ import template
from verdugo.common import VerdugoError
from verdugo.engine import Engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from analytics_fixtures import CASES


class AnalyticsContracts(unittest.TestCase):
    def test_source_evidence_covers_every_recipe_at_catalog_pin(self):
        from verdugo.source_evidence import read_sources
        sources = {r['id']: r for r in read_sources()}
        manifest = json.loads((Path(__file__).resolve().parents[1]/'sources/contracts-v020.json').read_text())
        rows = manifest['files']
        self.assertEqual(set(local_analytics.SPECS), {r['service'] for r in rows})
        for r in rows:
            self.assertEqual(40, len(r['blob_sha']))
            if 'commit' in r:
                self.assertEqual(sources[r['service']]['commit_sha'], r['commit'])

    def test_default_configuration_requires_explicit_reviews(self):
        config = template('nexus')['tenants']['nexus']['services']
        for sid in local_analytics.SPECS:
            for field in ('enabled', 'license_reviewed', 'runtime_reviewed'):
                self.assertIs(config[sid][field], False)

    def test_missing_distribution_prevents_execution(self):
        with patch('verdugo.local_runtime.metadata.version', side_effect=importlib.metadata.PackageNotFoundError):
            for sid, (op, _, version) in local_analytics.SPECS.items():
                with self.subTest(service=sid), self.assertRaises(VerdugoError):
                    local_runtime.preflight(sid, op, {'version': version, 'runtime_reviewed': True})

    def test_recipe_change_invalidates_fingerprint(self):
        original = Path.read_bytes
        def changed(path):
            return original(path)+(b'\n# changed' if path.name == 'local_analytics.py' else b'')
        before = local_runtime.implementation_digest()
        with patch.object(Path, 'read_bytes', changed):
            self.assertNotEqual(before, local_runtime.implementation_digest())

    def test_fixtures_can_never_be_labeled_real(self):
        with self.assertRaises(VerdugoError):
            local_runtime.validate('faker', 'fixtures.generate', dict(CASES['faker'], dataset='real'))

    def test_regression_calibration_lengths_must_agree(self):
        for change in ({'train_y': [1]}, {'score_x': [[1, 2]]}, {'calibration_y': [2]}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                local_runtime.validate('mapie', 'regression.intervals', dict(CASES['mapie'], **change))

    def test_invalid_graph_references_and_duplicate_nodes(self):
        for change in ({'nodes': ['x', 'x']}, {'edges': [['intake', 'unknown']]},
                       {'edges': [['intake', 'qualify'], ['intake', 'qualify']]}):
            with self.assertRaises(VerdugoError):
                local_runtime.validate('networkx', 'dependencies.analyze', dict(CASES['networkx'], **change))

    def test_bounds_and_statistical_assumptions(self):
        changes = {
            'pymcdm': {'weights': [0.5, 0.6]}, 'h3': {'locations': [[91, 0]]},
            'mlxtend': {'baskets': [['a', 'a'], ['b']]}, 'nashpy': {'row_payoffs': [[1]*3]*3},
            'lifelines': {'events': [1, 1, 1, 1]}, 'statsforecast': {'horizon': 31},
            'numpy-financial': {'rate': -1}, 'causal-learn': {'rows': [[1, 1]]*20},
            'pyod': {'reference': [[1]]}, 'sqlglot': {'dialect': 'arbitrary'},
        }
        for sid, change in changes.items():
            with self.subTest(service=sid), self.assertRaises(VerdugoError):
                local_runtime.validate(sid, local_analytics.SPECS[sid][0], dict(CASES[sid], **change))

    def test_local_only_product_requires_no_http_service(self):
        e = Engine(':memory:', template('nexus'))
        request = {'id': 'analytics', 'services': [], 'dataset': 'demo', 'currency': 'MXN',
                   'analyses': [{'id': 'summary', 'service': 'river', 'params': CASES['river']}]}
        try:
            r = product.observe(e, request)
            self.assertEqual('blocked', r['state'])
            self.assertEqual('river', r['blockers'][0]['service'])
            self.assertFalse(r['external_calls_made'])
        finally: e.close()

    def test_product_dataset_currency_duplicates_and_forbidden_service(self):
        e = Engine(':memory:', template('nexus'))
        request = {'id': 'analytics', 'services': [], 'dataset': 'demo', 'currency': 'MXN',
                   'analyses': [{'id': 'sum', 'service': 'arrow', 'params': CASES['arrow']}]}
        bad = []
        r=copy.deepcopy(request);r['analyses'][0]['params']['dataset']='real';bad.append(r)
        r=copy.deepcopy(request);r['analyses'][0]['params']['currency']='USD';bad.append(r)
        r=copy.deepcopy(request);r['analyses'].append(r['analyses'][0]);bad.append(r)
        r=copy.deepcopy(request);r['analyses'][0]['service']='unimplemented-provider';bad.append(r)
        r=copy.deepcopy(request);r['analyses'][0]['depends_on']=['unknown'];bad.append(r)
        try:
            for r in bad:
                with self.assertRaises(VerdugoError): product.observe(e,r)
        finally: e.close()


def contract_case(sid):
    def test(self):
        op = local_analytics.SPECS[sid][0]
        local_runtime.validate(sid, op, CASES[sid])
        for name in ('shell', 'url', 'path', 'sql', 'token', 'tenant', 'model', 'callback'):
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, op, dict(CASES[sid], **{name: 'blocked'}))
        for dataset in ('', None, True, 'production'):
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, op, dict(CASES[sid], dataset=dataset))
        with self.assertRaises(VerdugoError):
            local_runtime.validate(sid, op+'.unimplemented', CASES[sid])
    return test


for _sid in local_analytics.SPECS:
    setattr(AnalyticsContracts, 'test_contract_'+_sid.replace('-', '_'), contract_case(_sid))
