import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from verdugo import local_database as db, local_runtime
from verdugo.common import VerdugoError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from database_fixtures import CASES


class DatabaseContracts(unittest.TestCase):
    def test_only_bounded_operations_not_hosts_or_queries(self):
        for sid, params in CASES.items():
            local_runtime.validate(sid,db.SPECS[sid][0],params)
            for key in ('host','port','sql','cypher','path','command','socket','password','tenant','loopback'):
                with self.subTest(service=sid,key=key), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid,db.SPECS[sid][0],dict(params,**{key:'forbidden'}))

    def test_invalid_graphs_keys_and_vectors_are_rejected_before_execution(self):
        for sid, changes in {
            'valkey': [{'entries':[{'id':'x\nCONFIG','value':1}]}, {'entries':[{'id':'x','value':True}]},
                       {'entries':[{'id':'x','value':1},{'id':'x','value':2}]}],
            'pgvector': [{'query':[0,float('nan'),0]}, {'query':[1,2]}, {'limit':0},
                         {'rows':[{'id':"x');DROP TABLE items;--",'vector':[1,2,3]}]}],
            'apache-age': [{'edges':[{'source':'a','target':'missing'}]},
                           {'edges':[{'source':'a','target':'b'}]*2}, {'nodes':['a','a']},
                           {'nodes':['a','b$MATCH']}],
        }.items():
            for change in changes:
                with self.subTest(service=sid,change=change), self.assertRaises(VerdugoError):
                    db.validate(sid,db.SPECS[sid][0],dict(CASES[sid],**change))

    def test_runtime_and_transport_are_administrator_controlled(self):
        for value in ('relative','/tmp/../other','/tmp/x\n'):
            with patch.dict(os.environ,{db.ENV:value}),self.assertRaises(VerdugoError):
                db.root()
        with patch.dict(os.environ,{db.ENV:'/nonexistent/verdugo-database'}),patch('subprocess.run',side_effect=AssertionError('Executed')):
            for sid in CASES:self.assertFalse(db.runtime_state(sid)['version_matches'])
        with patch.dict(os.environ,{db.LOOPBACK_ENV:'0'}):self.assertFalse(db.loopback())
        with patch.dict(os.environ,{db.LOOPBACK_ENV:'1'}):self.assertTrue(db.loopback())
        for mode in ('yes','0.0.0.0','127.0.0.1','true'):
            with patch.dict(os.environ,{db.LOOPBACK_ENV:mode}),self.assertRaises(VerdugoError):db.loopback()

    def test_input_data_crosses_parameter_or_copy_boundaries(self):
        p=copy.deepcopy(CASES['apache-age']);p['nodes']=['unique_node'];p['edges']=[]
        sql,variables=db.query('apache-age',p)
        self.assertNotIn('unique_node',sql);self.assertIn('unique_node',''.join(variables))
        p=copy.deepcopy(CASES['pgvector']);p['query']=[123,456,789]
        sql,variables=db.query('pgvector',p)
        self.assertNotIn('123',sql);self.assertIn('123',''.join(variables))
        p=copy.deepcopy(CASES['postgres']);p['rows'][0]['channel']='line\n\\.\nSELECT'
        with self.assertRaises(VerdugoError):db.validate('postgres','campaigns.aggregate',p)
