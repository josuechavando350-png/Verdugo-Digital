"""Synthetic contracts and real loopback sockets; NOT upstream deployment acceptance."""
import copy
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from verdugo.__main__ import template
from verdugo.adapters import SPECS, build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo import connections, readiness_reads as batch, source_evidence, workflow

TOKEN = 'synthetic-token-v018-never-production'
PRIVATE = 'private-customer@example.invalid'
REPLIES = {
    'uptime-kuma': {'ok': True, 'monitors': [
        {'id': 1, 'name': PRIVATE, 'active': True, 'type': 'http', 'url': 'https://private.invalid/' + TOKEN},
        {'id': 2, 'name': 'Private service', 'active': False, 'type': 'port', 'tags': [{'name': PRIVATE}]}]},
    'gotenberg': {'status': 'up', 'details': {
        'chromium': {'status': 'up', 'timestamp': '2026-11-14T19:00:00.123456Z', 'debug': PRIVATE},
        'libreoffice': {'status': 'up', 'timestamp': '2026-11-14T19:00:00+00:00', 'extra': TOKEN}}},
}


def configured(tenant='nexus'):
    config = template(tenant)
    env = {}
    for sid in batch.SPECS:
        cfg = config['tenants'][tenant]['services'][sid]
        cfg.update(enabled=True, license_reviewed=True, version='synthetic-contract-only')
        cfg['api_access_reviewed' if sid == 'uptime-kuma' else 'proxy_auth_reviewed'] = True
        env[cfg['token_env']] = TOKEN
    return config, env


def command(sid, key=None, params=None):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])),
            'params': {} if params is None else params, 'key': key or 'read-' + sid}


def combined():
    return {'id': 'readiness-v018', 'steps': [
        {'id': 'monitors', **{k: v for k, v in command('uptime-kuma').items() if k != 'key'}},
        {'id': 'documents', **{k: v for k, v in command('gotenberg').items() if k != 'key'},
         'depends_on': ['monitors']}]}


