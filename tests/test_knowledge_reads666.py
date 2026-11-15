"""Original community RAGFlow route, authentication, projection and wire contract."""
import json
import os
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from verdugo import knowledge_reads666 as batch, product, workflow
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo.registry666 import read_registry
from test_operations_reads_v019 import wire, PRIVATE

TOKEN = 'synthetic-ragflow-credential'
REPLY = {'code': 0, 'data': [{'id': 'synthetic-id', 'name': PRIVATE,
                           'description': PRIVATE, 'parser_config': {'private': TOKEN}}],
         'total_datasets': 3, 'message': 'success'}


def configured():
    cfg = template('nexus')
    cfg['tenants']['nexus']['services']['ragflow'].update(
        enabled=True, license_reviewed=True, version='synthetic-666',
        dedicated_instance_reviewed=True, native_auth_enforced_reviewed=True, community_build_reviewed=True)
    return cfg


class KnowledgeReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = configured(); self.service = self.cfg['tenants']['nexus']['services']['ragflow']
        env = patch.dict(os.environ, {self.service['token_env']: TOKEN})
        env.start(); self.addCleanup(env.stop)

    def test_fixed_original_route_auth_and_defaults(self):
        req = build('ragflow', 'datasets.summary', {}, self.service)
        self.assertEqual('https://example.invalid/api/v1/datasets?page=1&page_size=100', req['public']['url'])
        self.assertEqual('GET', req['public']['method']); self.assertIsNone(req['public']['body'])
        self.assertEqual('Bearer '+TOKEN, req['headers']['Authorization'])
        self.assertFalse(req['mutates']); self.assertNotIn(TOKEN, json.dumps(req['public']))
        self.assertEqual('datasets.summary', product.read_operations()['ragflow'])
        initial = template('nexus')['tenants']['nexus']['services']['ragflow']
        for flag in ('enabled', 'license_reviewed', 'native_auth_enforced_reviewed',
                     'community_build_reviewed', 'dedicated_instance_reviewed'):
            self.assertIs(initial[flag], False)

    def test_community_auth_and_instance_gates(self):
        for field in ('community_build_reviewed', 'native_auth_enforced_reviewed', 'dedicated_instance_reviewed'):
            for value in (None, False, 1, 'true'):
                with self.subTest(field=field, value=value), self.assertRaises(VerdugoError):
                    build('ragflow', 'datasets.summary', {}, self.service | {field: value})
        for changes in ({'api_surface': 'cloud'}, {'api_surface': 'enterprise'}, {'auth_mode': 'none'}):
            with self.assertRaises(VerdugoError): build('ragflow', 'datasets.summary', {}, self.service | changes)

    def test_caller_cannot_select_identity_path_or_model(self):
        for params in ({'tenant_id': 'other'}, {'page': 2}, {'page_size': 1}, {'name': PRIVATE},
                       {'model': 'remote'}, {'query': PRIVATE}, {'url': 'https://other.invalid'},
                       {'headers': {}}, {'token': TOKEN}, {'ids': ['synthetic-id']}):
            with self.subTest(params=params), self.assertRaises(VerdugoError):
                build('ragflow', 'datasets.summary', params, self.service)
        with self.assertRaises(VerdugoError): build('ragflow', 'dataset.create', {}, self.service)

    def test_projection_original_success_and_empty_page(self):
        value = check('ragflow', 'datasets.summary', REPLY)
        self.assertEqual(1, value['datasets_in_response']); self.assertEqual(3, value['datasets_total_reported'])
        self.assertTrue(value['more_reported']); self.assertFalse(value['complete_export_verified'])
        self.assertNotIn(PRIVATE, json.dumps(value)); self.assertNotIn(TOKEN, json.dumps(value))
        self.assertFalse(value['live_verified']); self.assertEqual(0, value['models_called'])
        self.assertEqual(0, check('ragflow', 'datasets.summary', {'code': 0, 'data': [], 'total_datasets': 0})['datasets_in_response'])

    def test_schema_error_and_bounds_rejected(self):
        for value in ({}, [], {'code': True}, REPLY | {'code': 102}, REPLY | {'data': None},
                      REPLY | {'total_datasets': True}, REPLY | {'total_datasets': 0},
                      REPLY | {'total_datasets': 10**12+1}, REPLY | {'data': [{}]},
                      REPLY | {'data': [{'id': False, 'name': 'a'}]},
                      REPLY | {'data': [{'id': 'a', 'name': False}]},
                      REPLY | {'data': [{'id': 'a', 'name': 'x'*4097}]},
                      REPLY | {'data': REPLY['data']*101, 'total_datasets': 101}):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                check('ragflow', 'datasets.summary', value)

    def test_sockets_mcp_cli_restart_and_no_raw_persistence(self):
        spec = {'id': 'ragflow-read', 'steps': [{'id': 'inventory', 'service': 'ragflow',
                                               'operation': 'datasets.summary', 'params': {}}]}
        with tempfile.TemporaryDirectory() as tmp, wire(self.cfg, {'ragflow': REPLY}, batch.SPECS, {'ragflow': ('Authorization', 'Bearer '+TOKEN)}) as server:
            path = str(Path(tmp)/'state.sqlite3')
            with closing(Engine(path, self.cfg)) as engine:
                preview = invoke(engine, 'verdugo_workflow', {'workflow': spec})
                self.assertEqual([], preview['approval_batch']); self.assertEqual([], server['calls'])
                result = invoke(engine, 'verdugo_workflow', {'workflow': spec, 'execute': True})
                self.assertEqual('succeeded', result['state'], result)
                self.assertEqual(1, len(server['calls']))
                dump = '\n'.join(engine.db.iterdump())
                self.assertNotIn(PRIVATE, dump); self.assertNotIn(TOKEN, dump)
            with closing(Engine(path, self.cfg, transport=lambda *_: self.fail('replayed network'))) as engine:
                replay = workflow.run(engine, spec, True)
                self.assertEqual(result['steps'], replay['steps'])
            config = Path(tmp)/'config.json'; config.write_text(json.dumps(self.cfg)); config.chmod(0o600)
            request = Path(tmp)/'request.json'; request.write_text(json.dumps(spec))
            result = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config), '--state', path,
                                     'workflow', '@'+str(request), '--execute'], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('succeeded', json.loads(result.stdout)['state']); self.assertEqual(1, len(server['calls']))

    def test_http_failures_oversize_and_replay_gates(self):
        with wire(self.cfg, {'ragflow': REPLY}, batch.SPECS, {'ragflow': ('Authorization', 'Bearer '+TOKEN)}) as server:
            with closing(Engine(':memory:', self.cfg)) as engine:
                for i, status in enumerate((202, 204, 302, 401, 500)):
                    server['status'] = status
                    result = engine.execute({'service':'ragflow','operation':'datasets.summary',
                                             'params':{},'key':'status-'+str(i)}, True)
                    self.assertEqual('failed', result['state'])
                    self.assertNotIn(PRIVATE, json.dumps(result))
                server['status'] = 200; server['raw'] = b'x' * (1024*1024+1)
                result = engine.execute({'service':'ragflow','operation':'datasets.summary',
                                         'params':{},'key':'oversize'}, True)
                self.assertEqual('failed', result['state'])
                server['raw'] = None
                command = {'service':'ragflow','operation':'datasets.summary','params':{},'key':'replay'}
                self.assertEqual('succeeded', engine.execute(command, True)['state'])
                self.service['community_build_reviewed'] = False
                with self.assertRaises(VerdugoError): engine.execute(command, True)
                self.service['community_build_reviewed'] = True
                with patch.dict(os.environ, {self.service['token_env']: TOKEN+'-changed'}):
                    with self.assertRaises(VerdugoError): engine.execute(command, True)

    def test_original_source_evidence_and_server_not_executed(self):
        r = json.loads(batch.CONTRACT.read_text())['records'][0]
        reg = next(x for x in read_registry()['records'] if x['id'] == 'ragflow')
        self.assertEqual(reg['commit_sha'], r['commit']); self.assertTrue(r['license_text_read'])
        self.assertFalse(r['original_server_executed']); self.assertFalse(r['live_verified'])
        self.assertEqual(10, len(r['files']))
        for f in r['files']:
            self.assertRegex(f['git_blob_sha'], '^[a-f0-9]{40}$'); self.assertRegex(f['sha256'], '^[a-f0-9]{64}$')
