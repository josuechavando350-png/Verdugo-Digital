from contextlib import closing
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from verdugo import local_cli, local_pycli, local_runtime, workflow
from verdugo.__main__ import template
from verdugo.common import VerdugoError
from verdugo.engine import Engine
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from cli_fixtures import CASES


class CliContracts(unittest.TestCase):
    def test_missing_or_tampered_binary_fails_closed(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{local_cli.ENV:d}):
            home=Path(d);(home/'bin').mkdir();binary=home/'bin/vale';binary.write_bytes(b'not executable');binary.chmod(0o755)
            metadata={'binaries':{'vale':{'source_commit':local_cli.SPECS['vale'][2],'sha256':'0'*64}}}
            (home/'manifest.json').write_text(json.dumps(metadata))
            with patch('subprocess.run',side_effect=AssertionError('Executed')):
                self.assertFalse(local_cli.runtime_state('vale')['version_matches'])
                self.assertFalse(local_cli.runtime_state('sops')['version_matches'])
                metadata['binaries']['vale']['sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
                (home/'manifest.json').write_text(json.dumps(metadata))
                self.assertTrue(local_cli.runtime_state('vale')['version_matches'])
                binary.write_bytes(b'changed')
                self.assertFalse(local_cli.runtime_state('vale')['version_matches'])

    def test_bounds_and_option_injection(self):
        invalid={'syft':{'packages':[{'name':'--config','version':'1.2.*'}]},
                 'grype':{'packages':[{'name':'../x','version':'1.2.3'}]},
                 'dnstwist':{'domain':'--registered'},'vale':{'text':'x'*32000},
                 'gitleaks':{'secret_text':''},'restic':{'secret_text':'x'*32000},
                 'sops':{'secret_text':42},'dvc':{'secret_text':[]}}
        for sid,diff in invalid.items():
            with self.subTest(service=sid),self.assertRaises(VerdugoError):
                local_runtime.validate(sid,local_runtime.SPECS[sid][0],dict(CASES[sid],**diff))

    def test_workflow_plan_never_returns_secret_input(self):
        secret='SYNTHETIC-PRIVATE-INPUT-45863'
        config=template('nexus')
        config['tenants']['nexus']['services']['gitleaks'].update(enabled=True,license_reviewed=True,runtime_reviewed=True)
        installed=dict(distribution='cli:gitleaks',expected=local_cli.SPECS['gitleaks'][2],installed=local_cli.SPECS['gitleaks'][2],version_matches=True,extra_distributions={},runtime_binding='test')
        with closing(Engine(':memory:',config)) as e, patch('verdugo.local_cli.runtime_state',return_value=installed):
            spec={'id':'private-plan','steps':[{'id':'scan','service':'gitleaks','operation':'text.scan','params':{'dataset':'demo','secret_text':secret}}]}
            output=workflow.run(e,spec,False)
            self.assertNotIn(secret,json.dumps(output))
            self.assertNotIn(secret,'\n'.join(e.db.iterdump()))


def case(sid):
    def run(self):
        op=local_runtime.SPECS[sid][0];local_runtime.validate(sid,op,CASES[sid])
        for key in ('url','path','shell','command','args','code','callback','token','tenant','database','key_file','remote'):
            with self.assertRaises(VerdugoError): local_runtime.validate(sid,op,dict(CASES[sid],**{key:'forbidden'}))
    return run

for sid in CASES:setattr(CliContracts,'test_contract_'+sid.replace('-','_'),case(sid))
