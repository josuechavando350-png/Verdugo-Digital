import json
CASES={
 'cc-webgraph':{'dataset':'demo','adjacencies':[[1,2,2,4],[2,3,4],[]]},
 'arx':{'dataset':'demo','k':2,'secret_text':json.dumps([{'age':21,'zipcode':'12345'},{'age':22,'zipcode':'12346'},{'age':31,'zipcode':'12450'},{'age':32,'zipcode':'12451'}])},
 'openapi-generator':{'dataset':'demo','secret_text':json.dumps({'openapi':'3.0.3','info':{'title':'PrivateSuppliedSpec','version':'1'},'paths':{'/status':{'get':{'responses':{'200':{'description':'OK'}}}}}})},
 'goaccess':{'dataset':'demo','events':[{'path':'/a','status':200,'bytes':120,'method':'GET'},{'path':'/b','status':404,'bytes':20,'method':'GET'},{'path':'/a','status':200,'bytes':200,'method':'HEAD'}]},
}
def assert_result(test,sid,out):
 if sid=='cc-webgraph':
  test.assertEqual([{'node':1,'occurrences':1},{'node':2,'occurrences':3},{'node':3,'occurrences':1},{'node':4,'occurrences':2}],out['counts']);test.assertFalse(out['external_webgraph_loaded'])
 elif sid=='arx':
  test.assertEqual(4,out['records']);test.assertEqual(2,out['minimum_class_size']);test.assertEqual(2,out['equivalence_classes']);test.assertFalse(out['privacy_certified'])
 elif sid=='openapi-generator':test.assertTrue(out['schema_valid']);test.assertEqual(0,out['validation_errors']);test.assertFalse(out['api_runtime_verified'])
 else:test.assertEqual(3,out['requests']);test.assertEqual(340,out['bytes']);test.assertEqual({'200':2,'404':1},out['status_codes']);test.assertFalse(out['real_visitors_verified'])
