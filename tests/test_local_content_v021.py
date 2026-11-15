import copy
from pathlib import Path
import sys
import unittest
from verdugo import local_content, local_runtime
from verdugo.common import VerdugoError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from content_fixtures import CASES


class ContentContracts(unittest.TestCase):
    def test_invalid_spans_dates_groups_and_budgets(self):
        changes={'chronos':{'values':[float('nan')]},'graphiti':{'items':['a','a']},
                 'gliner':{'predicted':[[{'label':'ORG','start':5,'end':2}]]},
                 'openbb':{'rows':[dict(CASES['openbb']['rows'][0],high=5)]},
                 'people-also-ask':{'html':'x'*33000},'jobspy':{'html':'<!ENTITY x SYSTEM "https://example.invalid">'}}
        for sid,diff in changes.items():
            with self.subTest(service=sid),self.assertRaises((VerdugoError,ValueError)):
                local_runtime.validate(sid,local_content.SPECS[sid][0],dict(CASES[sid],**diff))


def case(sid):
    def run(self):
        op=local_content.SPECS[sid][0];local_runtime.validate(sid,op,CASES[sid])
        for key in ('url','path','shell','code','callback','model','token','tenant','package'):
            with self.assertRaises(VerdugoError):local_runtime.validate(sid,op,dict(CASES[sid],**{key:'forbidden'}))
    return run


for sid in CASES:setattr(ContentContracts,'test_contract_'+sid.replace('-','_'),case(sid))
