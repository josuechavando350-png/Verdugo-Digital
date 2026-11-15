import copy
import json
import sys
from pathlib import Path
import unittest
from verdugo import local_native_tools as nt
from verdugo.common import VerdugoError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from native_tools_fixtures import CASES

class NativeToolsValidation(unittest.TestCase):
 def test_callers_cannot_supply_executables_flags_destinations_or_paths(self):
  for sid,p in CASES.items():
   nt.validate(sid,nt.SPECS[sid][0],p)
   for key in ('command','args','host','path','query','script','tenant','headers'):
    with self.subTest(service=sid,field=key),self.assertRaises(VerdugoError):nt.validate(sid,nt.SPECS[sid][0],p|{key:'forbidden'})
 def test_private_openapi_input_rejects_external_references_and_ambiguous_json(self):
  for ref in ('file:///etc/passwd','https://example.invalid/spec.json','#','relative.json'):
   p=copy.deepcopy(CASES['openapi-generator']);d=json.loads(p['secret_text']);d['components']={'schemas':{'X':{'$ref':ref}}};p['secret_text']=json.dumps(d)
   with self.assertRaises(VerdugoError):nt.validate('openapi-generator','spec.validate',p)
  for raw in ('{"openapi":"3.0.3","a":1,"a":2}','{"openapi":"3.0.3","a":NaN}','{"openapi":"3.0.3","a":1e999}'):
   with self.assertRaises(VerdugoError):nt.validate('openapi-generator','spec.validate',CASES['openapi-generator']|{'secret_text':raw})
 def test_arx_input_is_bounded_and_unsupported_identifiers_are_rejected(self):
  for k in (True,0,5):
   with self.assertRaises(VerdugoError):nt.validate('arx','groups.anonymize',CASES['arx']|{'k':k})
  p=copy.deepcopy(CASES['arx']);d=json.loads(p['secret_text']);d[0]['name']='private';p['secret_text']=json.dumps(d)
  with self.assertRaises(VerdugoError):nt.validate('arx','groups.anonymize',p)
 def test_sorted_graph_and_fixed_log_encoding_boundaries(self):
  for rows in ([[2,1]],[[True]],[[-1]],[[1]*201]):
   with self.assertRaises(VerdugoError):nt.validate('cc-webgraph','adjacency.merge',CASES['cc-webgraph']|{'adjacencies':rows})
  for value in ('/ok\nmalicious','http://other.invalid','/a?token=private','/"bad'):
   p=copy.deepcopy(CASES['goaccess']);p['events'][0]['path']=value
   with self.assertRaises(VerdugoError):nt.validate('goaccess','requests.summarize',p)
 def test_installer_source_and_runtime_files_are_pinned(self):
  import hashlib
  d=nt.contract();self.assertEqual(set(nt.SPECS),set(d['groups']))
  for name,sha in d['sources'].items():self.assertEqual(sha,hashlib.sha256((nt.SOURCE/name).read_bytes()).hexdigest())
  for group in d['groups'].values():
   self.assertTrue(group)
   for name in group:self.assertIn(name,d['files']);self.assertNotIn('..',Path(name).parts)
