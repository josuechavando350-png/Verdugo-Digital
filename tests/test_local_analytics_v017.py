"""v0.17: contracts of the 27 analytics recipes. No third-party library is imported here.

Real execution against the installed libraries is verified separately by
tests_runtime in the runtime acceptance workflow.
"""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests_runtime'))
from analytics_fixtures import CASES

from verdugo import connections, local_analytics, local_runtime, runtime_profile
from verdugo.__main__ import template
from verdugo.catalog import catalog
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.license_policy import record


class AnalyticsContracts(unittest.TestCase):
    def test_inventory_matches_catalogue_policy_and_map(self):
        ids = {r['id'] for r in catalog()}
        self.assertEqual(27, len(local_analytics.SPECS))
        self.assertEqual(set(local_analytics.SPECS), set(local_analytics.FIELDS))
        self.assertEqual(set(local_analytics.SPECS), set(local_analytics.HANDLERS))
        self.assertEqual(set(local_analytics.SPECS), set(CASES))
        self.assertEqual(46, len(local_runtime.SPECS))
        for sid, (operation, distribution, version) in local_analytics.SPECS.items():
            with self.subTest(sid=sid):
                self.assertIn(sid, ids)
                self.assertNotEqual('excluido', record(sid)['policy'])
                self.assertEqual('biblioteca', connections.read_map()[0][sid])
                self.assertEqual('conectado', connections.state(sid))
                self.assertTrue(local_runtime.supports(sid, operation))
                self.assertRegex(version, r'^[0-9][0-9A-Za-z.]*$')
                self.assertNotIn(version.lower(), ('latest', 'main'))
                self.assertEqual(local_runtime.SPECS[sid], (operation, distribution, version))

    def test_requirements_pin_every_tested_distribution(self):
        lines = (ROOT / 'requirements' / 'runtime-analytics.txt').read_text().splitlines()
        pins = {line.split('==')[0].split('[')[0]: line.split('==')[1] for line in lines if '==' in line}
        constraints = (ROOT / 'requirements' / 'runtime-analytics.constraints.txt').read_text().splitlines()
        locked = {line.split('==')[0].lower(): line.split('==')[1] for line in constraints if '==' in line}
        self.assertIn('-c runtime-analytics.constraints.txt', lines)
        for sid, (_, distribution, version) in local_analytics.SPECS.items():
            with self.subTest(sid=sid):
                self.assertEqual(version, pins[distribution])
                self.assertEqual(version, locked[distribution.lower()])

    def test_fixtures_validate_and_unknown_fields_fail_closed(self):
        for sid, (operation, _, _) in local_analytics.SPECS.items():
            local_runtime.validate(sid, operation, CASES[sid])
            for field in ('shell', 'url', 'path', 'model', 'token', 'callback', 'tenant', 'python'):
                with self.subTest(service=sid, field=field), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, operation, dict(CASES[sid], **{field: 'forbidden'}))
            for dataset in ('production', '', None):
                with self.subTest(service=sid, dataset=dataset), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, operation, dict(CASES[sid], dataset=dataset))
            with self.subTest(service=sid, case='wrong operation'), self.assertRaises(VerdugoError):
                local_runtime.validate(sid, 'shell.run', CASES[sid])

    def test_out_of_bounds_inputs_are_rejected(self):
        bad = {
            'networkx': {'edges': [['a', 'b', 'c']]},
            'statsmodels': {'values': [1.0] * 12},
            'polars': {'currency': 'BTC'},
            'ibis': {'rows': []},
            'sqlglot': {'dialect': 'oracle-plsql'},
            'faker': {'dataset': 'real'},
            'pandera': {'schema': {'x': {'type': 'object', 'nullable': False}}},
            'datasketch': {'threshold': 0.1},
            'h3': {'points': [[91.0, 0.0]]},
            'lifelines': {'observed': [2] * 12},
            'pyod': {'contamination': 0.9},
            'river': {'values': [float('nan')] * 40},
            'numpy-financial': {'cashflows_minor': [1.5, 2.5]},
            'nashpy': {'payoffs_column': [[1, 2, 3], [4, 5, 6]]},
            'pymcdm': {'weights': [0.5, 0.4, 0.4]},
            'mlxtend': {'min_support': 0.001},
            'arrow': {'rows': [{'a': {'nested': 1}}]},
            'markitdown': {'html': '<!DOCTYPE html [<!ENTITY x "y">]><p>&x;</p>'},
            'great-tables': {'rows': [{'a': 1}, {'b': 2}]},
            'spacy': {'language': 'xx'},
            'parsedmarc': {'xml': '<!DOCTYPE feedback SYSTEM "http://example.invalid/x.dtd"><feedback/>'},
            'shap': {'train_y': [1] * 60},
            'statsforecast': {'season_length': 40},
            'opendp': {'epsilon': 0},
            'splink': {'records': [{'id': 'a'}, {'id': 'a'}]},
            'advertools': {'match_types': ['Negative']},
            'dnstwist': {'domain': 'https://example.com/path'},
        }
        self.assertEqual(set(bad), set(local_analytics.SPECS))
        for sid, change in bad.items():
            with self.subTest(sid=sid), self.assertRaises(VerdugoError):
                local_runtime.validate(sid, local_analytics.SPECS[sid][0], dict(copy.deepcopy(CASES[sid]), **change))

    def test_template_starts_disabled_with_exact_versions(self):
        services = template('nexus')['tenants']['nexus']['services']
        for sid, (_, _, version) in local_analytics.SPECS.items():
            cfg = services[sid]
            self.assertEqual((False, False, False, version),
                             (cfg['enabled'], cfg['license_reviewed'], cfg['runtime_reviewed'], cfg['version']))

    def test_engine_fails_closed_without_review_or_installation(self):
        config = template('nexus')
        cfg = config['tenants']['nexus']['services']['opendp']
        command = {'service': 'opendp', 'operation': 'count.privatize', 'params': CASES['opendp'], 'key': 'v017-1'}
        engine = Engine(':memory:', config)
        try:
            with self.assertRaisesRegex(VerdugoError, 'Integration disabled'):
                engine.execute(command, True)
            cfg.update(enabled=True, license_reviewed=True)
            with self.assertRaisesRegex(VerdugoError, 'Local resource and privacy review required'):
                engine.execute(command, True)
            cfg.update(runtime_reviewed=True, version='latest')
            with self.assertRaises(VerdugoError):
                engine.execute(command, True)
            cfg.update(version=local_analytics.SPECS['opendp'][2])
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('VERDUGO_ANALYTICS_PYTHON', None)
                with patch.object(runtime_profile, 'versions', return_value={'opendp': None}):
                    with self.assertRaisesRegex(VerdugoError, 'Missing or mismatched local distribution'):
                        engine.execute(command, True)
        finally:
            engine.close()

    def test_analytics_services_use_their_own_administrator_profile(self):
        for sid in local_analytics.SPECS:
            self.assertEqual('VERDUGO_ANALYTICS_PYTHON', runtime_profile.PROFILE_ENV[sid])
        self.assertEqual('VERDUGO_RAGAS_PYTHON', runtime_profile.PROFILE_ENV['ragas'])
        self.assertNotIn('duckdb', runtime_profile.PROFILE_ENV)
        for value in ('python', '../venv/bin/python', '/tmp/x/bin/bash', ''):
            with self.subTest(value=value), patch.dict(os.environ, {'VERDUGO_ANALYTICS_PYTHON': value}):
                with self.assertRaises(VerdugoError):
                    runtime_profile.interpreter('polars')

    def test_implementation_digest_covers_analytics_module(self):
        original = Path.read_bytes

        def changed(path):
            content = original(path)
            return content + b'\n# modified' if path.name == 'local_analytics.py' else content
        before = local_runtime.implementation_digest()
        with patch.object(Path, 'read_bytes', changed):
            self.assertNotEqual(before, local_runtime.implementation_digest())


if __name__ == '__main__':
    unittest.main()
