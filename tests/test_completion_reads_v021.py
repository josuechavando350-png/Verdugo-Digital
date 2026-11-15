import copy
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from verdugo import completion_reads as reads, product
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.read_contracts import check
from verdugo.transport import send, TransportError

TOKEN = 'oseo_private_test_credential'
DEVELOPER = 'private_test_developer_credential'
PRIVATE = 'private-person@example.invalid'
REPLIES = {
    'anubis': {'bounded_text': 'OK\n'},
    'postal': {'bounded_text': 'OK'},
    'tusd': {'bounded_text': '# HELP tusd_connections_open Current connections\ntusd_connections_open 3\nother_metric{person="' + PRIVATE + '"} 7\n'},
    'nlweb': {'status': 'healthy', 'uptime_seconds': 12.5, 'version': '2.0.0', 'mode': PRIVATE},
    'openprospector': {'ok': True, 'configured_providers': 3, 'queue_available': True, 'private': PRIVATE},
    'openseo': {'ok': True, 'data': [{'id': '12345678-1234-1234-1234-123456789abc', 'name': PRIVATE}]},
    'google-ads': {'resourceNames': ['customers/1234567890', 'customers/9876543210']},
    'meta-ads': {'data': [{'id': 'act_12345', 'account_status': 1, 'name': PRIVATE}],
                 'paging': {'next': 'https://graph.facebook.com/next?access_token=' + TOKEN}},
    'temporal': {'namespaces': [{'namespaceInfo': {'id': 'namespace-1', 'name': PRIVATE}}], 'nextPageToken': 'cHJpdmF0ZQ=='},
    'debezium': {'name': 'sales', 'connector': {'state': 'RUNNING', 'worker_id': PRIVATE},
                 'tasks': [{'id': 0, 'state': 'FAILED', 'trace': PRIVATE}]},
    'otel-collector': {'bounded_text': 'otelcol_process_uptime{service_instance_id="' + PRIVATE + '"} 42.25\n'},
    'huginn': [{'id': 1, 'disabled': False, 'options': {'secret': PRIVATE}}, {'id': 2, 'disabled': True}],
    'opengmb': {'data': {'actions': [{'name': 'profile.read', 'kind': 'read', 'needsPerson': False, 'description': PRIVATE},
                                    {'name': 'profile.write', 'kind': 'write', 'needsPerson': True}]}},
    'livekit': {'rooms': [{'sid': 'RM_test1', 'numParticipants': 2, 'metadata': PRIVATE}, {'sid': 'RM_test2'}]},
    'webmention-io': {'type': 'feed', 'children': [{'wm-id': 1, 'content': PRIVATE}],
                      'paging': {'page': 0, 'per-page': 50, 'total': 1, 'total-pages': 1}},
    'datosmex': {'bmx': {'series': [{'idSerie': 'SF43718', 'titulo': PRIVATE,
                                   'datos': [{'fecha': '14/11/2026', 'dato': '20.1234'}]}]}},
    'mcp-gsc': {'siteEntry': [{'siteUrl': 'sc-domain:example.invalid', 'permissionLevel': 'siteOwner'}]},
    'praw': {'kind': 'Listing', 'data': {'children': [{'kind': 't3', 'data': {'id': 'abc123', 'score': 10, 'num_comments': 3, 'author': PRIVATE}}], 'after': None}},
    'python-podcastindex': {'status': 'true', 'stats': {'feedCountTotal': 100, 'episodeCountTotal': 2000, 'feedsWithNewEpisodes30days': 20}, 'description': PRIVATE},
    'letta': {'bounded_text': 'ok\n'},
    'humanlayer': {'status': 'ok', 'timestamp': '2026-11-15T00:00:00.000Z'},
    'krayin-crm': {'statistics': {key: {'current': 3, 'previous': 2, 'progress': 50}
                                 for key in ('total_leads', 'total_quotations', 'total_persons', 'total_organizations')},
                    'date_range': PRIVATE},
}
EXPECTED = {'anubis': ('process_health_reported', True), 'postal': ('process_health_reported', True),
            'tusd': ('open_connections_reported', 3), 'nlweb': ('uptime_seconds_reported', 12.5),
            'openprospector': ('configured_providers', 3), 'openseo': ('projects_in_response', 1),
            'google-ads': ('directly_accessible_accounts', 2), 'meta-ads': ('accounts_in_response', 1),
            'temporal': ('namespaces_in_response', 1), 'debezium': ('tasks_in_response', 1),
            'otel-collector': ('uptime_seconds_reported', 42.25), 'huginn': ('agents_in_response', 2),
            'opengmb': ('advertised_actions', 2), 'livekit': ('participants_reported', 2),
            'webmention-io': ('mentions_in_response', 1), 'datosmex': ('mxn_per_usd_reported', '20.1234'),
            'mcp-gsc': ('sites_in_response', 1), 'praw': ('posts_in_response', 1),
            'python-podcastindex': ('episodes_reported', 2000), 'letta': ('process_health_reported', True),
            'humanlayer': ('process_and_database_health_reported', True), 'krayin-crm': ('rest_api_extension_used', False)}


