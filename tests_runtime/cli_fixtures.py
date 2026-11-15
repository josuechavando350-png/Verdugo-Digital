CASES = {
    'gitleaks': {'dataset':'demo','secret_text':'api_key = "Vrg59D7hRk8Ss3B7w9H2nP0d6T4f8A1z"'},
    'restic': {'dataset':'demo','secret_text':'Synthetic archive verification'},
    'syft': {'dataset':'demo','packages':[{'name':'lodash','version':'4.17.20'}]},
    'grype': {'dataset':'demo','packages':[{'name':'lodash','version':'4.17.20'}]},
    'sops': {'dataset':'demo','secret_text':'Synthetic encryption verification'},
    'vale': {'dataset':'demo','text':'Obviamente esto simplemente funciona.'},
    'dvc': {'dataset':'demo','secret_text':'Synthetic data version verification'},
    'dnstwist': {'dataset':'demo','domain':'example.com'},
}


def assert_result(test,sid,r):
    if sid == 'gitleaks':
        test.assertGreaterEqual(r['findings'],1);test.assertFalse(r['credentials_tested'])
        test.assertIn({'rule_id':'generic-api-key','count':1},r['by_rule'])
    elif sid in ('restic','dvc'):
        test.assertTrue(r['roundtrip_verified']);test.assertFalse(r['durable_backup_created'])
        test.assertEqual(len(CASES[sid]['secret_text'].encode()),r['bytes_verified'])
    elif sid == 'sops':
        test.assertTrue(r['roundtrip_verified']);test.assertFalse(r['key_persisted']);test.assertGreater(r['encrypted_bytes'],r['input_bytes'])
    elif sid == 'syft':
        test.assertEqual(CASES[sid]['packages'],r['packages']);test.assertFalse(r['installed_packages_verified'])
    elif sid == 'grype':
        test.assertGreater(r['matches'],0);test.assertEqual(64,len(r['snapshot_sha256']));test.assertFalse(r['installed_assets_verified'])
        test.assertEqual(r['matches'],sum(r['by_severity'].values()))
    elif sid == 'vale': test.assertEqual(2,r['issues'])
    elif sid == 'dnstwist':
        test.assertIn('exmple.com',r['domains']);test.assertFalse(r['dns_queried']);test.assertNotIn('example.com',r['domains'])
