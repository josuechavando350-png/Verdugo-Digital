"""v0.15: twelve bounded read-only service contracts and the connection map.

Responses are synthetic. Passing these tests does NOT certify any vendor
installation, account or live third-party service.
"""
import base64
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
import tempfile
import threading
import unittest
from unittest.mock import patch

from verdugo.__main__ import template
from verdugo.adapters import SPECS, build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo import connections, service_reads
from verdugo.connections import read_map, summary
from verdugo.license_policy import record
from verdugo.read_contracts import check
from verdugo.transport import send

TOKEN = 'synthetic-secret-token-never-real'
SID = 'AC' + 'a' * 32
EXPECTED = {
    'vllm': ('models.list', '/v1/models', {}, 'Bearer ' + TOKEN),
    'ollama': ('models.list', '/api/tags', {}, 'Bearer ' + TOKEN),
    'label-studio': ('projects.list', '/api/projects/', {'page': ['1'], 'page_size': ['30']}, 'Token ' + TOKEN),
    'grist': ('orgs.list', '/api/orgs', {}, 'Bearer ' + TOKEN),
    'datasette': ('databases.list', '/-/databases.json', {}, 'Bearer ' + TOKEN),
    'svix': ('applications.list', '/api/v1/app', {'limit': ['50']}, 'Bearer ' + TOKEN),
    'cube': ('cubes.list', '/cubejs-api/v1/meta', {}, 'Bearer ' + TOKEN),
    'e2b': ('sandboxes.list', '/v2/sandboxes', {'limit': ['50']}, None),
    'langflow': ('flows.list', '/api/v1/flows/', {'get_all': ['false'], 'header_flows': ['true'],
                 'remove_example_flows': ['true'], 'page': ['1'], 'size': ['50']}, None),
    'mercadopago': ('payments.summary', '/v1/payments/search', {'sort': ['date_created'],
                    'criteria': ['desc'], 'limit': ['30'], 'offset': ['0']}, 'Bearer ' + TOKEN),
    'stripe-python': ('balance.read', '/v1/balance', {}, 'Bearer ' + TOKEN),
    'twilio-python': ('account.read', '/2010-04-01/Accounts/' + SID + '.json', {},
                      'Basic ' + base64.b64encode((SID + ':' + TOKEN).encode()).decode()),
    'crowdsec': ('decisions.summary', '/v1/decisions', {}, None),
    'clickhouse': ('databases.count', '/', {'query': ['SELECT count() AS databases FROM system.databases FORMAT JSON']}, None),
    'dittofeed': ('segments.list', '/api/admin/segments', {'workspaceId': ['00000000-0000-4000-8000-000000000001']}, 'Bearer ' + TOKEN),
}
PRIVATE = 'private-person@example.invalid'
REPLIES = {
    'vllm': {'object': 'list', 'data': [{'id': 'm', 'object': 'model', 'owned_by': PRIVATE}]},
    'ollama': {'models': [{'name': PRIVATE}, {'name': 'b'}]},
    'label-studio': {'count': 1, 'next': None, 'previous': None, 'results': [{'id': 1, 'title': PRIVATE}]},
    'grist': [{'id': 1, 'name': PRIVATE, 'domain': 'x'}],
    'datasette': [{'name': 'db', 'path': PRIVATE, 'size': 10}],
    'svix': {'data': [{'id': 'app_1', 'name': PRIVATE}], 'done': False, 'iterator': 'x'},
    'cube': {'cubes': [{'name': 'Orders', 'title': PRIVATE}]},
    'e2b': [{'sandboxID': 's1', 'state': 'running', 'metadata': {'owner': PRIVATE}},
            {'sandboxID': 's2', 'state': 'paused'}, {'sandboxID': 's3', 'state': 'weird'}],
    'langflow': {'items': [{'id': 'f', 'name': PRIVATE}], 'total': 1, 'page': 1, 'size': 50, 'pages': 1},
    'mercadopago': {'paging': {'total': 3}, 'results': [
        {'id': 1, 'status': 'approved', 'payer': {'email': PRIVATE}, 'transaction_amount': 9},
        {'id': 2, 'status': 'approved'}, {'id': 3, 'status': 'rejected'}]},
    'stripe-python': {'object': 'balance', 'livemode': False,
                      'available': [{'amount': 1500, 'currency': 'mxn'}],
                      'pending': [{'amount': 200, 'currency': 'mxn'}, {'amount': 7, 'currency': 'usd'}]},
    'twilio-python': {'sid': SID, 'friendly_name': PRIVATE, 'status': 'active', 'type': 'Trial',
                      'auth_token': TOKEN},
    'crowdsec': [{'id': 1, 'type': 'ban', 'scope': 'Ip', 'value': PRIVATE}, {'id': 2, 'type': 'captcha', 'value': '10.0.0.1'}],
    'clickhouse': {'meta': [{'name': 'databases', 'type': 'UInt64'}], 'data': [{'databases': '4'}], 'rows': 1},
    'dittofeed': {'segments': [{'id': 's', 'name': PRIVATE, 'definition': {}}]},
}