def configure(config):
    for sid in reads.SPECS:
        config['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True,
            version=reads.PINS[sid], token_env='VERDUGO_COMPLETION_TOKEN',
            auth_mode=reads.AUTH_MODES[sid], proxy_auth_reviewed=True,
            native_auth_enforced_reviewed=True, oauth_scope_reviewed=True,
            username='metrics', developer_token_env='VERDUGO_COMPLETION_DEVELOPER',
            connector_id='sales', debezium_connector_reviewed=True, default_metrics_names_reviewed=True,
            account_scope_reviewed=True, api_key_env='VERDUGO_COMPLETION_DEVELOPER',
            free_api_access_reviewed=True, subreddit='test', session_cookie_name='krayin_session')


def route(sid):
    return next(iter(reads.SPECS[sid].values()))[1].replace('{connector_id}', 'sales').replace('{subreddit}', 'test')


def command(sid):
    return {'service': sid, 'operation': next(iter(reads.SPECS[sid])), 'params': {}, 'key': sid}


class CompletionReads(unittest.TestCase):
    def setUp(self):
        self.config = template('nexus'); configure(self.config)
        env = patch.dict(os.environ, VERDUGO_COMPLETION_TOKEN=TOKEN, VERDUGO_COMPLETION_DEVELOPER=DEVELOPER)
        env.start(); self.addCleanup(env.stop)

    def test_templates_are_disabled_and_unreviewed(self):
        for sid in reads.SPECS:
            cfg = template('nexus')['tenants']['nexus']['services'][sid]
            self.assertIs(False, cfg['enabled']); self.assertIs(False, cfg['license_reviewed'])
            self.assertNotIn('license_policy_exception', cfg)
            if sid in reads.PROXY_ONLY: self.assertIs(False, cfg['proxy_auth_reviewed'])

    def test_fixed_methods_routes_and_params(self):
        for sid, ops in reads.SPECS.items():
            op, (method, path) = next(iter(ops.items()))
            cfg = self.config['tenants']['nexus']['services'][sid]
            req = build(sid, op, {}, cfg)
            self.assertEqual(method, req['public']['method'])
            self.assertTrue(req['public']['url'].endswith(route(sid)))
            self.assertFalse(req['mutates'])
            for secret in (TOKEN, DEVELOPER): self.assertNotIn(secret, json.dumps(req['public']))
            for field in ('url', 'method', 'token', 'headers', 'tenant', 'query', 'command'):
                with self.subTest(service=sid, field=field), self.assertRaises(VerdugoError):
                    build(sid, op, {field: 'forbidden'}, cfg)
            with self.assertRaises(VerdugoError): build(sid, op, {'page': 2}, cfg)
            with self.assertRaises(VerdugoError): build(sid, 'invented', {}, cfg)

    def test_google_origin_and_both_secrets_are_bound(self):
        cfg = self.config['tenants']['nexus']['services']['google-ads']; op = 'accounts.summary'
        request = build('google-ads', op, {}, cfg)
        self.assertEqual(DEVELOPER, request['headers']['developer-token'])
        for key in ('VERDUGO_COMPLETION_TOKEN', 'VERDUGO_COMPLETION_DEVELOPER'):
            with patch.dict(os.environ, {key: 'changed'}):
                changed = build('google-ads', op, {}, cfg)
                self.assertNotEqual(request['public']['credential_binding'], changed['public']['credential_binding'])
            with patch.dict(os.environ, {key: ''}), self.assertRaises(VerdugoError):
                build('google-ads', op, {}, cfg)
        with self.assertRaises(VerdugoError):
            build('google-ads', op, {}, cfg | {'base_url': 'https://other.invalid'})
        self.assertEqual(0, check('google-ads', op, {})['directly_accessible_accounts'])

    def test_provider_scope_and_identifiers_are_bound(self):
        cfg = self.config['tenants']['nexus']['services']['meta-ads']
        with self.assertRaises(VerdugoError):
            build('meta-ads', 'accounts.summary', {}, cfg | {'base_url': 'https://other.invalid'})
        for sid, flag in [('debezium', 'debezium_connector_reviewed'), ('otel-collector', 'default_metrics_names_reviewed')]:
            cfg = self.config['tenants']['nexus']['services'][sid]
            with self.assertRaises(VerdugoError): build(sid, command(sid)['operation'], {}, cfg | {flag: False})
        cfg = self.config['tenants']['nexus']['services']['debezium']
        for name in (None, '../x', 'x?other', 'a/b'):
            with self.assertRaises(VerdugoError): build('debezium', 'connector.summary', {}, cfg | {'connector_id': name})
        req = build('debezium', 'connector.summary', {}, cfg)
        with self.assertRaises(VerdugoError): check('debezium', 'connector.summary', dict(REPLIES['debezium'], name='wrong'), req['public'])

    def test_livekit_jwt_is_least_scope_and_replay_binding_is_stable(self):
        import base64
        import hashlib
        import hmac
        cfg = self.config['tenants']['nexus']['services']['livekit']
        with patch('verdugo.completion_reads.time.time', return_value=1000):
            first = build('livekit', 'rooms.summary', {}, cfg)
        with patch('verdugo.completion_reads.time.time', return_value=2000):
            later = build('livekit', 'rooms.summary', {}, cfg)
        self.assertEqual(first['public'], later['public'])
        self.assertNotEqual(first['headers']['Authorization'], later['headers']['Authorization'])
        jwt = first['headers']['Authorization'].removeprefix('Bearer ')
        head, body, signature = jwt.split('.')
        decode = lambda part: base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))
        self.assertEqual({'alg': 'HS256', 'typ': 'JWT'}, json.loads(decode(head)))
        self.assertEqual({'iss': DEVELOPER, 'nbf': 995, 'exp': 1060, 'video': {'roomList': True}}, json.loads(decode(body)))
        self.assertEqual(hmac.new(TOKEN.encode(), (head + '.' + body).encode(), hashlib.sha256).digest(), decode(signature))
        self.assertEqual({}, first['public']['body']); self.assertFalse(first['mutates'])
        with patch.dict(os.environ, VERDUGO_COMPLETION_DEVELOPER='new_key'):
            self.assertNotEqual(first['public']['credential_binding'], build('livekit', 'rooms.summary', {}, cfg)['public']['credential_binding'])

    def test_podcastindex_timestamp_signature_and_stable_binding(self):
        import hashlib
        cfg = self.config['tenants']['nexus']['services']['python-podcastindex']
        with patch('verdugo.completion_reads.time.time', return_value=1000):
            a = build('python-podcastindex', 'index.summary', {}, cfg)
        with patch('verdugo.completion_reads.time.time', return_value=2000):
            b = build('python-podcastindex', 'index.summary', {}, cfg)
        self.assertEqual(a['public'], b['public'])
        self.assertEqual(hashlib.sha1((DEVELOPER + TOKEN + '1000').encode()).hexdigest(), a['headers']['Authorization'])
        self.assertEqual(DEVELOPER, a['headers']['X-Auth-Key'])
        self.assertNotEqual(a['headers']['Authorization'], b['headers']['Authorization'])
        with patch.dict(os.environ, VERDUGO_COMPLETION_TOKEN='changed'):
            self.assertNotEqual(a['public']['credential_binding'], build('python-podcastindex', 'index.summary', {}, cfg)['public']['credential_binding'])

    def test_authentication_review_is_required(self):
        for sid in reads.SPECS:
            cfg = self.config['tenants']['nexus']['services'][sid]; op = command(sid)['operation']
            with self.assertRaises(VerdugoError): build(sid, op, {}, cfg | {'auth_mode': 'none'})
            flag = 'proxy_auth_reviewed' if sid in reads.PROXY_ONLY else 'native_auth_enforced_reviewed' if sid == 'anubis' else 'oauth_scope_reviewed' if sid in ('google-ads', 'meta-ads', 'mcp-gsc', 'praw') else 'account_scope_reviewed' if sid in ('huginn', 'opengmb', 'livekit', 'datosmex', 'webmention-io', 'python-podcastindex') else None
            if flag:
                for value in (False, None, 'true', 1):
                    with self.assertRaises(VerdugoError): build(sid, op, {}, cfg | {flag: value})
        with self.assertRaises(VerdugoError):
            cfg = self.config['tenants']['nexus']['services']['anubis']
            build('anubis', 'health.summary', {}, cfg | {'username': 'a:b'})

    def test_projection_and_schema_fail_closed(self):
        for sid, payload in REPLIES.items():
            op = command(sid)['operation']; result = check(sid, op, payload)
            key, expected = EXPECTED[sid]; self.assertEqual(expected, result[key])
            self.assertNotIn(PRIVATE, json.dumps(result)); self.assertIs(False, result['live_verified'])
            for bad in (None, {'invalid': []}, {'error': PRIVATE}):
                with self.subTest(service=sid), self.assertRaises(VerdugoError): check(sid, op, bad)
        bad_cases = {'anubis': {'bounded_text': 'OK'}, 'postal': {'bounded_text': 'OK\n'},
                     'tusd': {'bounded_text': 'tusd_connections_open NaN'},
                     'nlweb': dict(REPLIES['nlweb'], uptime_seconds=True),
                     'openprospector': dict(REPLIES['openprospector'], configured_providers=True),
                     'openseo': {'ok': True, 'data': REPLIES['openseo']['data'] * 2},
                     'google-ads': {'resourceNames': ['customers/1'] * 2}}
        for sid, payload in bad_cases.items():
            with self.subTest(service=sid), self.assertRaises(VerdugoError): check(sid, command(sid)['operation'], payload)

    def test_text_decoder_is_scoped_and_bounded(self):
        for sid, raw, mime in [('postal', b'OK', 'application/json'), ('postal', b'\xff', 'text/plain'),
                               ('postal', b'a' * 262145, 'text/plain'), ('postal', b'OK\x00', 'text/plain'),
                               ('nlweb', b'OK', 'text/plain')]:
            with self.assertRaises(VerdugoError): reads.decode_text(sid, command(sid)['operation'], raw, mime)

    def test_every_contract_uses_real_loopback_transport(self):
        for sid, payload in REPLIES.items():
            calls = []
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args): pass
                def do_POST(self):
                    body = self.rfile.read(int(self.headers['Content-Length']))
                    if body != b'{}':
                        self.send_error(400); return
                    self.do_GET()
                def do_GET(self):
                    calls.append((self.path, dict(self.headers)))
                    is_text = 'bounded_text' in payload
                    raw = payload['bounded_text'].encode() if is_text else json.dumps(payload).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8' if is_text else 'application/json')
                    self.end_headers(); self.wfile.write(raw)
            with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                try:
                    cfg = self.config['tenants']['nexus']['services'][sid] | {'allow_local_http': True}
                    request = build(sid, command(sid)['operation'], {}, cfg)
                    # Test-only routing after asserting build rejects a Google origin override.
                    # This exercises identical headers, path and decoder through a real socket.
                    request['public']['url'] = 'http://127.0.0.1:' + str(server.server_port) + route(sid)
                    result = check(sid, command(sid)['operation'], send(request, cfg))
                    key, expected = EXPECTED[sid]; self.assertEqual(expected, result[key])
                    self.assertEqual(1, len(calls)); self.assertEqual(route(sid), calls[0][0])
                    credential_header = 'Cookie' if sid in ('huginn', 'krayin-crm') else 'Bmx-Token' if sid == 'datosmex' else 'Authorization'
                    self.assertEqual(request['headers'][credential_header], calls[0][1][credential_header])
                    if sid == 'google-ads': self.assertEqual(DEVELOPER, calls[0][1]['developer-token'])
                finally:
                    server.shutdown(); thread.join()

    def test_single_engine_sqlite_and_restart_without_private_payloads(self):
        calls = []
        def transport(request, cfg):
            sid = request['public']['service']; calls.append(sid); return copy.deepcopy(REPLIES[sid])
        request = {'id': 'completion-reads', 'services': sorted(REPLIES), 'dataset': 'demo', 'currency': 'MXN'}
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / 'state.db'
            with closing(Engine(db, self.config, transport=transport)) as engine:
                result = product.observe(engine, request, True)
                self.assertEqual('succeeded', result['state'], result)
                self.assertEqual(len(REPLIES), result['new_observations'])
                stored = '\n'.join(engine.db.iterdump())
                for private in (PRIVATE, TOKEN, DEVELOPER): self.assertNotIn(private, stored)
            with closing(Engine(db, self.config, transport=lambda *a: self.fail('Replay performed HTTP'))) as engine:
                replay = product.observe(engine, request, True)
                self.assertEqual(len(REPLIES), replay['reused_observations'])
            self.assertEqual(len(REPLIES), len(calls))
