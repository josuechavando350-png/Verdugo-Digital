import json
REF={'name':'Private Business','address':'Private Street 1','phone':'+525500001111'}
def maps_payload(title='Private Maps Place'):
 data=[None]*200;data[11]=title;data[13]=['Cafe','Coffee'];data[4]=[None]*9;data[4][7]=4.5;data[4][8]=12;data[7]=['https://example.invalid'];data[9]=[None,None,19.4,-99.1]
 return json.dumps([[None]*6+[data]])
CASES={
 'cua':{'dataset':'demo','width':640,'height':480,'actions':[{'type':'click','x':10,'y':20},{'type':'scroll','direction':'down','amount':3},{'type':'done'}]},
 'tinytroupe':{'dataset':'demo','control':[1,2,3,4,5],'treatment':[2,3,4,5,6],'assumptions_reviewed':True},
 'local-seo-skills':{'dataset':'demo','secret_text':json.dumps({'reference':REF,'listings':[REF|{'id':'same'},REF|{'id':'different','name':'PRIVATE BUSINESS'}]})},
 'google-maps-scraper':{'dataset':'demo','secret_text':maps_payload()},
}
def assert_result(t,sid,r):
 if sid=='cua':
  t.assertEqual([{'type':'ClickAction','x':10,'y':20},{'type':'ScrollAction','direction':'down','amount':3},{'type':'DoneAction'}],r['actions']);t.assertFalse(r['actions_executed'])
 elif sid=='tinytroupe':
  t.assertEqual(1,r['mean_difference']);t.assertAlmostEqual(.34659350708733416,r['p_value'],places=10);t.assertEqual(8,r['degrees_of_freedom']);t.assertFalse(r['significant']);t.assertFalse(r['agents_simulated'])
 elif sid=='local-seo-skills':
  t.assertEqual(1,r['consistent']);t.assertEqual([{'id':'same','mismatched_fields':[]},{'id':'different','mismatched_fields':['name']}],r['listings']);t.assertFalse(r['directory_presence_verified'])
 else:
  t.assertEqual([{'categories':2,'opening_days':0,'rating':4.5,'review_count':12,'website_present':True}],r['records']);t.assertFalse(r['google_maps_queried'])
