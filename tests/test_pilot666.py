"""Fail-closed pilot contracts; original SDK execution is in acceptance CI."""
import copy
from contextlib import closing
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

from verdugo import local_pilot666, local_runtime, objectives, runtime_profile
from verdugo.__main__ import template
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.registry666 import read_registry

ROOT = Path(__file__).resolve().parents[1]


class Pilot666Tests(unittest.TestCase):
    def setUp(self):
        self.step = json.loads((ROOT/'examples/kernel666.synthetic.json').read_text())['steps'][0]
        self.params = self.step['params']

    def test_only_explicit_synthetic_fixed_function_is_supported(self):
        local_runtime.validate('semantic-kernel', 'objective.plan', self.params)
        mutations = [lambda p:p.update(dataset='real'), lambda p:p.update(model='remote'),
                     lambda p:p.update(code='arbitrary'), lambda p:p['goal'].update(dataset='real'),
                     lambda p:p.pop('dataset')]
        for mutate in mutations:
            p = copy.deepcopy(self.params)
            mutate(p)
            with self.assertRaises(VerdugoError):
                local_runtime.validate('semantic-kernel', 'objective.plan', p)
        with self.assertRaises(VerdugoError):
            local_pilot666.validate('semantic-kernel', 'agent.run', self.params)

    def test_runtime_and_license_reviews_cannot_be_skipped(self):
        cfg = template('nexus')
        with closing(Engine(':memory:', cfg)) as e:
            cmd = {k:v for k,v in self.step.items() if k != 'id'} | {'key':'pilot'}
            with self.assertRaises(VerdugoError):
                e.plan(cmd)
            scfg = cfg['tenants']['nexus']['services']['semantic-kernel']
            scfg.update(enabled=True, license_reviewed=True, version='1.47.0')
            with self.assertRaises(VerdugoError):
                e.plan(cmd)
            scfg['runtime_reviewed'] = True
            with patch.object(local_runtime, 'installed', return_value={
                    'version_matches':False, 'distribution':'semantic-kernel'}):
                with self.assertRaises(VerdugoError):
                    e.plan(cmd)

    def test_source_contract_and_runtime_version_are_bound_to_registered_pin(self):
        contract = json.loads((ROOT/'sources/contracts-kernel666.json').read_text())
        registered = next(r for r in read_registry()['records'] if r['id']=='semantic-kernel')
        self.assertEqual(registered['commit_sha'], contract['source_commit'])
        self.assertEqual(local_pilot666.SPECS['semantic-kernel'][2], contract['version'])
        self.assertEqual('VERDUGO_KERNEL666_PYTHON', runtime_profile.PROFILE_ENV['semantic-kernel'])
        for row in contract['source_files']:
            self.assertEqual(contract['source_commit'], row['commit_sha'])
            self.assertRegex(row['blob_sha'], r'^[0-9a-f]{40}$')
            self.assertRegex(row['sha256'], r'^[0-9a-f]{64}$')

    def test_changes_to_goal_algorithm_invalidate_local_plan_fingerprint(self):
        before = local_runtime.implementation_digest()
        original = Path.read_bytes
        def changed(path):
            value = original(path)
            return value+b'\n# changed algorithm' if path == Path(objectives.__file__) else value
        with patch.object(Path, 'read_bytes', changed):
            self.assertNotEqual(before, local_runtime.implementation_digest())

    def test_same_version_with_different_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'altered.py'
            path.write_text('# an unrelated wheel with the same version')
            with patch.object(local_pilot666.metadata, 'distribution') as distribution:
                distribution.return_value.locate_file.return_value = path
                with self.assertRaises(VerdugoError):
                    local_pilot666.verify_installed_source()
