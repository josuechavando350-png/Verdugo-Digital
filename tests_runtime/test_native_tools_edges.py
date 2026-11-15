"""Negative and boundary evidence from the original JVM programs, not mocks."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import closing
from verdugo import local_native_tools as nt
from verdugo.__main__ import template
from verdugo.engine import Engine
from native_tools_fixtures import CASES

class NativeToolsEdges(unittest.TestCase):
 def setUp(self):
  selected=set(os.getenv('VERDUGO_RUNTIME_SERVICES','').split(','))
  if not set(nt.SPECS)<=selected:self.skipTest('Other runtime group selected')
  if any(not nt.runtime_state(s)['version_matches'] for s in nt.SPECS):self.fail('Missing required original native tools')
 def test_invalid_spec_is_false_and_arx_and_merge_handle_boundary_cases(self):
  cfg=template('nexus')
  for sid in nt.SPECS:cfg['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=60)
  spec=copy.deepcopy(CASES['openapi-generator']);d=json.loads(spec['secret_text']);del d['paths']['/status']['get']['responses'];spec['secret_text']=json.dumps(d)
  arx=CASES['arx']|{'secret_text':json.dumps([{'age':30,'zipcode':'12345'}]*4),'k':4}
  with tempfile.TemporaryDirectory() as temp,closing(Engine(Path(temp)/'state.db',cfg)) as e:
   for sid,p,expected in [('openapi-generator',spec,{'schema_valid':False,'validation_errors':1}),('arx',arx,{'minimum_class_size':4,'equivalence_classes':1}),('cc-webgraph',CASES['cc-webgraph']|{'adjacencies':[[],[]]},{'counts':[]})]:
    reply=e.execute({'service':sid,'operation':nt.SPECS[sid][0],'params':p,'key':'native-edge-'+sid},True)
    self.assertEqual('succeeded',reply['state'],reply)
    out=reply['result']['result']
    for key,value in expected.items():self.assertEqual(value,out[key])
   self.assertNotIn('PrivateSuppliedSpec','\n'.join(e.db.iterdump()))
 def test_native_java_policy_rejects_network_and_child_processes(self):
  source='''public class GuardProbe { public static void main(String[] x) throws Exception {
  System.setSecurityManager(new VerdugoJavaWorker.Offline()); int blocked=0;
  try { new java.net.Socket("127.0.0.1",9); } catch(SecurityException e) { blocked++; }
  try { new ProcessBuilder("true").start(); } catch(SecurityException e) { blocked++; }
  if(blocked!=2) throw new AssertionError(); System.out.println("blocked=2"); }}'''
  home=nt.root()
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'GuardProbe.java';path.write_text(source)
   subprocess.run([str(home/'jdk/bin/javac'),'-proc:none','-cp',str(home/'classes'),str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
   result=subprocess.run([str(home/'jdk/bin/java'),'-Djava.security.manager=allow','-cp',temp+os.pathsep+str(home/'classes'),'GuardProbe'],text=True,capture_output=True,timeout=15,check=True)
   self.assertEqual('blocked=2',result.stdout.strip())
