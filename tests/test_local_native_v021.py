import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_native, local_runtime
from verdugo.common import VerdugoError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from native_fixtures import CASES


class NativeContracts(unittest.TestCase):
    def test_missing_runtime_is_unavailable_without_executing(self):
        with patch.dict(os.environ,{local_native.ENV:'/nonexistent/verdugo-native'}), patch('subprocess.run',side_effect=AssertionError('Executed')):
            for sid in CASES:self.assertFalse(local_native.runtime_state(sid)['version_matches'])

    def test_administrator_paths_reject_relative_and_writable_roots(self):
        for root in ('relative','/tmp/../root','/tmp/x\n'):
            with patch.dict(os.environ,{local_native.ENV:root}),self.assertRaises(VerdugoError):local_native.root()
        with tempfile.TemporaryDirectory() as temp:
            Path(temp).chmod(0o777)
            with patch.dict(os.environ,{local_native.ENV:temp}),self.assertRaises(VerdugoError):local_native.root()

    def test_deep_or_foreign_schema_and_network_paths_rejected(self):
        changes={'site-md':{'html':'<!ENTITY x SYSTEM "https://outside.invalid/entity">'},
                 'seo-graph':{'host':'user:password@host.invalid/path'},
                 'structured-data-validator':{'graph':{'@context':'https://outside.invalid','@graph':[]}}}
        # The HTML adapter rejects XML entity declarations.
        for sid,diff in changes.items():
            with self.subTest(service=sid),self.assertRaises(VerdugoError):
                local_runtime.validate(sid,local_native.SPECS[sid][0],dict(CASES[sid],**diff))


def case(sid):
    def run(self):
        op=local_native.SPECS[sid][0];local_runtime.validate(sid,op,CASES[sid])
        for key in ('url','path','shell','command','javascript','code','callback','model','token','tenant','package'):
            with self.assertRaises(VerdugoError):local_runtime.validate(sid,op,dict(CASES[sid],**{key:'forbidden'}))
    return run


for sid in CASES:setattr(NativeContracts,'test_contract_'+sid.replace('-','_'),case(sid))
