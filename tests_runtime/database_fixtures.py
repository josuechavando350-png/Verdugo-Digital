CASES = {
    'valkey': {'dataset':'demo','entries':[{'id':'solar','value':10},{'id':'wind','value':20}],
               'lookup':['wind','missing','solar']},
    'postgres': {'dataset':'demo','currency':'MXN','rows':[
        {'channel':'organic','spend_minor':100,'revenue_minor':300,'leads':3,'conversions':1},
        {'channel':'organic','spend_minor':50,'revenue_minor':400,'leads':2,'conversions':1}]},
    'pgvector': {'dataset':'demo','rows':[
        {'id':'close','vector':[1,0,0]},{'id':'far','vector':[0,3,0]},{'id':'middle','vector':[2,0,0]}],
        'query':[0,0,0],'limit':2},
    'apache-age': {'dataset':'demo','nodes':['a','b','c'],
                   'edges':[{'source':'a','target':'b'},{'source':'a','target':'c'},{'source':'b','target':'c'}]},
}


def assert_result(test, sid, value):
    import os
    tcp = os.getenv('VERDUGO_DATABASE_LOOPBACK', '0') == '1'
    test.assertEqual(tcp, value['tcp_listener_enabled'])
    test.assertEqual('authenticated_loopback' if tcp else 'private_unix_socket', value['listener_scope'])
    if sid == 'valkey':
        test.assertEqual([20,None,10],value['matches'])
        test.assertEqual(2,value['hits']);test.assertEqual(1,value['misses'])
        test.assertFalse(value['persistent_cache_created'])
    else:
        test.assertTrue(value['temporary_database']);test.assertFalse(value['persistent_database_created'])
        if sid == 'postgres':
            test.assertEqual([{'channel':'organic','spend_minor':150,'revenue_minor':700,'leads':5,'conversions':2}],value['channels'])
            test.assertFalse(value['bank_reconciled'])
        elif sid == 'pgvector':
            test.assertEqual([{'id':'close','distance':1},{'id':'middle','distance':2}],value['matches'])
            test.assertFalse(value['semantic_relevance_verified'])
        else:
            test.assertEqual([{'id':'a','out_degree':2},{'id':'b','out_degree':1},{'id':'c','out_degree':0}],value['nodes'])
            test.assertFalse(value['external_graph_verified'])
