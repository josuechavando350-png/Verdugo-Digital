import json
RESPONSES=[{'id':'present','status':200,'text':'Private owned brand','mode':'status_code','marker':'Missing'},
 {'id':'absent','status':404,'text':'Missing private brand','mode':'status_code','marker':'Missing'},
 {'id':'soft-missing','status':200,'text':'Brand not found','mode':'message','marker':'Brand not found'}]
CASES={'siteone-crawler':{'dataset':'demo','pages':[{'id':'home','title':'Home','links':['about','missing']},{'id':'about','title':'About','links':['home']}]},
 'sherlock':{'dataset':'demo','secret_text':json.dumps(RESPONSES)}}
def assert_result(t,sid,r):
 t.assertTrue(r['local_server_closed'])
 if sid=='siteone-crawler':
  t.assertEqual(3,r['visited']);t.assertEqual({'200':2,'404':1},r['status_counts']);t.assertEqual(1,r['missing_pages']);t.assertEqual(4,r['owned_http_requests']);t.assertFalse(r['remote_site_fetched']);t.assertFalse(r['quality_scores_reported'])
 else:
  t.assertEqual([{'id':'present','classification':'Claimed','http_status':200},{'id':'absent','classification':'Available','http_status':404},{'id':'soft-missing','classification':'Available','http_status':200}],r['results']);t.assertEqual(3,r['owned_http_requests']);t.assertFalse(r['live_accounts_verified']);t.assertFalse(r['identity_inferred'])
