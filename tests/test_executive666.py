"""Executive SDK validation and budget findings never authorize execution."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile

from verdugo import local_executive666 as sdk, local_runtime
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests_runtime'))
from executive666_fixtures import CASES


class Executive666Tests(unittest.TestCase):
    def test_fixed_schema_rejects_real_data_models_and_dynamic_tools(self):
        for sid, params in CASES.items():
            sdk.validate(sid, sdk.SPECS[sid][0], params)
            for key, value in [('model','remote'),('tool','shell'),('dataset','real'),('url','https://example.invalid')]:
                with self.subTest(service=sid, field=key), self.assertRaises(VerdugoError):
                    sdk.validate(sid, sdk.SPECS[sid][0], dict(params, **{key:value}))

    def test_budget_rejection_and_acceptance_do_not_grant_approval(self):
        p = copy.deepcopy(CASES['ag2'])
        for budget, accepted in [(0,False),(59,False),(60,True),(61,True)]:
            p['budget_minor'] = budget
            r = sdk.check_actions(p)
            self.assertEqual(accepted, r['within_budget'])
            self.assertEqual(accepted, r['feasible_under_declared_limits'])
            self.assertTrue(r['operator_approval_still_required'])
            self.assertFalse(r['external_execution_authorized'])

    def test_total_contact_limit_can_fail_even_when_each_channel_is_valid(self):
        p = copy.deepcopy(CASES['ag2'])
        p['actions'] = [{'channel':c,'contacts':20000,'cost_per_contact_minor':0} for c in ('referral','content')]
        sdk.validate('ag2','actions.check',p)
        r = sdk.check_actions(p)
        self.assertTrue(r['within_budget'])
        self.assertFalse(r['within_contact_limit'])
        self.assertFalse(r['feasible_under_declared_limits'])

    def test_duplicate_channels_negative_cost_and_oversized_counts_are_rejected(self):
        for change in [('contacts',True),('contacts',20001),('cost_per_contact_minor',-1),('channel','arbitrary')]:
            p=copy.deepcopy(CASES['ag2']);p['actions'][0][change[0]]=change[1]
            with self.assertRaises(VerdugoError):sdk.validate('ag2','actions.check',p)
        p=copy.deepcopy(CASES['ag2']);p['actions'].append(copy.deepcopy(p['actions'][0]))
        with self.assertRaises(VerdugoError):sdk.validate('ag2','actions.check',p)

    def test_contract_matches_registry_and_each_installed_module_is_checked(self):
        registry={r['id']:r for r in read_registry()['records']}
        d=json.loads(sdk.CONTRACT.read_text())
        self.assertEqual(set(sdk.SPECS), {r['id'] for r in d['records']})
        for r in d['records']:
            self.assertEqual(registry[r['id']]['commit_sha'],r['commit'])
            self.assertEqual(sdk.SPECS[r['id']][2],r['version'])
            for f in r['files']:
                self.assertRegex(f['blob_sha'],r'^[0-9a-f]{40}$')
                self.assertRegex(f['sha256'],r'^[0-9a-f]{64}$')
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'altered.py';path.write_text('# altered')
                with patch.object(sdk.metadata,'distribution') as dist:
                    dist.return_value.locate_file.return_value=path
                    with self.assertRaises(VerdugoError):sdk.verify_source(r['id'])
