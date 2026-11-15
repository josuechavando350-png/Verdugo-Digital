"""Fail-closed boundaries for deterministic graph and formal process adapters."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_planning666 as planning, local_volt666 as volt, local_manus666 as manus, local_memory666 as memory, local_monty666 as monty, local_browserstate666 as browserstate
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests_runtime'))
from planning666_fixtures import CASES


class Planning666Tests(unittest.TestCase):
    def test_only_fixed_synthetic_inputs_no_code_models_or_commands(self):
        for sid, params in CASES.items():
            module = browserstate if sid == 'playwright-python' else monty if sid == 'monty' else memory if sid == 'servers' else manus if sid == 'openmanus' else volt if sid == 'voltagent' else planning
            module.validate(sid, module.SPECS[sid][0], params)
            for key, value in [('code', 'run'), ('model', 'remote'), ('url', 'https://example.invalid'),
                               ('sequence', ['shell']), ('dataset', 'real')]:
                with self.subTest(sid=sid, key=key), self.assertRaises(VerdugoError):
                    module.validate(sid, module.SPECS[sid][0], dict(params, **{key: value}))

    def test_hypothetical_review_requires_boolean_and_is_not_an_approval(self):
        for value in (1, 'true', None, {}):
            with self.assertRaises(VerdugoError):
                planning.validate('unified-planning', 'sequence.validate',
                                  dict(CASES['unified-planning'], hypothetical_review_available=value))
        with self.assertRaises(VerdugoError):
            planning.validate('unified-planning', 'sequence.validate',
                              dict(CASES['unified-planning'], sequence=['plan'] * 9))

    def test_exposure_cannot_be_negative_boolean_or_below_clients(self):
        for key, value in [('observed_contacts', 1), ('observed_clients', -1),
                           ('target_clients', True), ('simulated_median', 20001)]:
            with self.assertRaises(VerdugoError):
                volt.validate('voltagent', 'measurement.review', dict(CASES['voltagent'], **{key: value}))
        for contacts in (True, -1, 20001):
            p = copy.deepcopy(CASES['harness-sdk']); p['actions'][0]['contacts'] = contacts
            with self.assertRaises(VerdugoError): planning.validate('harness-sdk', 'limits.parallel', p)

    def test_sources_match_registry_and_altered_installed_modules_fail_closed(self):
        registry = {r['id']: r for r in read_registry()['records']}
        for r in json.loads(planning.CONTRACT.read_text())['records']:
            self.assertEqual(registry[r['id']]['commit_sha'], r['commit'])
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'altered.py'; path.write_text('# altered')
                with patch.object(planning.metadata, 'distribution') as dist:
                    dist.return_value.locate_file.return_value = path
                    with self.assertRaises(VerdugoError): planning.verify_source(r['id'])
        r = json.loads(volt.CONTRACT.read_text())
        self.assertEqual(registry['voltagent']['commit_sha'], r['commit'])
        self.assertEqual(10, r['source_map_files_verified'])
        self.assertEqual('24.22.1', r['node_version'])

    def test_node_runtime_with_tampered_lock_or_bundle_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); (home/'bin').mkdir(); (home/'bin/node').write_bytes(b'not-node')
            (home/'bin/node').chmod(0o700); (home/'package-lock.json').write_text('{}')
            with patch.dict('os.environ', {volt.ENV: str(home)}):
                self.assertFalse(volt.runtime_state('voltagent')['version_matches'])
