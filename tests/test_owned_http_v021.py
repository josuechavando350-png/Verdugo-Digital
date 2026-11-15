import json
import unittest
from verdugo import local_owned_http as m
from verdugo.common import VerdugoError
class OwnedHttpContracts(unittest.TestCase):
 def test_destinations_credentials_ports_and_commands_are_not_caller_controlled(self):
  cases={'siteone-crawler':{'dataset':'demo','pages':[{'id':'root','title':'Title','links':[]}]},'sherlock':{'dataset':'demo','secret_text':json.dumps([{'id':'case','status':200,'text':'Text','mode':'message','marker':'Missing'}])}}
  for sid,p in cases.items():
   op=m.SPECS[sid][0];m.validate(sid,op,p)
   for key in ['url','port','hostname','token','username','command','proxy','headers']:
    with self.assertRaises(VerdugoError):m.validate(sid,op,p|{key:'forbidden'})
  for link in ['https://example.com','../escape','/etc/passwd','x?query=1']:
   with self.assertRaises(VerdugoError):m.validate('siteone-crawler','pages.crawl',{'dataset':'demo','pages':[{'id':'root','title':'Title','links':[link]}]})
 def test_original_checker_accepts_only_bounded_response_modes_and_shapes(self):
  base={'id':'case','status':200,'text':'Text','mode':'message','marker':'Missing'}
  for change in [{'mode':'response_url'},{'status':True},{'status':302},{'text':'a'*1501},{'headers':{}},{'request_method':'POST'}]:
   with self.assertRaises(VerdugoError):m.validate('sherlock','responses.classify',{'dataset':'demo','secret_text':json.dumps([base|change])})
