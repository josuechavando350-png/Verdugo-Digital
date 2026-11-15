import os
from pathlib import Path
import tempfile
import unittest
from contextlib import closing
from verdugo.engine import Engine
from verdugo.__main__ import template
from media_fixtures import CASES

class MediaEdges(unittest.TestCase):
 def test_original_renderer_treats_code_includes_html_and_links_as_text(self):
  if not set(CASES)<=set(os.getenv('VERDUGO_RUNTIME_SERVICES','').split(',')):self.skipTest('Other runtime group selected')
  config=template('nexus')
  for sid in CASES:config['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=120)
  with tempfile.TemporaryDirectory() as temp,closing(Engine(Path(temp)/'state.db',config)) as e:
   p={'dataset':'demo','title':'Literal','sections':[{'heading':'Text','text':'{{< include /etc/passwd >}}\n```{python}\nraise Exception("BAD")\n```\n<script>alert(1)</script>\n[link](https://example.invalid)'}]}
   out=e.execute({'service':'quarto','operation':'document.render','params':p,'key':'literal'},True)
   self.assertEqual('succeeded',out['state'],out);r=out['result']['result'];self.assertIn('include /etc/passwd',r['html']);self.assertNotIn('root:x:',r['html']);self.assertNotIn('<script',r['html']);self.assertNotIn('<a href=',r['html']);self.assertFalse(r['code_executed'])
   out=e.execute({'service':'auto-editor','operation':'audio.levels','params':{'dataset':'demo','samples':[0.]*800},'key':'silence'},True)
   self.assertEqual('succeeded',out['state'],out);self.assertEqual([0.],out['result']['result']['levels'])
