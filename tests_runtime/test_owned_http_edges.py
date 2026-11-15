import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import closing
from verdugo.__main__ import template
from verdugo.engine import Engine
from owned_http_fixtures import CASES,RESPONSES
class OwnedHttpEdges(unittest.TestCase):
 def test_crawler_does_not_count_unreachable_page_and_checker_uses_body(self):
  if not set(CASES)<=set(os.getenv('VERDUGO_RUNTIME_SERVICES','').split(',')):self.skipTest('Other runtime group selected')
  c=template('nexus')
  for sid in CASES:c['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True)
  with tempfile.TemporaryDirectory() as d,closing(Engine(Path(d)/'state.db',c)) as e:
   p={'dataset':'demo','pages':[{'id':'root','title':'Root','links':[]},{'id':'unreachable','title':'Unreachable','links':[]}]}
   out=e.execute({'service':'siteone-crawler','operation':'pages.crawl','params':p,'key':'unreachable'},True)
   self.assertEqual('succeeded',out['state'],out);r=out['result']['result'];self.assertEqual(1,r['visited']);self.assertEqual(2,r['pages_in_input']);self.assertEqual(0,r['missing_pages'])
   p={'dataset':'demo','secret_text':json.dumps([RESPONSES[2]|{'text':'Private owned brand exists'}])}
   out=e.execute({'service':'sherlock','operation':'responses.classify','params':p,'key':'message-present'},True)
   self.assertEqual('succeeded',out['state'],out);self.assertEqual('Claimed',out['result']['result']['results'][0]['classification']);self.assertNotIn('Private owned brand exists','\n'.join(e.db.iterdump()))
