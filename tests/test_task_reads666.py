"""KAG's fixed read POST: task correlation, private envelopes, and shared Engine replay."""
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

from verdugo import task_reads666 as batch, product
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo.registry666 import read_registry
from test_operations_reads_v019 import wire, PRIVATE

TOKEN = 'synthetic-kag-proxy-credential'
TASK = 'a6c437f3-71f8-45d7-95fe-218d9ee24567'
OTHER = 'b6c437f3-71f8-45d7-95fe-218d9ee24567'
TASK_ENV = 'VERDUGO_NEXUS_KAG_TASK_ID'
REPLY = {'task_id': TASK, 'status': 'completed', 'result': {'private_answer': PRIVATE, 'token': TOKEN}}


def configured():
    cfg = template('nexus')
    cfg['tenants']['nexus']['services']['kag'].update(
        enabled=True, license_reviewed=True, version='synthetic-666', task_id_env=TASK_ENV,
        **{gate: True for gate in batch.GATES})
    return cfg


class TaskReads666Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = configured()
        self.service = self.cfg['tenants']['nexus']['services']['kag']
        self.env = patch.dict(os.environ, {self.service['token_env']: TOKEN, TASK_ENV: TASK})
        self.env.start(); self.addCleanup(self.env.stop)

    def command(self, key='task-read'):
        return {'service': 'kag', 'operation': 'task.summary', 'params': {}, 'key': key}

    def request(self):
        return build('kag', 'task.summary', {}, self.service)

    def test_fixed_route_private_nested_original_envelope_and_no_submit(self):
        req = self.request(); public = req['public']
        self.assertEqual(('POST', 'https://example.invalid/process'), (public['method'], public['url']))
        self.assertEqual('Bearer ' + TOKEN, req['headers']['Authorization'])
        self.assertEqual('application/json', req['headers']['Content-Type'])
        self.assertFalse(req['mutates']); self.assertIsNone(public['body'])
        self.assertFalse(public['authentication_policy']['upstream_native_auth'])
        for secret in (TASK, TOKEN, 'Bearer ' + TOKEN): self.assertNotIn(secret, json.dumps(public))
        outer = json.loads(batch.body_bytes(req))
        self.assertEqual({'features'}, set(outer)); self.assertEqual({'in_string'}, set(outer['features']))
        self.assertEqual({'req_id': TASK, 'cmd': 'query', 'app_id': 0, 'project_id': 0,
                          'req': '{}', 'config': '{}'}, json.loads(outer['features']['in_string']))
        self.assertEqual('task.summary', product.read_operations()['kag'])

    def test_disabled_defaults_proxy_scope_gates_and_license_gate(self):
        default = template('nexus')['tenants']['nexus']['services']['kag']
        for key in ('enabled', 'license_reviewed', *batch.GATES): self.assertIs(default[key], False)
        self.assertIsNone(default['task_id_env'])
        for key in batch.GATES:
            for value in (False, None, 1, 'true'):
                with self.subTest(key=key, value=value), self.assertRaises(VerdugoError):
                    build('kag', 'task.summary', {}, self.service | {key: value})
        for change in ({'api_surface': 'cloud'}, {'auth_mode': 'native_bearer'}, {'auth_mode': 'none'}):
            with self.assertRaises(VerdugoError): build('kag', 'task.summary', {}, self.service | change)
        for flag in ('enabled', 'license_reviewed'):
            cfg = copy.deepcopy(self.cfg); cfg['tenants']['nexus']['services']['kag'][flag] = False
            with closing(Engine(':memory:', cfg)) as e, self.assertRaises(VerdugoError):
                e.plan(self.command())

    def test_caller_cannot_choose_task_query_destination_model_or_command(self):
        for params in ({'task_id': OTHER}, {'req_id': OTHER}, {'cmd': 'submit'}, {'query': PRIVATE},
                       {'url': 'https://other.invalid'}, {'host_addr': 'http://127.0.0.1'},
                       {'tenant': 'other'}, {'project_id': 42}, {'config': {}}, {'token': TOKEN},
                       {'method': 'DELETE'}, {'features': {'in_string': '{}'}}):
            with self.subTest(params=params), self.assertRaises(VerdugoError):
                build('kag', 'task.summary', params, self.service)
        with self.assertRaises(VerdugoError): build('kag', 'task.submit', {}, self.service)

    def test_private_id_reference_and_canonical_uuid4_validation(self):
        for name in (None, 'HOME', 'VERDUGO_x', TASK, 'VERDUGO_../../secret'):
            with self.assertRaises(VerdugoError):
                build('kag', 'task.summary', {}, self.service | {'task_id_env': name})
        for value in ('', TASK.upper(), TASK + '\n', 'x' * 36, TASK.replace('-4', '-1', 1),
                      '00000000-0000-4000-0000-000000000000'):
            with patch.dict(os.environ, {TASK_ENV: value}), self.assertRaises(VerdugoError): self.request()

    def test_private_serializer_rejects_overrides_and_binding_changes(self):
        req = self.request()
        for change in ({'service': 'other'}, {'operation': 'task.submit'}, {'method': 'GET'},
                       {'url': 'https://example.invalid/submit'}, {'url': 'https://example.invalid/process?cmd=submit'},
                       {'url': 'https://example.invalid/process#submit'}, {'body': {'cmd': 'submit'}},
                       {'query_command': 'submit'}, {'task_binding': '0' * 64}):
            with self.assertRaises(VerdugoError): batch.body_bytes(req | {'public': req['public'] | change})
        for private in ({}, {'task_id': OTHER}, {'task_id': TASK, 'cmd': 'submit'}):
            with self.assertRaises(VerdugoError): batch.body_bytes(req | {'private_task': private})
        with self.assertRaises(VerdugoError): batch.body_bytes(req | {'mutates': True})

    def test_correlated_states_project_only_counts_and_preserve_failed_ambiguity(self):
        public = self.request()['public']
        for state, result in [('running', None), ('completed', REPLY['result']),
                              ('failed', 'Result not found or expired'), ('failed', PRIVATE)]:
            actual = check('kag', 'task.summary', REPLY | {'status': state, 'result': result}, public)
            self.assertEqual(1, actual['tasks_observed'])
            self.assertEqual(1, sum(actual[k] for k in ('running_reported', 'completed_reported', 'failed_reported')))
            self.assertEqual(1, actual[state + '_reported'])
            self.assertEqual(state == 'failed', actual['failed_may_mean_missing_or_expired'])
            for secret in (TASK, PRIVATE, TOKEN, 'not found'): self.assertNotIn(secret, json.dumps(actual))
            for flag in ('completion_verified', 'result_quality_verified', 'task_identifier_retained',
                         'raw_provider_payload_retained', 'live_verified', 'production_certified'):
                self.assertIs(actual[flag], False)
            self.assertEqual((0, 0), (actual['tasks_submitted'], actual['models_called']))

    def test_wrong_task_malformed_status_or_unbound_response_fails_closed(self):
        public = self.request()['public']
        bad = [{}, [], None, REPLY | {'task_id': OTHER}, REPLY | {'task_id': True},
               REPLY | {'status': True}, REPLY | {'status': []}, REPLY | {'status': 'init'},
               REPLY | {'status': 'running'}, REPLY | {'status': 'failed'},
               {k: v for k, v in REPLY.items() if k != 'result'}]
        for response in bad:
            with self.subTest(response=response), self.assertRaises(VerdugoError):
                check('kag', 'task.summary', response, public)
        for req in (None, {}, public | {'task_binding': '0' * 64}):
            with self.assertRaises(VerdugoError): check('kag', 'task.summary', REPLY, req)

    def test_product_mcp_cli_sqlite_restart_and_private_envelope(self):
        spec = {'id': 'kag-unified', 'services': ['kag'], 'dataset': 'demo', 'currency': 'MXN'}
        with tempfile.TemporaryDirectory() as tmp, wire(self.cfg, {'kag': REPLY}, batch.SPECS,
                {'kag': ('Authorization', 'Bearer ' + TOKEN)}) as server:
            state = str(Path(tmp) / 'state.sqlite3')
            with closing(Engine(state, self.cfg)) as e:
                preview = invoke(e, 'verdugo_product_run', {'request': spec})
                self.assertEqual('planned', preview['state']); self.assertEqual([], preview['approval_batch'])
                self.assertFalse(server['calls'])
                result = invoke(e, 'verdugo_product_run', {'request': spec, 'execute': True})
                self.assertEqual('succeeded', result['state'], result)
                text = '\n'.join(e.db.iterdump()) + json.dumps(preview) + json.dumps(result)
                for secret in (TASK, PRIVATE, TOKEN): self.assertNotIn(secret, text)
            self.assertEqual(1, len(server['calls']))
            call = server['calls'][0]
            self.assertEqual(('POST', '/process'), (call['method'], call['path']))
            self.assertEqual('query', json.loads(json.loads(call['body'])['features']['in_string'])['cmd'])
            with closing(Engine(state, self.cfg, transport=lambda *_: self.fail('network replay'))) as e:
                replay = product.observe(e, spec, True)
                self.assertEqual('succeeded', replay['state'])
            config = Path(tmp) / 'config.json'; config.write_text(json.dumps(self.cfg)); config.chmod(0o600)
            manifest = Path(tmp) / 'request.json'; manifest.write_text(json.dumps(spec))
            cli = subprocess.run([sys.executable, '-m', 'verdugo', '--config', str(config), '--state', state,
                                  'product-run', '@' + str(manifest), '--execute'], capture_output=True, text=True)
            self.assertEqual(0, cli.returncode, cli.stderr)
            for secret in (TASK, PRIVATE, TOKEN): self.assertNotIn(secret, cli.stdout + cli.stderr)
            self.assertEqual(1, len(server['calls']))

    def test_http_errors_limits_and_response_task_mismatch_do_not_persist_private_data(self):
        replies = {'kag': copy.deepcopy(REPLY)}
        with wire(self.cfg, replies, batch.SPECS, {'kag': ('Authorization', 'Bearer ' + TOKEN)}) as server, \
                closing(Engine(':memory:', self.cfg)) as e:
            for status in (202, 204, 302, 401, 403, 500):
                server['status'] = status
                self.assertEqual('failed', e.execute(self.command('status-' + str(status)), True)['state'])
            server['status'] = 200
            for index, raw in enumerate((b'not-json', b'x' * (1024 * 1024 + 1))):
                server['raw'] = raw
                self.assertEqual('failed', e.execute(self.command('raw-' + str(index)), True)['state'])
            server['raw'] = None; replies['kag']['task_id'] = OTHER
            self.assertEqual('failed', e.execute(self.command('wrong-task'), True)['state'])
            dump = '\n'.join(e.db.iterdump())
            for secret in (TASK, OTHER, PRIVATE, TOKEN): self.assertNotIn(secret, dump)

    def test_task_credential_or_gate_change_invalidates_replay(self):
        with closing(Engine(':memory:', self.cfg, transport=lambda *_: copy.deepcopy(REPLY))) as e:
            self.assertEqual('succeeded', e.execute(self.command(), True)['state'])
            for env in ({TASK_ENV: OTHER}, {self.service['token_env']: TOKEN + '-changed'}):
                with patch.dict(os.environ, env), self.assertRaises(VerdugoError): e.execute(self.command(), True)
            self.service['task_scope_reviewed'] = False
            with self.assertRaises(VerdugoError): e.execute(self.command(), True)

    def test_original_file_receipts_and_no_full_server_claim(self):
        r = json.loads(batch.CONTRACT.read_text())['records'][0]
        pinned = next(x for x in read_registry()['records'] if x['id'] == 'kag')
        self.assertEqual(pinned['commit_sha'], r['commit'])
        self.assertTrue(r['license_text_read']); self.assertFalse(r['original_server_executed'])
        self.assertFalse(r['live_verified']); self.assertEqual(4, len(r['files']))
        for f in r['files']:
            self.assertRegex(f['git_blob_sha'], '^[a-f0-9]{40}$')
            self.assertRegex(f['sha256'], '^[a-f0-9]{64}$')
            self.assertIn('/blob/' + r['commit'] + '/', f['source_url'])
