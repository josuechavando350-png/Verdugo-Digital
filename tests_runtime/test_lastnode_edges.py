import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import closing
from verdugo import local_lastnode
from verdugo.engine import Engine
from verdugo.__main__ import template
class LastNodeEdges(unittest.TestCase):
 def setUp(self):
  if 'landscape-app' not in os.getenv('VERDUGO_RUNTIME_SERVICES','').split(','):self.skipTest('Other runtime group selected')
 def test_original_validation_preserves_invalid_repo_and_date(self):
  c=template('nexus');c['tenants']['nexus']['services']['landscape-app'].update(enabled=True,license_reviewed=True,runtime_reviewed=True)
  with tempfile.TemporaryDirectory() as d,closing(Engine(Path(d)/'state.db',c)) as e:
   out=e.execute({'service':'landscape-app','operation':'landscape.validate','params':{'dataset':'demo','secret_text':json.dumps([{'name':'Private invalid project','repo_url':'https://github.com/example/','joined':'not-a-date'}])},'key':'invalid'},True)
   self.assertEqual('succeeded',out['state'],out);r=out['result']['result'];self.assertFalse(r['schema_valid']);self.assertEqual(2,r['fatal_errors']);self.assertNotIn('Private invalid project','\n'.join(e.db.iterdump()))
 def test_original_mcp_browser_snapshot_probe(self):
  # This host may forbid Unix sockets; CI must execute the real browser, not skip.
  home=local_lastnode.root();worker=Path(local_lastnode.__file__).with_name('_playwright_mcp_worker.cjs')
  with tempfile.TemporaryDirectory() as work:
   env={'HOME':work,'TMPDIR':work,'PATH':os.defpath,'LANG':'C.UTF-8','VERDUGO_MCP_PROBE':'1',local_lastnode.ENV:str(home)}
   p={'title':'Supplied document','headings':[{'level':1,'text':'Heading'},{'level':2,'text':'Detail'}],'buttons':['Book']}
   result=subprocess.run([str(home/'bin/node'),str(worker)],input=json.dumps(p),env=env,cwd=work,text=True,capture_output=True,timeout=60)
   self.assertEqual(0,result.returncode,result.stderr[-6000:]);r=json.loads(result.stdout);self.assertEqual(2,r['headings']);self.assertEqual([1,2],r['heading_levels']);self.assertEqual(1,r['buttons']);self.assertTrue(r['browser_started']);self.assertFalse(r['remote_page_fetched'])
