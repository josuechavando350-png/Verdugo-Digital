"""Arithmetic counterexamples, absent denominators and unavailable SDK honesty."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile

from verdugo import local_reasoning666 as sdk, local_runtime
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests_runtime'))
from reasoning666_fixtures import CASES


class Reasoning666Tests(unittest.TestCase):
    def test_counterexample_is_reported_without_claiming_general_truth(self):
        r=sdk.check_claims(CASES['langroid'])
        self.assertEqual(['supported','supported','contradicted'],[x['verdict'] for x in r['claims']])
        self.assertFalse(r['semantic_truth_verified'])
        self.assertFalse(r['net_profit_verified'])
        self.assertFalse(r['external_execution_authorized'])

    def test_empty_exposure_is_insufficient_not_success(self):
        p=copy.deepcopy(CASES['langroid']);p['before']['contacts']=p['before']['clients']=0
        sdk.validate('langroid','claims.check',p)
        self.assertEqual(['insufficient_data','insufficient_data','contradicted'],
                         [x['verdict'] for x in sdk.check_claims(p)['claims']])

    def test_rate_comparison_remains_exact_below_float_resolution(self):
        p=copy.deepcopy(CASES['langroid'])
        p['before'].update(contacts=10**9,clients=10**9-1)
        p['after'].update(contacts=10**9-1,clients=10**9-2)
        sdk.validate('langroid','claims.check',p)
        self.assertEqual('contradicted',sdk.check_claims(p)['claims'][0]['verdict'])

    def test_schema_denies_models_free_text_privacy_fields_and_unknown_claims(self):
        mutations=[lambda p:p.update(dataset='real'),lambda p:p.update(model='remote'),
                   lambda p:p.update(client_name='private'),lambda p:p.update(claims=['arbitrary']),
                   lambda p:p.update(claims=['conversion_rate_increased']*2),
                   lambda p:p['after'].update(clients=101),lambda p:p['after'].update(contacts=True)]
        for mutate in mutations:
            p=copy.deepcopy(CASES['langroid']);mutate(p)
            with self.assertRaises(VerdugoError):sdk.validate('langroid','claims.check',p)

    def test_metagpt_stays_pending_after_failed_original_dependency_resolution(self):
        self.assertNotIn('metagpt',local_runtime.SPECS)
        d=json.loads(sdk.CONTRACT.read_text())
        meta=next(r for r in d['records'] if r['id']=='metagpt')
        self.assertEqual('blocked_dependency_resolution',meta['runtime_state'])
        self.assertFalse(meta['blocker']['adapter_implemented'])
        self.assertFalse(meta['blocker']['workaround_applied'])

    def test_reviewed_source_is_bound_to_registry_and_changed_install_fails(self):
        d=json.loads(sdk.CONTRACT.read_text())
        registered={r['id']:r for r in read_registry()['records']}
        for record in d['records']:
            self.assertEqual(registered[record['id']]['commit_sha'],record['commit'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'altered.py';path.write_text('# changed')
            with patch.object(sdk.metadata,'distribution') as dist:
                dist.return_value.locate_file.return_value=path
                with self.assertRaises(VerdugoError):sdk.verify_source()

    def test_missing_or_corrupt_offline_tokenizer_fails_before_sdk_import(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp, patch.object(sdk,'tokenizer_directory',return_value=Path(tmp)):
            with self.assertRaises(VerdugoError):sdk.verify_tokenizer()
            (Path(tmp)/hashlib.sha1(sdk.TOKENIZER_URL.encode()).hexdigest()).write_bytes(b'corrupt')
            with self.assertRaises(VerdugoError):sdk.verify_tokenizer()
