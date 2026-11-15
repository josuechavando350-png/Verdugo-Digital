import json
CASES={'landscape-app':{'dataset':'demo','secret_text':json.dumps([{'name':'Private supplied project','repo_url':'https://github.com/example/demo','joined':'2026-01-01'}])}}
def assert_result(t,sid,r):
 t.assertTrue(r['schema_valid']);t.assertEqual(0,r['fatal_errors']);t.assertEqual(1,r['projects_in_input']);t.assertFalse(r['github_comment_sent']);t.assertFalse(r['repositories_verified'])
