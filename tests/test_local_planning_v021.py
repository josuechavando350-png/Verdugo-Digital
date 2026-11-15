import copy
import unittest
from pathlib import Path
import sys
from verdugo import local_planning,local_runtime
from verdugo.common import VerdugoError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from planning_fixtures import CASES

class PlanningContracts(unittest.TestCase):
 def test_no_caller_code_models_network_or_files(self):
  for sid,p in CASES.items():
   op=local_planning.SPECS[sid][0];local_runtime.validate(sid,op,p)
   for key in ('code','url','path','model','token','tenant','function','server_names','yaml','colang','imports'):
    with self.subTest(service=sid,field=key),self.assertRaises(VerdugoError):
     local_runtime.validate(sid,op,dict(p,**{key:'forbidden'}))

 def test_dialogue_injection_duplicates_and_size(self):
  for rows in ([{'id':'a','request':'hello\nimport malicious','response':'x'}],
               [CASES['nemo-guardrails']['flows'][0]]*2,[],
               [{'id':'a','request':'x'*501,'response':'y'}]):
   with self.assertRaises(VerdugoError):
    local_runtime.validate('nemo-guardrails','dialogue.compile',{'dataset':'demo','flows':rows})

 def test_campaign_tool_uses_existing_financial_input_constraints(self):
  p=copy.deepcopy(CASES['mcp-agent']);p['rows'][0]['spend_minor']=-1
  with self.assertRaises(VerdugoError):local_runtime.validate('mcp-agent','campaigns.tool',p)
