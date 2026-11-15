import copy
import json
from pathlib import Path
import sys
import unittest
from verdugo import local_source,local_data,local_cli,local_runtime
from verdugo.common import VerdugoError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from source_fixtures import CASES

class SourceFinish(unittest.TestCase):
 def test_import_adaptations_preserve_every_algorithm_byte(self):
  for sid,old,new in [('cua',b'from cua_bench.types import (',b'from verdugo.vendor.cua.types import ('),('tinytroupe',b'from tinytroupe.experimentation import logger',b'import logging\nlogger = logging.getLogger(__name__)')]:
   path=local_source.source_path(sid);original=(path.parent/'original.py').read_bytes()
   self.assertEqual(1,original.count(old));self.assertEqual(original.replace(old,new),path.read_bytes())
 def test_fixed_actions_block_code_network_fields_and_out_of_viewport_coordinates(self):
  for sid,p in CASES.items():
   op=local_runtime.SPECS[sid][0];local_runtime.validate(sid,op,p)
   for key in ('url','command','headers','path','model','tenant'):
    with self.assertRaises(VerdugoError):local_runtime.validate(sid,op,p|{key:'forbidden'})
  p=copy.deepcopy(CASES['cua']);p['actions'][0]['x']=p['width']
  with self.assertRaises(VerdugoError):local_source.validate('cua','actions.normalize',p)
  p['actions']=[{'type':'__import__("os").system("true")'}]
  with self.assertRaises(VerdugoError):local_source.validate('cua','actions.normalize',p)
 def test_inference_requires_review_and_nonconstant_independent_samples(self):
  p=CASES['tinytroupe']
  for change in ({'assumptions_reviewed':False},{'control':[2,2,2]},{'treatment':[1,2]},{'control':[1,True,3]}):
   with self.assertRaises(VerdugoError):local_source.validate('tinytroupe','experiments.compare',p|change)
 def test_nap_rules_return_disagreements_without_private_nap_values(self):
  p=CASES['local-seo-skills'];out=local_data.run('local-seo-skills',p)
  self.assertEqual(['name'],out['listings'][1]['mismatched_fields']);self.assertNotIn('Private',json.dumps(out));self.assertNotIn('+5255',json.dumps(out))
  d=json.loads(p['secret_text']);d['listings'][0]['phone']='5550001111'
  with self.assertRaises(VerdugoError):local_data.validate('local-seo-skills','nap.compare',p|{'secret_text':json.dumps(d)})
