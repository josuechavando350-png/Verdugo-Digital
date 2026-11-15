"""Bounded scenario comparability and original workflow provenance."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_flow666 as sdk, objectives
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests_runtime'))
from flow666_fixtures import CASES


class Flow666Tests(unittest.TestCase):
    def test_scenarios_use_conditional_dominance_and_preserve_equal_alternatives(self):
        plans=[objectives.plan(g) for g in CASES['griptape']['goals']]
        r=sdk.compare_plans(plans)
        self.assertEqual([0],r['pareto_nondominated_indices'])
        self.assertFalse(r['real_market_optimality_proven'])
        self.assertEqual([0,1],sdk.compare_plans([plans[0],plans[0]])['pareto_nondominated_indices'])

    def test_different_currencies_targets_or_time_windows_are_not_compared(self):
        for key,value in [('currency','USD'),('horizon_days',31),('target_clients',21)]:
            p=copy.deepcopy(CASES['griptape']);p['goals'][1][key]=value
            with self.assertRaises(VerdugoError):sdk.validate('griptape','objective.scenarios',p)

    def test_no_caller_code_model_callback_or_implicit_boolean_is_accepted(self):
        for sid,params in CASES.items():
            sdk.validate(sid,sdk.SPECS[sid][0],params)
            for key,value in [('code','danger'),('callback','function'),('model','remote'),('dataset','real')]:
                with self.subTest(service=sid,key=key),self.assertRaises(VerdugoError):
                    sdk.validate(sid,sdk.SPECS[sid][0],dict(params,**{key:value}))
        with self.assertRaises(VerdugoError):
            sdk.validate('beeai-framework','review.route',dict(CASES['beeai-framework'],budget_ok=1))

    def test_source_contract_matches_registry_and_changed_modules_fail(self):
        registry={r['id']:r for r in read_registry()['records']}
        d=json.loads(sdk.CONTRACT.read_text());self.assertEqual(set(sdk.SPECS),{r['id'] for r in d['records']})
        for r in d['records']:
            self.assertEqual(registry[r['id']]['commit_sha'],r['commit'])
            self.assertEqual(sdk.SPECS[r['id']][2],r['version'])
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'altered.py';path.write_text('# changed')
                with patch.object(sdk.metadata,'distribution') as dist:
                    dist.return_value.locate_file.return_value=path
                    with self.assertRaises(VerdugoError):sdk.verify_source(r['id'])
