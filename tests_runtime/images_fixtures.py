import json
CASES={'microsandbox':{'dataset':'demo','secret_text':json.dumps(['Private image content','Second supplied file'])}}
def assert_result(t,sid,r):
 t.assertEqual(2,r['files_in_input']);t.assertEqual(41,r['content_bytes']);t.assertEqual(1,r['image_layers']);t.assertEqual(10240,r['archive_layer_bytes']);t.assertEqual('amd64',r['architecture']);t.assertFalse(r['sandbox_started']);t.assertFalse(r['hardware_isolation_verified']);t.assertFalse(r['cloud_called'])
