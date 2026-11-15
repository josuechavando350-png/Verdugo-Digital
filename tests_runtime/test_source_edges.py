import copy
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import closing
from verdugo import local_runtime
from verdugo.engine import Engine
from verdugo.__main__ import template
from source_fixtures import CASES,maps_payload

class SourceEdges(unittest.TestCase):
 def test_original_parser_failure_and_equal_sample_comparison(self):
  selected=set(os.getenv('VERDUGO_RUNTIME_SERVICES','').split(','))
  if not set(CASES)<=selected:self.skipTest('Other runtime group selected')
  config=template('nexus')
  for sid in CASES:config['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True)
  with tempfile.TemporaryDirectory() as temp,closing(Engine(Path(temp)/'state.db',config)) as e:
   bad=CASES['google-maps-scraper']|{'secret_text':maps_payload(title='')}
   result=e.execute({'service':'google-maps-scraper','operation':'places.inspect','params':bad,'key':'missing-title'},True)
   self.assertEqual('failed',result['state']);self.assertNotIn('records',result)
   p=CASES['tinytroupe']|{'treatment':CASES['tinytroupe']['control']}
   result=e.execute({'service':'tinytroupe','operation':'experiments.compare','params':p,'key':'same-means'},True)
   self.assertEqual('succeeded',result['state'],result);out=result['result']['result']
   self.assertEqual(0,out['mean_difference']);self.assertEqual(1,out['p_value']);self.assertFalse(out['significant'])
   self.assertNotIn('Private Maps Place','\n'.join(e.db.iterdump()))
