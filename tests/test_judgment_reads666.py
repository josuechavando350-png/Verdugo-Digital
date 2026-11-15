"""Original HTTP contracts on synthetic loopback servers, never live certification."""
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import judgment_reads666 as batch, product, workflow
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo.registry666 import read_registry
from test_operations_reads_v019 import wire, TOKEN, PRIVATE

REPLIES = {
    'tensorzero': {'inferences': [
        {'type': 'chat', 'input': PRIVATE, 'output': TOKEN},
        {'type': 'json', 'input': PRIVATE, 'tags': {'private': TOKEN}},
        {'type': 'chat', 'function_name': PRIVATE}]},
    'opik': {'page': 1, 'size': 2, 'total': 5,
             'content': [{'name': PRIVATE, 'id': TOKEN}, {'name': TOKEN}],
             'sortable_by': [PRIVATE]},
}


def configured():
    cfg = template('nexus')
    for sid in batch.SPECS:
        cfg['tenants']['nexus']['services'][sid].update(
            enabled=True, license_reviewed=True, version='synthetic-666',
            dedicated_instance_reviewed=True, proxy_auth_reviewed=True,
            native_auth_enforced_reviewed=True)
    return cfg


def command(sid, key=None):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])),
            'params': {}, 'key': key or sid + '-observation'}


class JudgmentReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = configured()
        self.services = self.cfg['tenants']['nexus']['services']
        self.env = patch.dict(os.environ, {self.services[s]['token_env']: TOKEN for s in batch.SPECS})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_fixed_routes_read_body_headers_and_no_private_plan(self):
        for sid in batch.SPECS:
            method, path = next(iter(batch.SPECS[sid].values()))
            request = build(sid, command(sid)['operation'], {}, self.services[sid])
            self.assertEqual((method, 'https://example.invalid' + path),
                             (request['public']['method'], request['public']['url']))
            self.assertFalse(request['mutates'])
            self.assertEqual('Bearer ' + TOKEN, request['headers']['Authorization'])
            self.assertNotIn(TOKEN, json.dumps(request['public']))
            self.assertEqual({'limit': 100, 'offset': 0} if sid == 'tensorzero' else None,
                             request['public']['body'])
            if sid == 'opik':
                self.assertEqual('default', request['headers']['Comet-Workspace'])
            self.assertEqual(command(sid)['operation'], product.read_operations()[sid])

    def test_original_commit_and_source_evidence(self):
        records = {r['id']: r for r in read_registry()['records']}
        manifest = json.loads(batch.CONTRACT.read_text())
        self.assertEqual(set(batch.SPECS), {r['id'] for r in manifest['records']})
        for row in manifest['records']:
            self.assertEqual(records[row['id']]['commit_sha'], row['commit'])
            self.assertEqual(batch.PINNED_COMMITS[row['id']], row['commit'])
            self.assertFalse(row['live_verified'])
            self.assertFalse(row['original_server_executed'])
            for item in row['files']:
                self.assertRegex(item['git_blob_sha'], r'^[a-f0-9]{40}$')
                self.assertRegex(item['sha256'], r'^[a-f0-9]{64}$')
                self.assertIn('/blob/' + row['commit'] + '/', item['source_url'])

    def test_default_disabled_and_all_review_gates_fail_closed(self):
        for sid in batch.SPECS:
            initial = template('nexus')['tenants']['nexus']['services'][sid]
            self.assertIs(initial['enabled'], False)
            self.assertIs(initial['license_reviewed'], False)
            self.assertIs(initial['dedicated_instance_reviewed'], False)
            specific = 'native_auth_enforced_reviewed' if sid == 'tensorzero' else 'proxy_auth_reviewed'
            self.assertIs(initial[specific], False)
            for field in ('dedicated_instance_reviewed', specific):
                for bad in (None, False, 1, 'true'):
                    with self.subTest(service=sid, field=field, value=bad), self.assertRaises(VerdugoError):
                        build(sid, command(sid)['operation'], {}, self.services[sid] | {field: bad})
            for changes in ({'api_surface': 'cloud'}, {'auth_mode': 'public_no_credentials'}):
                with self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], {}, self.services[sid] | changes)

    def test_caller_cannot_select_routes_queries_workspaces_or_credentials(self):
        for sid in batch.SPECS:
            for p in ({'url': 'https://other.invalid'}, {'tenant': 'other'}, {'workspace': 'other'},
                      {'limit': 101}, {'page': 2}, {'offset': 100}, {'filters': {}},
                      {'function_name': 'other'}, {'headers': {}}, {'token': TOKEN},
                      {'query': 'arbitrary'}, {'method': 'DELETE'}):
                with self.subTest(service=sid, params=p), self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], p, self.services[sid])
            with self.assertRaises(VerdugoError):
                build(sid, 'inference.create', {}, self.services[sid])

    def test_projected_counts_and_empty_results(self):
        t = check('tensorzero', 'inferences.summary', REPLIES['tensorzero'])
        self.assertEqual(3, t['inferences_in_response'])
        self.assertEqual({'chat': 2, 'json': 1}, t['type_counts'])
        o = check('opik', 'projects.summary', REPLIES['opik'])
        self.assertEqual((2, 5, True), (o['projects_in_response'], o['projects_total_reported'], o['more_reported']))
        for result in (t, o):
            self.assertNotIn(PRIVATE, json.dumps(result))
            self.assertNotIn(TOKEN, json.dumps(result))
            self.assertFalse(result['live_verified'])
            self.assertFalse(result['raw_provider_payload_retained'])
            self.assertEqual(0, result['models_called'])
        self.assertEqual(0, check('tensorzero', 'inferences.summary', {'inferences': []})['inferences_in_response'])
        self.assertEqual(0, check('opik', 'projects.summary', {'page': 1, 'size': 0, 'total': 0, 'content': []})['projects_in_response'])

    def test_schema_and_response_bounds(self):
        bad = {
            'tensorzero': [{}, {'inferences': None}, {'inferences': [True]},
                          {'inferences': [{'type': 'unknown'}]}, {'inferences': [{'type': []}]},
                          {'inferences': [{'type': 'chat'}] * 101}],
            'opik': [{}, {'page': 1, 'size': 0, 'total': 0, 'content': None}],
        }
        for change in ({'page': 0}, {'page': 2}, {'page': True}, {'size': True},
                       {'size': 100}, {'total': -1}, {'total': 1}, {'total': 1.2},
                       {'content': [None]}, {'content': [{}] * 101}):
            bad['opik'].append(REPLIES['opik'] | change)
        for sid, replies in bad.items():
            for reply in replies:
                with self.subTest(service=sid, reply=reply), self.assertRaises(VerdugoError):
                    check(sid, command(sid)['operation'], reply)

    def test_socket_workflow_cli_mcp_restart_and_private_data_projection(self):
        spec = {'id': 'judgment-read-acceptance', 'steps': [
            {'id': sid, 'service': sid, 'operation': command(sid)['operation'], 'params': {}}
            for sid in batch.SPECS]}
        with tempfile.TemporaryDirectory() as tmp, wire(self.cfg, REPLIES, batch.SPECS) as server:
            path = str(Path(tmp) / 'state.sqlite3')
            with closing(Engine(path, self.cfg)) as engine:
                preview = invoke(engine, 'verdugo_workflow', {'workflow': spec})
                self.assertEqual([], preview['approval_batch'])
                self.assertEqual([], server['calls'])
                result = invoke(engine, 'verdugo_workflow', {'workflow': spec, 'execute': True})
                self.assertEqual('succeeded', result['state'])
                self.assertEqual(2, len(server['calls']))
                self.assertEqual('default', server['calls'][1]['headers']['Comet-Workspace'])
                self.assertEqual({'limit': 100, 'offset': 0}, json.loads(server['calls'][0]['body']))
                dump = '\n'.join(engine.db.iterdump())
                self.assertNotIn(PRIVATE, dump)
                self.assertNotIn(TOKEN, dump)
            with closing(Engine(path, self.cfg, transport=lambda *_: self.fail('read repeated'))) as engine:
                replay = workflow.run(engine, spec, True)
                self.assertEqual(result['steps'], replay['steps'])
            config = Path(tmp) / 'config.json'; config.write_text(json.dumps(self.cfg)); config.chmod(0o600)
            manifest = Path(tmp) / 'workflow.json'; manifest.write_text(json.dumps(spec))
            proc = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config),
                                   '--state', path, 'workflow', '@' + str(manifest), '--execute'],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual('succeeded', json.loads(proc.stdout)['state'])
            self.assertEqual(2, len(server['calls']))

    def test_socket_rejects_redirects_async_errors_and_oversized_or_invalid_json(self):
        with wire(self.cfg, REPLIES, batch.SPECS) as server:
            for sid in batch.SPECS:
                for status in (202, 204, 302, 401, 429, 500):
                    server['status'] = status
                    count = len(server['calls'])
                    with closing(Engine(':memory:', self.cfg)) as engine:
                        result = engine.execute(command(sid), True)
                        self.assertEqual('failed', result['state'])
                        self.assertNotIn(PRIVATE, '\n'.join(engine.db.iterdump()))
                    self.assertEqual(count + 1, len(server['calls']))
                server['status'] = 200
                for raw in (b'{not json', b'x' * (1024 * 1024 + 1)):
                    server['raw'] = raw
                    with closing(Engine(':memory:', self.cfg)) as engine:
                        self.assertEqual('failed', engine.execute(command(sid), True)['state'])
                server['raw'] = None
