import json
CASES={
 'landscape-app':{'dataset':'demo','secret_text':json.dumps([{'name':'Private supplied project','repo_url':'https://github.com/example/demo','joined':'2026-01-01'}])},
 'playwright-mcp':{'dataset':'demo','secret_text':json.dumps({'title':'Private supplied document','headings':[{'level':1,'text':'Private heading'},{'level':2,'text':'Private detail'}],'buttons':['Private booking']})},
}
def assert_result(t,sid,r):
 if sid=='playwright-mcp':
  t.assertEqual(2,r['headings']);t.assertEqual([1,2],r['heading_levels']);t.assertEqual(1,r['buttons'])
  t.assertEqual('browser_snapshot',r['mcp_tool']);t.assertTrue(r['browser_started']);t.assertTrue(r['browser_closed'])
  t.assertFalse(r['javascript_enabled']);t.assertFalse(r['remote_page_fetched'])
 else:
  t.assertTrue(r['schema_valid']);t.assertEqual(0,r['fatal_errors']);t.assertEqual(1,r['projects_in_input']);t.assertFalse(r['github_comment_sent']);t.assertFalse(r['repositories_verified'])