def make_config():
    cfg = template('nexus')
    env = {}
    for sid in service_reads.SPECS:
        s = cfg['tenants']['nexus']['services'][sid]
        s.update(enabled=True, license_reviewed=True, version='contract-fixture-only')
        if sid not in service_reads.FIXED_ORIGINS:
            s['base_url'] = 'https://example.invalid'
        env[s['token_env']] = TOKEN
    cfg['tenants']['nexus']['services']['twilio-python']['account_sid'] = SID
    cfg['tenants']['nexus']['services']['clickhouse']['username'] = 'verdugo_readonly'
    cfg['tenants']['nexus']['services']['dittofeed']['workspace_id'] = '00000000-0000-4000-8000-000000000001'
    return cfg, env


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.config, env = make_config()
        self.env = patch.dict(os.environ, env)
        self.env.start()
        self.services = self.config['tenants']['nexus']['services']

    def tearDown(self):
        self.env.stop()

    def test_exact_inventory_is_read_only(self):
        self.assertEqual(set(EXPECTED), set(service_reads.SPECS))
        for sid, ops in service_reads.SPECS.items():
            self.assertEqual(['GET'], [m for m, _ in ops.values()])
            self.assertEqual(ops, SPECS[sid])
            self.assertNotEqual('excluido', record(sid)['policy'])

    def test_requests_match_pinned_upstream_contracts(self):
        for sid, (op, path, query, auth) in EXPECTED.items():
            with self.subTest(sid=sid):
                req = build(sid, op, {}, self.services[sid])
                url = urlsplit(req['public']['url'])
                self.assertEqual(path, url.path)
                self.assertEqual(query, parse_qs(url.query))
                self.assertEqual('GET', req['public']['method'])
                self.assertFalse(req['mutates'])
                self.assertNotIn(TOKEN, json.dumps(req['public']))
                if auth:
                    self.assertEqual(auth, req['headers']['Authorization'])
        self.assertEqual(TOKEN, build('e2b', 'sandboxes.list', {}, self.services['e2b'])['headers']['X-API-Key'])
        self.assertEqual(TOKEN, build('langflow', 'flows.list', {}, self.services['langflow'])['headers']['x-api-key'])
        self.assertEqual(TOKEN, build('crowdsec', 'decisions.summary', {}, self.services['crowdsec'])['headers']['X-Api-Key'])
        ch = build('clickhouse', 'databases.count', {}, self.services['clickhouse'])['headers']
        self.assertEqual(('verdugo_readonly', TOKEN), (ch['X-ClickHouse-User'], ch['X-ClickHouse-Key']))

    def test_cloud_credentials_are_bound_to_official_origin(self):
        for sid, origin in service_reads.FIXED_ORIGINS.items():
            op = EXPECTED[sid][0]
            with self.subTest(sid=sid):
                self.assertTrue(build(sid, op, {}, self.services[sid])['public']['url'].startswith(origin + '/'))
                cfg = dict(self.services[sid], base_url='https://attacker.example')
                with self.assertRaisesRegex(VerdugoError, 'may only be sent'):
                    build(sid, op, {}, cfg)

    def test_parameters_cannot_change_route_page_or_credentials(self):
        for value in ({'page': 2}, {'url': 'https://x'}, {'limit': 1000}, {'token': 'x'}, {'page': 'abc'}):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                build('svix', 'applications.list', value, self.services['svix'])
        with self.assertRaises(VerdugoError):
            build('svix', 'applications.create', {}, self.services['svix'])

    def test_scoped_providers_require_reviewed_identifiers(self):
        for sid, key, bad in (('clickhouse', 'username', ['', 'a b', None, 'x' * 65]),
                              ('dittofeed', 'workspace_id', ['', 'ws1', None, '../x'])):
            for value in bad:
                cfg = dict(self.services[sid], **{key: value})
                with self.subTest(sid=sid, value=value), self.assertRaises(VerdugoError):
                    build(sid, EXPECTED[sid][0], {}, cfg)

    def test_twilio_requires_reviewed_account_sid(self):
        for value in (None, 'AC123', 'ac' + 'a' * 32, '../' + SID):
            cfg = dict(self.services['twilio-python'], account_sid=value)
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                build('twilio-python', 'account.read', {}, cfg)

    def test_projection_keeps_counts_never_raw_payloads(self):
        for sid, (op, *_rest) in EXPECTED.items():
            with self.subTest(sid=sid):
                value = check(sid, op, json.loads(json.dumps(REPLIES[sid])))
                self.assertFalse(value['raw_provider_payload_retained'])
                self.assertFalse(value['live_verified'])
                dumped = json.dumps(value)
                self.assertNotIn(PRIVATE, dumped)
                self.assertNotIn(TOKEN, dumped)
        self.assertEqual({'running': 1, 'paused': 1, 'OTHER': 1}, check('e2b', 'sandboxes.list', REPLIES['e2b'])['status_counts'])
        self.assertEqual({'approved': 2, 'rejected': 1}, check('mercadopago', 'payments.summary', REPLIES['mercadopago'])['status_counts'])
        self.assertEqual({'mxn': {'available_minor': 1500, 'pending_minor': 200}, 'usd': {'available_minor': 0, 'pending_minor': 7}},
                         check('stripe-python', 'balance.read', REPLIES['stripe-python'])['provider_reported_balance'])
        tw = check('twilio-python', 'account.read', REPLIES['twilio-python'])
        self.assertEqual(('active', 'Trial'), (tw['account_status'], tw['account_type']))
        self.assertTrue(check('svix', 'applications.list', REPLIES['svix'])['more_pages'])
        self.assertEqual(2, check('ollama', 'models.list', REPLIES['ollama'])['records_in_response'])
        self.assertEqual(4, check('clickhouse', 'databases.count', REPLIES['clickhouse'])['databases'])
        self.assertEqual({'ban': 1, 'captcha': 1}, check('crowdsec', 'decisions.summary', REPLIES['crowdsec'])['status_counts'])
        self.assertEqual(0, check('crowdsec', 'decisions.summary', None)['records_in_response'])

    def test_schema_mismatch_fails_closed(self):
        bad = {'vllm': {'models': []}, 'grist': {'orgs': []}, 'cube': [], 'e2b': {'data': []},
               'stripe-python': {'object': 'charge'}, 'twilio-python': [],
               'mercadopago': {'results': ['x']}, 'label-studio': {'results': [1] * 2},
               'datasette': [{'a': 1}] * 1001, 'clickhouse': {'data': [{'databases': 'x'}]},
               'dittofeed': {'items': []}}
        for sid, body in bad.items():
            with self.subTest(sid=sid), self.assertRaises(VerdugoError):
                check(sid, EXPECTED[sid][0], body)
        with self.assertRaises(VerdugoError):
            check('stripe-python', 'balance.read', {'object': 'balance', 'available': [{'amount': '1', 'currency': 'mxn'}], 'pending': []})

    def test_engine_persists_only_the_projection(self):
        calls = []
        def transport(req, cfg):
            calls.append(req['public']['service'])
            return json.loads(json.dumps(REPLIES[req['public']['service']]))
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o700)
            state = Path(tmp) / 'state.sqlite3'
            engine = Engine(state, self.config, transport=transport)
            try:
                for sid, (op, *_rest) in EXPECTED.items():
                    cmd = {'service': sid, 'operation': op, 'params': {}, 'key': 'v015-' + sid}
                    self.assertEqual('planned', engine.execute(cmd)['state'])
                    out = engine.execute(cmd, True)
                    self.assertEqual('succeeded', out['state'], sid)
                    self.assertTrue(engine.execute(cmd, True)['replayed'])
            finally:
                engine.close()
            self.assertEqual(sorted(EXPECTED), sorted(calls))
            raw = state.read_bytes()
            self.assertNotIn(PRIVATE.encode(), raw)
            self.assertNotIn(TOKEN.encode(), raw)

    def test_real_loopback_http_for_self_hosted_services(self):
        incoming = []
        routes = {EXPECTED[s][1]: s for s in EXPECTED if s not in service_reads.FIXED_ORIGINS}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                sid = routes.get(urlsplit(self.path).path)
                incoming.append((sid, self.headers.get('Authorization') or self.headers.get('x-api-key') or self.headers.get('X-ClickHouse-Key')))
                body = json.dumps(REPLIES.get(sid, {})).encode()
                self.send_response(200 if sid else 404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for sid in routes.values():
                self.services[sid].update(base_url='http://127.0.0.1:%d' % server.server_port, allow_local_http=True)
            engine = Engine(':memory:', self.config, transport=send)
            try:
                for sid in routes.values():
                    op = EXPECTED[sid][0]
                    out = engine.execute({'service': sid, 'operation': op, 'params': {}, 'key': 'loop-' + sid}, True)
                    self.assertEqual('succeeded', out['state'], sid)
                    self.assertGreaterEqual(out['result'].get('records_in_response', out['result'].get('databases', 0)), 1)
            finally:
                engine.close()
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(sorted(routes.values()), sorted(s for s, _ in incoming))
        self.assertTrue(all(auth for _, auth in incoming))


class ConnectionMapTests(unittest.TestCase):
    def test_states_are_computed_from_code(self):
        value = summary()
        self.assertEqual(322, value['registered'])
        self.assertEqual({'conectado': 58, 'pieza_de_construccion': 56, 'pendiente': 186, 'excluido': 22},
                         value['states'])
        self.assertEqual(0, value['live_verified'])
        for sid in service_reads.SPECS:
            self.assertEqual('conectado', connections.state(sid))
        self.assertEqual('excluido', connections.state('twenty'))
        self.assertEqual('pieza_de_construccion', connections.state('tailwindcss'))
        self.assertEqual('pendiente', connections.state('splink'))

    def test_map_tampering_is_rejected(self):
        original = json.loads(connections.PATH.read_text())
        mutations = [
            lambda d: d['records'][0].update(kind='servicio'),       # excluded entry un-excluded
            lambda d: d['records'][5].update(kind='componente'),     # chatwoot HTTP adapter as component
            lambda d: d['records'][22].update(kind='servicio'),      # scrapy local recipe as service
            lambda d: d['records'].pop(),
            lambda d: d['records'][9].update(state='conectado'),     # state cannot be asserted
            lambda d: d['kinds'].pop('cli'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'connections.json'
            for i, mutate in enumerate(mutations):
                changed = json.loads(json.dumps(original))
                mutate(changed)
                target.write_text(json.dumps(changed))
                connections._CACHE.pop(str(target), None)
                with self.subTest(mutation=i), self.assertRaises(VerdugoError):
                    read_map(target)

    def test_status_exposes_connection_state(self):
        engine = Engine(':memory:')
        try:
            status = engine.status()
        finally:
            engine.close()
        self.assertEqual(58, status['connection_states']['conectado'])
        row = next(r for r in status['integrations'] if r['id'] == 'vllm')
        self.assertEqual(('servicio', 'conectado'), (row['connection_kind'], row['connection_state']))


if __name__ == '__main__':
    unittest.main()
