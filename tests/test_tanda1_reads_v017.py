"""Synthetic contract/loopback tests, NOT live upstream or production acceptance."""
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from verdugo.__main__ import template, main
from verdugo.adapters import SPECS, build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check
from verdugo.transport import send
from verdugo import connections, source_evidence, tanda1_reads as batch, workflow
from contextlib import redirect_stdout, closing

TOKEN = 'synthetic-private-token-never-real'
PRIVATE = 'private-company-contact@example.invalid'
REPLIES = {
    'openrefine': {'projects': {'123': {'name': PRIVATE, 'password': TOKEN}},
                   'customMetadataColumns': [PRIVATE]},
    'steel-browser': {'sessions': [
        {'id': '00000000-0000-4000-8000-000000000001', 'status': 'live',
         'websocketUrl': 'wss://private.invalid/' + TOKEN, 'cookies': PRIVATE},
        {'id': '00000000-0000-4000-8000-000000000002', 'status': 'released'}]},
    'crawl4ai': {'available_actions': {'wait_for_selector': {
        'hook_point': 'after_goto', 'description': PRIVATE, 'params_schema': {'private': PRIVATE}}},
        'usage': {'field': 'hooks', 'max_hooks': 10},
        'timeout_limits': {'min': 1, 'default': 30, 'max': 120}},
    'fides': {'items': [{'name': PRIVATE, 'key': 'private-policy', 'rules': [{'secret': TOKEN}]}],
              'total': 1, 'page': 1, 'size': 50, 'pages': 1},
}
COUNT_FIELDS = {'openrefine': 'projects_in_response', 'steel-browser': 'sessions_in_response',
                'crawl4ai': 'actions_available', 'fides': 'policies_in_response'}


def configured(tenant='nexus'):
    config = template(tenant)
    env = {}
    for sid in batch.SPECS:
        cfg = config['tenants'][tenant]['services'][sid]
        cfg.update(enabled=True, license_reviewed=True, version='synthetic-contract-only')
        if sid in batch.PROXY_ONLY:
            cfg['proxy_auth_reviewed'] = True  # fixture authorization, never a production approval
        env[cfg['token_env']] = TOKEN
    return config, env


def command(sid, key=None, params=None):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])),
            'params': {} if params is None else params, 'key': key or 'read-' + sid}


def combined():
    return {'id': 'batch1-read-overview', 'steps': [
        {'id': sid, 'service': sid, 'operation': next(iter(batch.SPECS[sid])),
         'params': {}, 'depends_on': [] if index == 0 else [list(batch.SPECS)[index-1]]}
        for index, sid in enumerate(batch.SPECS)]}


