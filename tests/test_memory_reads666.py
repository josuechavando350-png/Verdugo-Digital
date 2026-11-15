"""Counts-only memory observations on synthetic sockets; no original server certification."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import memory_reads666 as batch, product, workflow
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo.registry666 import read_registry
from test_operations_reads_v019 import wire, TOKEN, PRIVATE

TASKS = dict(zip(batch.TASK_STATES, (2, 1, 2, 4, 1, 0, 8)))
DOCS = dict(zip(batch.DOC_STATES + ('all',), (1, 2, 3, 4, 0, 5, 1, 0, 16)))
REPLIES = {
    'memos': {'code': 200, 'message': PRIVATE,
              'data': {'scheduler_summary': TASKS | {'private': TOKEN},
                       'all_tasks_summary': TASKS | {'private': PRIVATE}, 'tasks': [PRIVATE]}},
    'lightrag': {'status_counts': DOCS, 'private': [PRIVATE, TOKEN]},
}
AUTH = {'lightrag': ('X-API-Key', TOKEN)}


def configured():
    cfg = template('nexus')
    for sid in batch.SPECS:
        cfg['tenants']['nexus']['services'][sid].update(
            enabled=True, license_reviewed=True, version='synthetic-666',
            dedicated_instance_reviewed=True, proxy_auth_reviewed=True,
            proxy_strips_credentials_reviewed=True, native_auth_enforced_reviewed=True,
            status_storage_reviewed=True)
    return cfg


def command(sid, key=None):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])),
            'params': {}, 'key': key or sid + '-observation'}


class MemoryReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = configured()
        self.services = self.cfg['tenants']['nexus']['services']
        self.env = patch.dict(os.environ, {self.services[s]['token_env']: TOKEN for s in batch.SPECS})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_routes_original_auth_and_no_private_plan(self):
        for sid in batch.SPECS:
            method, path = next(iter(batch.SPECS[sid].values()))
            req = build(sid, command(sid)['operation'], {}, self.services[sid])
            self.assertEqual((method, 'https://example.invalid' + path),
                             (req['public']['method'], req['public']['url']))
            self.assertIsNone(req['public']['body']); self.assertFalse(req['mutates'])
            header, value = AUTH.get(sid, ('Authorization', 'Bearer ' + TOKEN))
            self.assertEqual(value, req['headers'][header])
            if sid == 'lightrag': self.assertNotIn('Authorization', req['headers'])
            self.assertNotIn(TOKEN, json.dumps(req['public']))
            self.assertEqual(command(sid)['operation'], product.read_operations()[sid])

    def test_evidence_and_fixed_commit(self):
        registry = {r['id']: r for r in read_registry()['records']}
        manifest = json.loads(batch.CONTRACT.read_text())
        self.assertEqual(set(batch.SPECS), {r['id'] for r in manifest['records']})
        for row in manifest['records']:
            self.assertEqual(registry[row['id']]['commit_sha'], row['commit'])
            self.assertEqual(batch.PINNED_COMMITS[row['id']], row['commit'])
            self.assertFalse(row['live_verified']); self.assertFalse(row['original_server_executed'])
            self.assertTrue(row['license_text_read'])
            for item in row['files']:
                self.assertRegex(item['git_blob_sha'], r'^[a-f0-9]{40}$')
                self.assertRegex(item['sha256'], r'^[a-f0-9]{64}$')
                self.assertIn('/blob/' + row['commit'] + '/', item['source_url'])

    def test_disabled_defaults_and_auth_storage_review_gates(self):
        for sid in batch.SPECS:
            gates = ('dedicated_instance_reviewed',) + (
                ('proxy_auth_reviewed', 'proxy_strips_credentials_reviewed') if sid == 'memos'
                else ('native_auth_enforced_reviewed', 'status_storage_reviewed'))
            initial = template('nexus')['tenants']['nexus']['services'][sid]
            for field in ('enabled', 'license_reviewed') + gates: self.assertIs(initial[field], False)
            for field in gates:
                for value in (False, None, 1, 'true'):
                    with self.subTest(sid=sid, field=field, value=value), self.assertRaises(VerdugoError):
                        build(sid, command(sid)['operation'], {}, self.services[sid] | {field: value})
            for changes in ({'api_surface': 'cloud'}, {'auth_mode': 'public_no_credentials'}):
                with self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], {}, self.services[sid] | changes)
        with self.assertRaises(VerdugoError):
            build('lightrag', 'documents.summary', {}, self.services['lightrag'] | {'status_storage': 'PGDocStatusStorage'})

    def test_no_caller_routes_queries_tenants_credentials_or_writes(self):
        for sid in batch.SPECS:
            for p in ({'url': 'https://other.invalid'}, {'tenant': 'other'}, {'workspace': 'other'},
                      {'page': 2}, {'user_id': 'other'}, {'status': 'all'}, {'headers': {}},
                      {'token': TOKEN}, {'query': 'text'}, {'method': 'DELETE'}, {'backend': 'other'}):
                with self.subTest(sid=sid, params=p), self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], p, self.services[sid])
            with self.assertRaises(VerdugoError): build(sid, 'memory.create', {}, self.services[sid])

    def test_projected_counts_overlap_and_zero(self):
        for sid in batch.SPECS:
            r = check(sid, command(sid)['operation'], REPLIES[sid])
            self.assertNotIn(PRIVATE, json.dumps(r)); self.assertNotIn(TOKEN, json.dumps(r))
            self.assertFalse(r['live_verified']); self.assertFalse(r['raw_provider_payload_retained'])
            self.assertEqual(0, r['models_called']); self.assertEqual(0, r['retrievals_executed'])
        r = check('memos', 'scheduler.summary', REPLIES['memos'])
        self.assertEqual(TASKS, r['scheduler_summary']); self.assertEqual(TASKS, r['all_tasks_summary'])
        self.assertFalse(r['counts_are_disjoint']); self.assertNotEqual(sum(TASKS.values()), TASKS['total'])
        self.assertEqual(DOCS, check('lightrag', 'documents.summary', REPLIES['lightrag'])['status_counts'])
        zero = {name: 0 for name in DOCS}
        self.assertEqual(zero, check('lightrag', 'documents.summary', {'status_counts': zero})['status_counts'])
        zero_tasks = {name: 0 for name in TASKS}
        z = check('memos', 'scheduler.summary', {'code': 200, 'data': {
            'scheduler_summary': zero_tasks, 'all_tasks_summary': zero_tasks}})
        self.assertEqual(zero_tasks, z['scheduler_summary'])

    def test_schema_bounds_unknown_statuses_and_false_success(self):
        bad = {'memos': [{}, {'code': 200, 'data': None}, REPLIES['memos'] | {'code': 500},
                         REPLIES['memos'] | {'code': True}, REPLIES['memos'] | {'code': '200'}],
               'lightrag': [{}, {'status_counts': None}, {'status_counts': DOCS | {'all': 17}},
                            {'status_counts': DOCS | {'UNKNOWN': 1}}]}
        for sid in batch.SPECS:
            for key in (TASKS if sid == 'memos' else DOCS):
                for value in (True, -1, 1.0, '1', None, 10**12 + 1):
                    reply = copy.deepcopy(REPLIES[sid])
                    counts = reply['data']['all_tasks_summary'] if sid == 'memos' else reply['status_counts']
                    counts[key] = value; bad[sid].append(reply)
            for reply in bad[sid]:
                with self.subTest(sid=sid, reply=reply), self.assertRaises(VerdugoError):
                    check(sid, command(sid)['operation'], reply)

    def test_socket_workflow_cli_mcp_restart_and_no_private_persistence(self):
        spec = {'id': 'memory-read-acceptance', 'steps': [
            {'id': sid, 'service': sid, 'operation': command(sid)['operation'], 'params': {}}
            for sid in batch.SPECS]}
        with tempfile.TemporaryDirectory() as tmp, wire(self.cfg, REPLIES, batch.SPECS, AUTH) as server:
            path = str(Path(tmp) / 'state.sqlite3')
            with closing(Engine(path, self.cfg)) as engine:
                preview = invoke(engine, 'verdugo_workflow', {'workflow': spec})
                self.assertEqual([], preview['approval_batch']); self.assertEqual([], server['calls'])
                result = invoke(engine, 'verdugo_workflow', {'workflow': spec, 'execute': True})
                self.assertEqual('succeeded', result['state'], result)
                self.assertEqual(2, len(server['calls']))
                for call in server['calls']:
                    header, value = AUTH.get(call['service'], ('Authorization', 'Bearer ' + TOKEN))
                    self.assertEqual(value, call['headers'][header]); self.assertEqual(b'', call['body'])
                dump = '\n'.join(engine.db.iterdump())
                self.assertNotIn(PRIVATE, dump); self.assertNotIn(TOKEN, dump)
            with closing(Engine(path, self.cfg, transport=lambda *_: self.fail('read repeated'))) as engine:
                self.assertEqual(result['steps'], workflow.run(engine, spec, True)['steps'])
            config = Path(tmp) / 'config.json'; config.write_text(json.dumps(self.cfg)); config.chmod(0o600)
            manifest = Path(tmp) / 'workflow.json'; manifest.write_text(json.dumps(spec))
            proc = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config),
                                   '--state', path, 'workflow', '@' + str(manifest), '--execute'],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual('succeeded', json.loads(proc.stdout)['state']); self.assertEqual(2, len(server['calls']))

    def test_http_error_redirects_async_invalid_and_oversized_json_no_retry(self):
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

    def test_removed_review_or_changed_credentials_cannot_reuse_prior_read(self):
        with wire(self.cfg, REPLIES, batch.SPECS, AUTH) as server, closing(Engine(':memory:', self.cfg)) as engine:
            for sid in batch.SPECS:
                self.assertEqual('succeeded', engine.execute(command(sid), True)['state'])
                field = 'proxy_strips_credentials_reviewed' if sid == 'memos' else 'native_auth_enforced_reviewed'
                self.services[sid][field] = False
                with self.assertRaises(VerdugoError): engine.execute(command(sid), True)
                self.services[sid][field] = True
                with patch.dict(os.environ, {self.services[sid]['token_env']: 'changed-synthetic-credential'}):
                    with self.assertRaises(VerdugoError): engine.execute(command(sid), True)
            self.assertEqual(2, len(server['calls']))