class ReadinessContracts(unittest.TestCase):
    def setUp(self):
        self.config, env = configured()
        self.services = self.config['tenants']['nexus']['services']
        self.env = patch.dict(os.environ, env)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def request(self, sid, params=None):
        c = command(sid, params=params)
        return build(sid, c['operation'], c['params'], self.services[sid])

    def test_fixed_get_paths_auth_and_original_pins(self):
        for sid, specs in batch.SPECS.items():
            request = self.request(sid)
            p = request['public']
            self.assertEqual(specs, SPECS[sid])
            self.assertEqual(next(iter(specs.values())), (p['method'], urlsplit(p['url']).path))
            self.assertEqual('', urlsplit(p['url']).query)
            self.assertIsNone(p['body'])
            self.assertFalse(request['mutates'])
            self.assertEqual('Bearer ' + TOKEN, request['headers']['Authorization'])
            self.assertEqual(batch.PINNED_COMMITS[sid], source_evidence.report(sid)['source_commit_sha'])
            self.assertEqual(64, len(p['implementation_binding']))
            self.assertNotIn(TOKEN, json.dumps(p))

    def test_template_remains_disabled_unreviewed_and_no_license_exceptions(self):
        config = template('nexus')['tenants']['nexus']['services']
        for sid in batch.SPECS:
            self.assertIs(config[sid]['enabled'], False)
            self.assertIs(config[sid]['license_reviewed'], False)
            self.assertNotIn('license_policy_exception', config[sid])
        self.assertIs(config['uptime-kuma']['api_access_reviewed'], False)
        self.assertIs(config['gotenberg']['proxy_auth_reviewed'], False)

    def test_native_and_proxy_modes_cannot_be_interchanged(self):
        self.services['uptime-kuma']['auth_mode'] = 'reviewed_proxy_bearer'
        self.services['gotenberg']['auth_mode'] = 'native_api_key_bearer'
        for sid in batch.SPECS:
            with self.assertRaises(VerdugoError):
                self.request(sid)

    def test_review_requires_exact_true_not_truthy(self):
        for sid, key in [('uptime-kuma', 'api_access_reviewed'), ('gotenberg', 'proxy_auth_reviewed')]:
            for v in (False, None, 1, 'true', [], {}):
                self.services[sid][key] = v
                with self.subTest(sid=sid, value=v), self.assertRaises(VerdugoError):
                    self.request(sid)
            self.services[sid][key] = True

    def test_no_params_can_supply_url_method_tenant_credentials_or_filter(self):
        for sid in batch.SPECS:
            for params in ({'url': 'https://evil.invalid'}, {'method': 'POST'}, {'query': 'x'},
                           {'tenant': 'other'}, {'token': TOKEN}, {'monitor_id': 1}, {'limit': 1},
                           {'page': 2}, {'page': True}, {'page': 1.0}, {'page': '1'}):
                with self.subTest(sid=sid, params=params), self.assertRaises(VerdugoError):
                    self.request(sid, params)
            self.assertEqual(self.request(sid)['public'], self.request(sid, {'page': 1})['public'])
            with self.assertRaises(VerdugoError):
                build(sid, 'delete', {}, self.services[sid])

    def test_invalid_credentials_never_produce_request(self):
        for sid in batch.SPECS:
            for value in ('', 'key\nheader', 'x' * 8193):
                with patch.dict(os.environ, {self.services[sid]['token_env']: value}):
                    with self.assertRaises(VerdugoError):
                        self.request(sid)

    def test_counts_are_not_availability_or_pdf_conversion(self):
        kuma = check('uptime-kuma', 'monitors.summary', REPLIES['uptime-kuma'])
        self.assertEqual((2, 1, 1), (kuma['monitors_in_response'], kuma['enabled_monitors'], kuma['paused_monitors']))
        self.assertIs(kuma['target_availability_verified'], False)
        self.assertNotIn('up', kuma)
        pdf = check('gotenberg', 'health.summary', REPLIES['gotenberg'])
        self.assertEqual('up', pdf['reported_status'])
        self.assertEqual(2, pdf['dependency_checks_in_response'])
        self.assertIs(pdf['document_conversion_verified'], False)
        for r in (kuma, pdf):
            self.assertNotIn(PRIVATE, json.dumps(r))
            self.assertNotIn(TOKEN, json.dumps(r))
            self.assertIs(r['live_verified'], False)
            self.assertIs(r['production_certified'], False)
            self.assertIs(r['raw_provider_payload_retained'], False)

    def test_empty_native_list_valid_but_empty_object_not_success(self):
        self.assertEqual(0, check('uptime-kuma', 'monitors.summary', {'ok': True, 'monitors': []})['monitors_in_response'])
        for sid in batch.SPECS:
            for response in (None, [], {}, True, {'ok': True}, {'error': PRIVATE}):
                with self.subTest(sid=sid, response=response), self.assertRaises(VerdugoError) as error:
                    check(sid, command(sid)['operation'], response)
                self.assertNotIn(PRIVATE, str(error.exception))

    def test_monitor_id_active_and_types_validate_strictly(self):
        bad = [('id', True), ('id', 0), ('id', 2**53), ('id', '1'), ('active', 1),
               ('active', 'false'), ('type', None), ('type', ''), ('name', []), ('name', '')]
        for key, value in bad:
            data = copy.deepcopy(REPLIES['uptime-kuma'])
            data['monitors'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(VerdugoError):
                check('uptime-kuma', 'monitors.summary', data)

    def test_monitor_duplicates_overflow_and_error_envelope_rejected(self):
        row = REPLIES['uptime-kuma']['monitors'][0]
        for data in ({'ok': True, 'monitors': [row, row]}, {'ok': False, 'monitors': []},
                     {'ok': 1, 'monitors': []}, {'ok': True, 'monitors': [row]*1001}):
            with self.assertRaises(VerdugoError):
                check('uptime-kuma', 'monitors.summary', data)

    def test_monitor_boundary_is_not_silently_truncated(self):
        rows = [dict(id=i+1, name='synthetic', type='http', active=False) for i in range(1000)]
        self.assertEqual(1000, check('uptime-kuma', 'monitors.summary', {'ok': True, 'monitors': rows})['paused_monitors'])

    def test_gotenberg_unhealthy_or_inconsistent_status_not_passed(self):
        for field, value in [('status', 'down'), ('details', []), ('details', None)]:
            data = copy.deepcopy(REPLIES['gotenberg']); data[field] = value
            with self.assertRaises(VerdugoError): check('gotenberg', 'health.summary', data)
        for changes in ({'status': 'down'}, {'error': PRIVATE}, {'status': True}):
            data = copy.deepcopy(REPLIES['gotenberg']); data['details']['chromium'].update(changes)
            with self.assertRaises(VerdugoError) as error: check('gotenberg', 'health.summary', data)
            self.assertNotIn(PRIVATE, str(error.exception))

    def test_gotenberg_timestamp_and_bound_validated_without_retention(self):
        for stamp in (None, 1, 'not-a-date', '2026-11-14T00:00:00', 'x'*65):
            data = copy.deepcopy(REPLIES['gotenberg']); data['details']['chromium']['timestamp'] = stamp
            with self.assertRaises(VerdugoError): check('gotenberg', 'health.summary', data)
        detail = REPLIES['gotenberg']['details']['chromium']
        with self.assertRaises(VerdugoError):
            check('gotenberg', 'health.summary', {'status': 'up', 'details': {str(i): detail for i in range(33)}})

    def test_revocation_blocks_even_cached_operation(self):
        for sid, field in [('uptime-kuma', 'api_access_reviewed'), ('gotenberg', 'proxy_auth_reviewed')]:
            calls = []
            with closing(Engine(':memory:', self.config, transport=lambda *_: calls.append(1) or REPLIES[sid])) as engine:
                self.assertEqual('succeeded', engine.execute(command(sid), True)['state'])
                self.services[sid][field] = False
                with self.assertRaises(VerdugoError): engine.execute(command(sid), True)
                self.services[sid][field] = True
            self.assertEqual(1, len(calls))

    def test_version_or_key_change_cannot_replay_old_fingerprint(self):
        for sid in batch.SPECS:
            cfg = self.services[sid]
            with closing(Engine(':memory:', self.config)) as engine:
                engine.plan(command(sid))
                cfg['version'] = 'different-version'
                with self.assertRaises(VerdugoError): engine.plan(command(sid))
                cfg['version'] = 'synthetic-contract-only'
                with patch.dict(os.environ, {cfg['token_env']: 'different-token'}):
                    with self.assertRaises(VerdugoError): engine.plan(command(sid))

    def test_schema_error_persists_no_raw_secret_or_customer(self):
        with closing(Engine(':memory:', self.config, transport=lambda *_: {'ok': False, 'error': PRIVATE, 'token': TOKEN})) as engine:
            r = engine.execute(command('uptime-kuma'), True)
            self.assertEqual('failed', r['state'])
            dump = '\n'.join(engine.db.iterdump())
            self.assertNotIn(PRIVATE, dump); self.assertNotIn(TOKEN, dump)

    def test_viewer_preview_cannot_send_requests(self):
        with closing(Engine(':memory:', self.config, role='viewer', transport=lambda *_: self.fail('network'))) as engine:
            self.assertEqual('planned', engine.execute(command('gotenberg'))['state'])
            with self.assertRaises(VerdugoError): engine.execute(command('gotenberg'), True)


class ReadinessWireTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.sqlite3'
        self.config, env = configured()
        other, second = configured('client2'); self.config['tenants'].update(other['tenants'])
        self.env = patch.dict(os.environ, env | second); self.env.start()
        self.calls = []; self.status = 200; self.override = None
        owner = self
        self.routes = {next(iter(v.values()))[1]: s for s, v in batch.SPECS.items()}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                sid = owner.routes.get(urlsplit(self.path).path)
                auth = self.headers.get('Authorization')
                owner.calls.append((sid, self.path, auth))
                self.send_response(owner.status if sid and auth == 'Bearer ' + TOKEN else 401)
                body = owner.override if owner.override is not None else json.dumps(REPLIES.get(sid, {})).encode()
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                if owner.status == 302: self.send_header('Location', '/do-not-follow')
                self.end_headers()
                try: self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError): pass
            def do_POST(self):
                owner.calls.append(('WRITE', self.path, None)); self.send_response(405); self.end_headers()
        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        for tenant in self.config['tenants'].values():
            for sid in batch.SPECS:
                tenant['services'][sid].update(base_url='http://127.0.0.1:%d' % self.server.server_port, allow_local_http=True)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
        self.env.stop(); self.tmp.cleanup()

    def test_shared_engine_mcp_workflow_and_sqlite_restart(self):
        with closing(Engine(self.path, self.config)) as engine:
            self.assertEqual('planned', invoke(engine, 'verdugo_workflow', {'workflow': combined()})['state'])
            self.assertFalse(self.calls)
            result = invoke(engine, 'verdugo_workflow', {'workflow': combined(), 'execute': True})
            self.assertEqual('succeeded', result['state'])
            self.assertNotIn(PRIVATE, '\n'.join(engine.db.iterdump()))
            self.assertNotIn(TOKEN, '\n'.join(engine.db.iterdump()))
        with closing(Engine(self.path, self.config)) as reopened:
            self.assertEqual(result, workflow.run(reopened, combined(), True))
            self.assertEqual(0, reopened.status()['live_verified'])
        self.assertEqual(2, len(self.calls))

    def test_same_workflow_in_other_tenant_does_not_reuse_private_results(self):
        for tenant in ('nexus', 'client2'):
            with closing(Engine(self.path, self.config, tenant=tenant)) as engine:
                self.assertEqual('succeeded', workflow.run(engine, combined(), True)['state'])
        self.assertEqual(4, len(self.calls))

    def test_review_preflight_blocks_entire_workflow(self):
        self.config['tenants']['nexus']['services']['gotenberg']['proxy_auth_reviewed'] = False
        with closing(Engine(self.path, self.config)) as engine:
            with self.assertRaises(VerdugoError): workflow.run(engine, combined(), True)
        self.assertFalse(self.calls)

    def test_http_requires_200_not_redirect_async_or_error(self):
        for status in (202, 204, 302, 401, 403, 429, 500, 503):
            self.status = status
            with closing(Engine(':memory:', self.config)) as engine:
                self.assertEqual('failed', engine.execute(command('gotenberg'), True)['state'])
        self.assertEqual(8, len(self.calls))
        self.assertTrue(all(path == '/health' for _, path, _ in self.calls))

    def test_oversize_response_fails_closed(self):
        self.override = b' '*(1024*1024+1)
        with closing(Engine(':memory:', self.config)) as engine:
            self.assertEqual('failed', engine.execute(command('uptime-kuma'), True)['state'])

    def test_malformed_json_fails_without_retaining_text(self):
        self.override = ('<html>' + PRIVATE).encode()
        with closing(Engine(self.path, self.config)) as engine:
            self.assertEqual('failed', engine.execute(command('uptime-kuma'), True)['state'])
            self.assertNotIn(PRIVATE, '\n'.join(engine.db.iterdump()))

    def test_cli_uses_same_engine_and_replay_does_not_call_again(self):
        path = Path(self.tmp.name) / 'config.json'; path.write_text(json.dumps(self.config))
        args = [sys.executable, '-m', 'verdugo', '--config', str(path), '--state', str(self.path),
                'run', json.dumps(command('uptime-kuma')), '--execute']
        first = subprocess.run(args, text=True, capture_output=True, timeout=15)
        self.assertEqual(0, first.returncode, first.stderr)
        r = json.loads(first.stdout); self.assertEqual('succeeded', r['state'])
        self.assertEqual(2, r['result']['monitors_in_response'])
        self.assertNotIn(PRIVATE, first.stdout + first.stderr); self.assertNotIn(TOKEN, first.stdout + first.stderr)
        again = subprocess.run(args, text=True, capture_output=True, timeout=15)
        self.assertTrue(json.loads(again.stdout)['replayed'])
        self.assertEqual(1, len(self.calls))