class ContractTests(unittest.TestCase):
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

    def test_four_get_contracts_exact_source_pins(self):
        self.assertEqual({'openrefine', 'steel-browser', 'crawl4ai', 'fides'}, set(batch.SPECS))
        for sid, ops in batch.SPECS.items():
            self.assertEqual(ops, SPECS[sid])
            self.assertEqual(batch.PINNED_COMMITS[sid], source_evidence.report(sid)['source_commit_sha'])
            request = self.request(sid)
            public = request['public']
            url = urlsplit(public['url'])
            self.assertEqual(next(iter(ops.values())), (public['method'], url.path))
            self.assertEqual({'page': ['1'], 'size': ['50']} if sid == 'fides' else {}, parse_qs(url.query))
            self.assertIsNone(public['body'])
            self.assertFalse(request['mutates'])
            self.assertEqual('Bearer ' + TOKEN, request['headers']['Authorization'])
            self.assertEqual(64, len(public['implementation_binding']))
            self.assertNotIn(TOKEN, json.dumps(public))
            self.assertEqual('conectado', connections.state(sid))

    def test_all_stay_disabled_and_unreviewed_in_operator_template(self):
        values = template('nexus')['tenants']['nexus']['services']
        for sid in batch.SPECS:
            self.assertIs(values[sid]['enabled'], False)
            self.assertIs(values[sid]['license_reviewed'], False)
            self.assertNotIn('license_policy_exception', values[sid])
            if sid in batch.PROXY_ONLY:
                self.assertIs(values[sid]['proxy_auth_reviewed'], False)
        with closing(Engine(':memory:', template('nexus'))) as engine:
            with self.assertRaisesRegex(VerdugoError, 'disabled'):
                engine.execute(command('fides'), True)

    def test_proxy_review_required_exact_bool_before_network(self):
        for sid in batch.PROXY_ONLY:
            for value in (False, None, 'true', 1, {}, []):
                self.services[sid]['proxy_auth_reviewed'] = value
                with self.subTest(sid=sid, value=value), self.assertRaises(VerdugoError):
                    self.request(sid)
            self.services[sid]['proxy_auth_reviewed'] = True
            self.services[sid]['auth_mode'] = 'bearer'
            with self.assertRaises(VerdugoError):
                self.request(sid)

    def test_fides_does_not_silently_reuse_proxy_mode(self):
        self.services['fides']['auth_mode'] = 'reviewed_proxy_bearer'
        with self.assertRaises(VerdugoError):
            self.request('fides')

    def test_destination_params_credential_method_query_and_tenant_refused(self):
        for sid in batch.SPECS:
            for params in ({'url': 'https://evil.invalid'}, {'method': 'POST'}, {'query': 'mutate'},
                           {'token': TOKEN}, {'tenant': 'other'}, {'limit': 10000},
                           {'page': 2}, {'page': True}, {'page': '1'}, {'page': 1.0},
                           {'hooks': ['execute-code']}, {'operation': 'delete'}):
                with self.subTest(sid=sid, params=params), self.assertRaises(VerdugoError):
                    self.request(sid, params)
            with self.assertRaises(VerdugoError):
                build(sid, 'delete', {}, self.services[sid])

    def test_projection_discards_personal_fields_ids_and_secrets(self):
        for sid, reply in REPLIES.items():
            with self.subTest(sid=sid):
                result = check(sid, command(sid)['operation'], reply)
                encoded = json.dumps(result)
                self.assertNotIn(PRIVATE, encoded)
                self.assertNotIn(TOKEN, encoded)
                self.assertNotIn('private-policy', encoded)
                self.assertNotIn('00000000-0000', encoded)
                self.assertIs(result['raw_provider_payload_retained'], False)
                self.assertIs(result['live_verified'], False)
                self.assertIs(result['production_certified'], False)
                self.assertGreater(result[COUNT_FIELDS[sid]], 0)
        self.assertIs(check('crawl4ai', 'hooks.summary', REPLIES['crawl4ai'])['crawl_executed'], False)

    def test_invalid_top_level_never_becomes_zero_success(self):
        for sid in batch.SPECS:
            for value in (None, [], {}, 'OK', 5, {'error': PRIVATE}, {'success': True}):
                with self.subTest(sid=sid, value=value), self.assertRaises(VerdugoError) as error:
                    check(sid, command(sid)['operation'], value)
                self.assertNotIn(PRIVATE, str(error.exception))

    def test_openrefine_empty_project_map_and_long_id_bounds(self):
        self.assertEqual(0, check('openrefine', 'projects.count', {'projects': {}})['projects_in_response'])
        for projects in ([], {'alice@example.invalid': {}}, {'0': {}}, {'9223372036854775808': {}},
                         {'123': []}, {str(n+1): {} for n in range(1001)}):
            with self.assertRaises(VerdugoError):
                check('openrefine', 'projects.count', {'projects': projects})

    def test_steel_statuses_are_enumerated_and_duplicate_ids_rejected(self):
        result = check('steel-browser', 'sessions.summary', REPLIES['steel-browser'])
        self.assertEqual({'failed': 0, 'idle': 0, 'live': 1, 'released': 1}, result['status_counts'])
        original = REPLIES['steel-browser']['sessions'][0]
        for sessions in ([{}], [dict(original, status=PRIVATE)], [dict(original, id='private-id')],
                         [original, original], [original]*1001):
            with self.assertRaises(VerdugoError):
                check('steel-browser', 'sessions.summary', {'sessions': sessions})

    def test_crawl4ai_requires_registry_shape_and_bounded_numeric_limits(self):
        for mutation in ({'available_actions': []}, {'available_actions': {'run': {}}},
                         {'usage': {'field': 'exec', 'max_hooks': 10}},
                         {'usage': {'field': 'hooks', 'max_hooks': True}},
                         {'timeout_limits': {'min': 30, 'default': 1, 'max': 120}},
                         {'timeout_limits': {'min': 1, 'default': 30, 'max': 10**9}}):
            with self.assertRaises(VerdugoError):
                check('crawl4ai', 'hooks.summary', REPLIES['crawl4ai'] | mutation)

    def test_fides_pagination_and_item_types_fail_closed(self):
        for mutation in ({'items': [{}]}, {'total': -1}, {'total': True}, {'total': '1'},
                         {'total': 1.5}, {'total': 2}, {'page': 2}, {'size': 1000},
                         {'size': True}, {'items': [{}]*51}):
            with self.assertRaises(VerdugoError):
                check('fides', 'policies.count', REPLIES['fides'] | mutation)
        empty = {'items': [], 'page': 1, 'size': 50, 'total': 0}
        self.assertEqual(0, check('fides', 'policies.count', empty)['policies_in_response'])
        many = {'items': [{'name': PRIVATE}]*50, 'page': 1, 'size': 50, 'total': 51}
        result = check('fides', 'policies.count', many)
        self.assertEqual(50, result['policies_in_response'])
        self.assertTrue(result['more_pages'])

    def test_config_and_credential_changes_change_fingerprint(self):
        with closing(Engine(':memory:', self.config)) as engine:
            first = engine.plan(command('fides'))
            self.services['fides']['version'] = 'different-reviewed-fixture'
            with self.assertRaises(VerdugoError):
                engine.plan(command('fides'))
            self.services['fides']['version'] = 'synthetic-contract-only'
            with patch.dict(os.environ, {self.services['fides']['token_env']: 'another-secret'}):
                with self.assertRaises(VerdugoError):
                    engine.plan(command('fides'))
            self.assertNotIn(TOKEN, json.dumps(first))

    def test_revoked_proxy_review_blocks_even_a_previously_cached_result(self):
        calls = []
        with closing(Engine(':memory:', self.config, transport=lambda req, cfg: calls.append(1) or REPLIES['openrefine'])) as engine:
            self.assertEqual('succeeded', engine.execute(command('openrefine'), True)['state'])
            self.services['openrefine']['proxy_auth_reviewed'] = False
            with self.assertRaises(VerdugoError):
                engine.execute(command('openrefine'), True)
        self.assertEqual(1, len(calls))

    def test_schema_errors_persist_only_generic_failure(self):
        with closing(Engine(':memory:', self.config, transport=lambda req, cfg: {'error': PRIVATE})) as engine:
            result = engine.execute(command('fides'), True)
            self.assertEqual('failed', result['state'])
            self.assertNotIn(PRIVATE, '\n'.join(engine.db.iterdump()))
            self.assertNotIn(TOKEN, '\n'.join(engine.db.iterdump()))
            self.assertTrue(engine.execute(command('fides'), True)['replayed'])

    def test_viewer_can_preview_but_cannot_call_provider(self):
        with closing(Engine(':memory:', self.config, role='viewer', transport=lambda *_: self.fail('network'))) as engine:
            self.assertEqual('planned', engine.execute(command('fides'))['state'])
            with self.assertRaises(VerdugoError):
                engine.execute(command('fides'), True)


class LoopbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.sqlite3'
        self.config, env = configured()
        other, second_env = configured('client2')
        self.config['tenants'].update(other['tenants'])
        self.env = patch.dict(os.environ, env | second_env)
        self.env.start()
        self.calls = []
        self.status = 200
        self.override = None
        owner = self
        self.routes = {next(iter(v.values()))[1]: s for s, v in batch.SPECS.items()}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                sid = owner.routes.get(urlsplit(self.path).path)
                auth = self.headers.get('Authorization')
                owner.calls.append((sid, self.path, auth))
                status = owner.status if sid and auth == 'Bearer ' + TOKEN else 401
                body = owner.override if owner.override is not None else json.dumps(REPLIES.get(sid, {})).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                if status == 302:
                    self.send_header('Location', 'http://127.0.0.1:%d/evil' % owner.server.server_port)
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                owner.calls.append(('WRITE', self.path, None))
                self.send_response(405)
                self.end_headers()

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        for tenant in self.config['tenants'].values():
            for sid in batch.SPECS:
                tenant['services'][sid].update(base_url='http://127.0.0.1:%d' % self.server.server_port, allow_local_http=True)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.env.stop()
        self.tmp.cleanup()

    def test_combined_engine_workflow_persists_and_resumes_without_second_calls(self):
        spec = combined()
        with closing(Engine(self.path, self.config)) as engine:
            preview = invoke(engine, 'verdugo_workflow', {'workflow': spec})
            self.assertEqual('planned', preview['state'])
            self.assertFalse(self.calls)
            result = invoke(engine, 'verdugo_workflow', {'workflow': spec, 'execute': True})
            self.assertEqual('succeeded', result['state'])
            self.assertEqual(set(batch.SPECS), set(result['steps']))
            dump = '\n'.join(engine.db.iterdump())
            self.assertNotIn(PRIVATE, dump)
            self.assertNotIn(TOKEN, dump)
            self.assertNotIn('private-policy', dump)
        self.assertEqual(4, len(self.calls))
        with closing(Engine(self.path, self.config)) as reopened:
            self.assertEqual(result, workflow.run(reopened, spec, True))
            self.assertEqual(0, reopened.status()['live_verified'])
        self.assertEqual(4, len(self.calls))
        with closing(Engine(self.path, self.config, tenant='client2')) as another:
            self.assertEqual('succeeded', workflow.run(another, spec, True)['state'])
        self.assertEqual(8, len(self.calls))

    def test_missing_proxy_review_stops_whole_workflow_before_any_request(self):
        self.config['tenants']['nexus']['services']['crawl4ai']['proxy_auth_reviewed'] = False
        with closing(Engine(self.path, self.config)) as engine:
            with self.assertRaises(VerdugoError):
                workflow.run(engine, combined(), True)
        self.assertFalse(self.calls)

    def test_http_requires_synchronous_200_and_does_not_follow_redirects(self):
        for status in (202, 204, 302, 401, 403, 500):
            self.status = status
            with closing(Engine(':memory:', self.config)) as engine:
                out = engine.execute(command('fides'), True)
                self.assertEqual('failed', out['state'])
        self.assertEqual(6, len(self.calls))
        self.assertTrue(all('/api/v1/dsr/policy?' in path for _, path, _ in self.calls))

    def test_response_larger_than_one_mib_is_rejected(self):
        self.override = b' ' * (1024*1024+1)
        with closing(Engine(':memory:', self.config)) as engine:
            self.assertEqual('failed', engine.execute(command('fides'), True)['state'])

    def test_cli_uses_same_runtime_and_does_not_export_private_reply(self):
        config = Path(self.tmp.name) / 'config.json'
        config.write_text(json.dumps(self.config))
        args = [sys.executable, '-m', 'verdugo', '--state', str(self.path), '--config', str(config),
                'run', json.dumps(command('openrefine')), '--execute']
        outcome = subprocess.run(args, text=True, capture_output=True, timeout=15)
        self.assertEqual(0, outcome.returncode, outcome.stderr)
        result = json.loads(outcome.stdout)
        self.assertEqual('succeeded', result['state'])
        self.assertEqual(1, result['result']['projects_in_response'])
        self.assertNotIn(PRIVATE, outcome.stdout + outcome.stderr)
        self.assertNotIn(TOKEN, outcome.stdout + outcome.stderr)
        again = subprocess.run(args, text=True, capture_output=True, timeout=15)
        self.assertTrue(json.loads(again.stdout)['replayed'])
        self.assertEqual(1, len(self.calls))


