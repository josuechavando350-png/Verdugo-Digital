"""Original index inventory contracts with synthetic responses and real loopback sockets."""
import json
import os
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import vector_reads666 as batch, product, workflow
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo.registry666 import read_registry
from test_operations_reads_v019 import wire, PRIVATE

TOKEN = 'synthetic-vector-credential-000000000000'
REPLIES = {'kernel-memory': {'results': [{'name': PRIVATE}, {'name': TOKEN, 'raw': PRIVATE}]},
           'chroma': 7, 'milvus': {'code': 0, 'data': [PRIVATE, TOKEN], 'private': PRIVATE}}
AUTH = {sid: ('Authorization', TOKEN if sid == 'kernel-memory' else 'Bearer ' + TOKEN)
        for sid in batch.SPECS}


def configured():
    cfg = template('nexus')
    for sid in batch.SPECS:
        cfg['tenants']['nexus']['services'][sid].update(
            enabled=True, license_reviewed=True, version='synthetic-666',
            dedicated_instance_reviewed=True, proxy_auth_reviewed=True, native_auth_enforced_reviewed=True)
    return cfg


def command(sid):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])), 'params': {}, 'key': sid + '-inventory'}


class VectorReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = configured(); self.services = self.cfg['tenants']['nexus']['services']
        self.env = patch.dict(os.environ, {self.services[sid]['token_env']: TOKEN for sid in batch.SPECS})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_fixed_routes_body_original_auth_and_no_private_plan(self):
        for sid in batch.SPECS:
            method, path = next(iter(batch.SPECS[sid].values()))
            req = build(sid, command(sid)['operation'], {}, self.services[sid])
            self.assertEqual((method, 'https://example.invalid' + path),
                             (req['public']['method'], req['public']['url']))
            self.assertEqual({'dbName': 'default'} if sid == 'milvus' else None, req['public']['body'])
            self.assertEqual(AUTH[sid][1], req['headers']['Authorization'])
            self.assertFalse(req['mutates']); self.assertNotIn(TOKEN, json.dumps(req['public']))
            self.assertEqual(command(sid)['operation'], product.read_operations()[sid])
        self.assertEqual({('milvus', 'collections.summary')}, batch.READ_POSTS)

    def test_original_evidence_pins_and_unverified_server_scope(self):
        reg = {r['id']: r for r in read_registry()['records']}
        records = json.loads(batch.CONTRACT.read_text())['records']
        self.assertEqual(set(batch.SPECS), {r['id'] for r in records})
        for r in records:
            self.assertEqual(reg[r['id']]['commit_sha'], r['commit'])
            self.assertEqual(batch.PINNED_COMMITS[r['id']], r['commit'])
            self.assertFalse(r['live_verified']); self.assertFalse(r['original_server_executed'])
            self.assertTrue(r['license_text_read'])
            for f in r['files']:
                self.assertRegex(f['git_blob_sha'], r'^[a-f0-9]{40}$')
                self.assertRegex(f['sha256'], r'^[a-f0-9]{64}$')
                self.assertIn('/blob/' + r['commit'] + '/', f['source_url'])

    def test_disabled_defaults_and_auth_review_gates(self):
        for sid in batch.SPECS:
            specific = 'proxy_auth_reviewed' if sid == 'chroma' else 'native_auth_enforced_reviewed'
            initial = template('nexus')['tenants']['nexus']['services'][sid]
            for f in ('enabled', 'license_reviewed', 'dedicated_instance_reviewed', specific):
                self.assertIs(initial[f], False)
            for f in ('dedicated_instance_reviewed', specific):
                for value in (False, None, 1, 'true'):
                    with self.subTest(sid=sid, field=f, value=value), self.assertRaises(VerdugoError):
                        build(sid, command(sid)['operation'], {}, self.services[sid] | {f: value})
            for changes in ({'api_surface': 'cloud'}, {'auth_mode': 'public_no_credentials'}):
                with self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], {}, self.services[sid] | changes)
        for bad in ('x' * 31, 'x' * 32 + '%', 'Bearer ' + TOKEN):
            with patch.dict(os.environ, {self.services['kernel-memory']['token_env']: bad}):
                with self.assertRaises(VerdugoError):
                    build('kernel-memory', 'indexes.summary', {}, self.services['kernel-memory'])

    def test_no_caller_tenant_database_paths_credentials_queries_or_writes(self):
        for sid in batch.SPECS:
            for p in ({'url': 'https://other.invalid'}, {'tenant': 'other'}, {'database': 'other'},
                      {'dbName': 'other'}, {'page': 2}, {'limit': 1}, {'headers': {}}, {'token': TOKEN},
                      {'query': 'text'}, {'method': 'DELETE'}, {'collection': 'other'}):
                with self.subTest(sid=sid, params=p), self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], p, self.services[sid])
            with self.assertRaises(VerdugoError): build(sid, 'collection.create', {}, self.services[sid])

    def test_projection_and_empty_inventory(self):
        results = {sid: check(sid, command(sid)['operation'], r) for sid, r in REPLIES.items()}
        self.assertEqual(2, results['kernel-memory']['indexes_in_response'])
        self.assertEqual(7, results['chroma']['collections_reported'])
        self.assertEqual(2, results['milvus']['collections_in_response'])
        for r in results.values():
            self.assertNotIn(PRIVATE, json.dumps(r)); self.assertNotIn(TOKEN, json.dumps(r))
            self.assertFalse(r['live_verified']); self.assertFalse(r['raw_provider_payload_retained'])
            self.assertEqual(0, r['models_called']); self.assertEqual(0, r['vectors_written'])
        self.assertEqual(0, check('kernel-memory', 'indexes.summary', {'results': []})['indexes_in_response'])
        self.assertEqual(0, check('chroma', 'collections.summary', 0)['collections_reported'])
        self.assertEqual(0, check('milvus', 'collections.summary', {'code': 0, 'data': []})['collections_in_response'])

    def test_invalid_schemas_scalars_error_envelopes_and_oversize_arrays(self):
        invalid = {
            'kernel-memory': [{}, {'results': None}, {'results': [None]}, {'results': [{}]},
                              {'results': [{'name': False}]}, {'results': [{'name': 'a'}] * 1001},
                              {'results': [{'name': 'a' * 1025}]}],
            'chroma': [None, {}, [], True, -1, 1.0, '7', 2**32],
            'milvus': [{}, {'code': True, 'data': []}, {'code': '0', 'data': []},
                       {'code': 200, 'data': []}, {'code': 0, 'data': None},
                       {'code': 0, 'data': [None]}, {'code': 0, 'data': ['']},
                       {'code': 0, 'data': ['a' * 1025]}, {'code': 0, 'data': ['a'] * 1001}],
        }
        for sid, replies in invalid.items():
            for r in replies:
                with self.subTest(sid=sid, reply=r), self.assertRaises(VerdugoError):
                    check(sid, command(sid)['operation'], r)
        self.assertEqual(2**32 - 1, check('chroma', 'collections.summary', 2**32 - 1)['collections_reported'])

    def test_socket_workflow_mcp_cli_restart_privacy_and_fixed_post(self):
        spec = {'id': 'vector-inventory-acceptance', 'steps': [
            {'id': sid, 'service': sid, 'operation': command(sid)['operation'], 'params': {}}
            for sid in batch.SPECS]}
        with tempfile.TemporaryDirectory() as tmp, wire(self.cfg, REPLIES, batch.SPECS, AUTH) as server:
            path = str(Path(tmp) / 'state.sqlite3')
            with closing(Engine(path, self.cfg)) as engine:
                plan = invoke(engine, 'verdugo_workflow', {'workflow': spec})
                self.assertEqual([], plan['approval_batch']); self.assertEqual([], server['calls'])
                result = invoke(engine, 'verdugo_workflow', {'workflow': spec, 'execute': True})
                self.assertEqual('succeeded', result['state'], result)
                self.assertEqual(3, len(server['calls']))
                for call in server['calls']:
                    self.assertEqual(AUTH[call['service']][1], call['headers']['Authorization'])
                    self.assertEqual({'dbName': 'default'} if call['service'] == 'milvus' else None,
                                     json.loads(call['body']) if call['body'] else None)
                dump = '\n'.join(engine.db.iterdump())
                self.assertNotIn(PRIVATE, dump); self.assertNotIn(TOKEN, dump)
            with closing(Engine(path, self.cfg, transport=lambda *_: self.fail('duplicate read'))) as engine:
                self.assertEqual(result['steps'], workflow.run(engine, spec, True)['steps'])
            config = Path(tmp) / 'config.json'; config.write_text(json.dumps(self.cfg)); config.chmod(0o600)
            manifest = Path(tmp) / 'workflow.json'; manifest.write_text(json.dumps(spec))
            proc = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config), '--state', path,
                                   'workflow', '@' + str(manifest), '--execute'], capture_output=True, text=True, timeout=30)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual('succeeded', json.loads(proc.stdout)['state']); self.assertEqual(3, len(server['calls']))

    def test_http_statuses_bad_json_limits_and_no_retries(self):
        with wire(self.cfg, REPLIES, batch.SPECS, AUTH) as server:
            for sid in batch.SPECS:
                for status in (202, 204, 302, 401, 403, 429, 500):
                    server['status'] = status; count = len(server['calls'])
                    with closing(Engine(':memory:', self.cfg)) as engine:
                        self.assertEqual('failed', engine.execute(command(sid), True)['state'])
                        self.assertNotIn(PRIVATE, '\n'.join(engine.db.iterdump()))
                    self.assertEqual(count + 1, len(server['calls']))
                server['status'] = 200
                for raw in (b'{not json', b'x' * (1024 * 1024 + 1)):
                    server['raw'] = raw
                    with closing(Engine(':memory:', self.cfg)) as engine:
                        self.assertEqual('failed', engine.execute(command(sid), True)['state'])
                server['raw'] = None

    def test_removed_review_and_changed_credential_block_replay(self):
        with wire(self.cfg, REPLIES, batch.SPECS, AUTH) as server, closing(Engine(':memory:', self.cfg)) as engine:
            for sid in batch.SPECS:
                self.assertEqual('succeeded', engine.execute(command(sid), True)['state'])
                self.services[sid]['dedicated_instance_reviewed'] = False
                with self.assertRaises(VerdugoError): engine.execute(command(sid), True)
                self.services[sid]['dedicated_instance_reviewed'] = True
                with patch.dict(os.environ, {self.services[sid]['token_env']: TOKEN + '-changed'}):
                    with self.assertRaises(VerdugoError): engine.execute(command(sid), True)
            self.assertEqual(3, len(server['calls']))