class ReadinessInventoryTests(unittest.TestCase):
    def test_manifest_source_pins_and_plan_are_honest(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root/'sources/contracts-v018.json').read_text())
        self.assertEqual(set(batch.SPECS), {r['id'] for r in manifest['records']})
        for item in manifest['records']:
            self.assertEqual(batch.PINNED_COMMITS[item['id']], item['commit'])
            self.assertIs(item['live_verified'], False)
            for source in item['files']:
                self.assertRegex(source['git_blob_sha'], r'^[a-f0-9]{40}$')
                self.assertIn('/blob/'+item['commit']+'/', source['source_url'])
        plan = json.loads((root/'docs/plan_conexion.json').read_text())
        self.assertEqual(set(batch.SPECS), {p['id'] for p in plan['implemented_v018']})
        self.assertEqual(1, plan['pending'])
        self.assertEqual(1, len(plan['items']))
        self.assertTrue(all(p['live_verified'] is False for p in plan['implemented_v018']))

    def test_code_derived_counts_never_certify_live_services(self):
        self.assertEqual({'conectado': 243, 'pendiente': 1, 'pieza_de_construccion': 56, 'excluido': 22}, connections.summary()['states'])
        with closing(Engine(':memory:')) as engine:
            status = engine.status()
        self.assertEqual(104, status['api_adapters_implemented'])
        self.assertEqual(108, status['api_actions_implemented'])
        self.assertEqual(262, status['total_adapters_implemented'])
        self.assertEqual(0, status['live_verified'])

if __name__ == '__main__':
    unittest.main()