class CatalogueTruthTests(unittest.TestCase):
    def test_remaining_plan_matches_computed_pending_entries(self):
        from verdugo.catalog import catalog
        root = Path(__file__).resolve().parents[1]
        plan = json.loads((root / 'docs/plan_conexion.json').read_text())
        expected = {p['id'] for p in catalog() if connections.state(p['id']) == 'pendiente'}
        self.assertEqual(len(expected), plan['pending'])
        self.assertEqual(expected, {p['id'] for p in plan['items']})
        self.assertEqual(len(expected), len(plan['items']))
        self.assertEqual(set(batch.SPECS), {p['id'] for p in plan['implemented_v017']})

    def test_inspected_contract_manifest_matches_original_catalog_pins(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'sources/contracts-v017.json').read_text())
        self.assertEqual(set(batch.SPECS), {p['id'] for p in manifest['records']})
        for item in manifest['records']:
            self.assertEqual(batch.PINNED_COMMITS[item['id']], item['commit'])
            self.assertIs(item['live_verified'], False)
            self.assertTrue(item['files'])
            for source in item['files']:
                self.assertRegex(source['git_blob_sha'], r'^[0-9a-f]{40}$')
                self.assertIn('/blob/' + item['commit'] + '/', source['source_url'])

    def test_init_reports_actual_322_not_historical_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'config.json'
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(['init', '--out', str(target)])
            self.assertEqual(0, code)
            self.assertEqual(688, json.loads(output.getvalue())['registered'])
            cfg = json.loads(target.read_text())
            self.assertEqual(688, len(cfg['tenants']['nexus']['services']))
            self.assertTrue(all(s['enabled'] is False for s in cfg['tenants']['nexus']['services'].values()))

    def test_connection_changes_are_code_derived_and_do_not_certify_production(self):
        report = connections.summary()
        self.assertEqual({'conectado': 269, 'pendiente': 341, 'pieza_de_construccion': 56, 'excluido': 22}, report['states'])
        self.assertEqual(0, report['live_verified'])
        with closing(Engine(':memory:')) as engine:
            status = engine.status()
        self.assertEqual(107, status['api_adapters_implemented'])
        self.assertEqual(111, status['api_actions_implemented'])
        self.assertEqual(288, status['total_adapters_implemented'])
        self.assertEqual(400, status['projects_without_any_adapter'])


if __name__ == '__main__':
    unittest.main()
