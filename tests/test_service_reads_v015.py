"""v0.15: thirteen bounded read-only service contracts and the connection map.

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
EXPECTED = {
    'vllm': ('models.list', '/v1/models', {}, 'Bearer ' + TOKEN),
    'ollama': ('models.list', '/api/tags', {}, 'Bearer ' + TOKEN),
    'label-studio': ('projects.list', '/api/projects/', {'page': ['1'], 'page_size': ['30']}, 'Token ' + TOKEN),
    'grist': ('orgs.list', '/api/orgs', {}, 'Bearer ' + TOKEN),
    'datasette': ('databases.list', '/-/databases.json', {}, 'Bearer ' + TOKEN),
    'svix': ('applications.list', '/api/v1/app', {'limit': ['50']}, 'Bearer ' + TOKEN),
    'cube': ('cubes.list', '/cubejs-api/v1/meta', {}, 'Bearer ' + TOKEN),
    'langflow': ('flows.list', '/api/v1/flows/', {'get_all': ['false'], 'header_flows': ['true'],
                 'remove_example_flows': ['true'], 'page': ['1'], 'size': ['50']}, None),
    'android-sms-gateway': ('devices.list', '/devices', {},
                            'Basic ' + base64.b64encode(('sms' + ':' + TOKEN).encode()).decode()),
    'sendportal': ('campaigns.summary', '/api/v1/campaigns', {}, 'Bearer ' + TOKEN),
    'crowdsec': ('decisions.summary', '/v1/decisions', {}, None),
    'clickhouse': ('databases.count', '/', {'query': ['SELECT count() AS databases FROM system.databases FORMAT JSON']}, None),
    'dittofeed': ('segments.list', '/api/admin/segments', {'workspaceId': ['00000000-0000-4000-8000-000000000001']}, 'Bearer ' + TOKEN),
    'owncast': ('chat_clients.count', '/api/integrations/clients', {}, 'Bearer ' + TOKEN),
    'lighthouse-ci': ('projects.list', '/v1/projects', {},
                      'Basic ' + base64.b64encode(('lhci' + ':' + TOKEN).encode()).decode()),
    'cal-diy': ('bookings.summary', '/v2/bookings', {}, 'Bearer ' + TOKEN),
}
PAID_REMOVED = ('stripe-python', 'twilio-python', 'mercadopago', 'e2b', 'composio')
PRIVATE = 'private-person@example.invalid'
REPLIES = {
    'vllm': {'object': 'list', 'data': [{'id': 'm', 'object': 'model', 'owned_by': PRIVATE}]},
    'ollama': {'models': [{'name': PRIVATE}, {'name': 'b'}]},
    'label-studio': {'count': 1, 'next': None, 'previous': None, 'results': [{'id': 1, 'title': PRIVATE}]},
    'grist': [{'id': 1, 'name': PRIVATE, 'domain': 'x'}],
    'datasette': [{'name': 'db', 'path': PRIVATE, 'size': 10}],
    'svix': {'data': [{'id': 'app_1', 'name': PRIVATE}], 'done': False, 'iterator': 'x'},
    'cube': {'cubes': [{'name': 'Orders', 'title': PRIVATE}]},
    'langflow': {'items': [{'id': 'f', 'name': PRIVATE}], 'total': 1, 'page': 1, 'size': 50, 'pages': 1},
    'android-sms-gateway': [{'id': 'd1', 'name': PRIVATE, 'simCards': [{'slot': 1, 'number': PRIVATE}, {'slot': 2}]}],
    'sendportal': {'data': [{'id': 1, 'name': PRIVATE, 'content': PRIVATE, 'status_id': 4},
                            {'id': 2, 'status_id': 1}, {'id': 3, 'status_id': 9}], 'links': {}, 'meta': {'total': 3}},
    'crowdsec': [{'id': 1, 'type': 'ban', 'scope': 'Ip', 'value': PRIVATE}, {'id': 2, 'type': 'captcha', 'value': '10.0.0.1'}],
    'clickhouse': {'meta': [{'name': 'databases', 'type': 'UInt64'}], 'data': [{'databases': '4'}], 'rows': 1},
    'dittofeed': {'segments': [{'id': 's', 'name': PRIVATE, 'definition': {}}]},
    'owncast': [{'id': 1, 'user': {'displayName': PRIVATE}, 'ipAddress': '10.0.0.2'}],
    'lighthouse-ci': [{'id': 'p1', 'name': PRIVATE, 'token': '', 'adminToken': ''}],
    'cal-diy': {'status': 'success', 'data': [{'id': 1, 'status': 'accepted', 'attendees': [{'email': PRIVATE}]},
                                              {'id': 2, 'status': 'cancelled'}, {'id': 3, 'status': 'odd'}],
                'pagination': {'totalItems': 3}},
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
    cfg['tenants']['nexus']['services']['android-sms-gateway']['username'] = 'sms'
    cfg['tenants']['nexus']['services']['lighthouse-ci']['username'] = 'lhci'
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
        self.assertEqual(TOKEN, build('langflow', 'flows.list', {}, self.services['langflow'])['headers']['x-api-key'])
        self.assertEqual(TOKEN, build('crowdsec', 'decisions.summary', {}, self.services['crowdsec'])['headers']['X-Api-Key'])
        ch = build('clickhouse', 'databases.count', {}, self.services['clickhouse'])['headers']
        self.assertEqual(('verdugo_readonly', TOKEN), (ch['X-ClickHouse-User'], ch['X-ClickHouse-Key']))

    def test_paid_providers_are_not_registered_or_connected(self):
        from verdugo.catalog import catalog
        ids = {r['id'] for r in catalog()}
        repos = {r['repository'].casefold() for r in catalog()}
        for sid in PAID_REMOVED:
            self.assertNotIn(sid, ids)
            self.assertNotIn(sid, SPECS)
        for repo in ('stripe/stripe-python', 'twilio/twilio-python', 'mercadopago/sdk-nodejs',
                     'e2b-dev/e2b', 'composiohq/composio'):
            self.assertNotIn(repo, repos)
        self.assertEqual({}, service_reads.FIXED_ORIGINS)
        for sid in ('android-sms-gateway', 'krayin-crm', 'sendportal', 'microsandbox', 'huginn'):
            self.assertEqual('libre', record(sid)['policy'])

    def test_parameters_cannot_change_route_page_or_credentials(self):
        for value in ({'page': 2}, {'url': 'https://x'}, {'limit': 1000}, {'token': 'x'}, {'page': 'abc'}):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                build('svix', 'applications.list', value, self.services['svix'])
        with self.assertRaises(VerdugoError):
            build('svix', 'applications.create', {}, self.services['svix'])

    def test_scoped_providers_require_reviewed_identifiers(self):
        for sid, key, bad in (('clickhouse', 'username', ['', 'a b', None, 'x' * 65]),
                              ('android-sms-gateway', 'username', ['', 'a:b', None]),
                              ('lighthouse-ci', 'username', ['', 'a b', None]),
                              ('dittofeed', 'workspace_id', ['', 'ws1', None, '../x'])):
            for value in bad:
                cfg = dict(self.services[sid], **{key: value})
                with self.subTest(sid=sid, value=value), self.assertRaises(VerdugoError):
                    build(sid, EXPECTED[sid][0], {}, cfg)

    def test_projection_keeps_counts_never_raw_payloads(self):
        for sid, (op, *_rest) in EXPECTED.items():
            with self.subTest(sid=sid):
                value = check(sid, op, json.loads(json.dumps(REPLIES[sid])))
                self.assertFalse(value['raw_provider_payload_retained'])
                self.assertFalse(value['live_verified'])
                dumped = json.dumps(value)
                self.assertNotIn(PRIVATE, dumped)
                self.assertNotIn(TOKEN, dumped)
        self.assertEqual({'accepted': 1, 'cancelled': 1, 'OTHER': 1}, check('cal-diy', 'bookings.summary', REPLIES['cal-diy'])['status_counts'])
        self.assertEqual(0, check('owncast', 'chat_clients.count', None)['records_in_response'])
        cal = build('cal-diy', 'bookings.summary', {}, self.services['cal-diy'])
        self.assertEqual('2024-08-13', cal['headers']['cal-api-version'])
        self.assertNotIn('2024-08-13', cal['secret_values'])
        self.assertEqual({'sent': 1, 'draft': 1, 'OTHER': 1}, check('sendportal', 'campaigns.summary', REPLIES['sendportal'])['status_counts'])
        sms = check('android-sms-gateway', 'devices.list', REPLIES['android-sms-gateway'])
        self.assertEqual((1, 2), (sms['records_in_response'], sms['sim_cards']))
        self.assertTrue(check('svix', 'applications.list', REPLIES['svix'])['more_pages'])
        self.assertEqual(2, check('ollama', 'models.list', REPLIES['ollama'])['records_in_response'])
        self.assertEqual(4, check('clickhouse', 'databases.count', REPLIES['clickhouse'])['databases'])
        self.assertEqual({'ban': 1, 'captcha': 1}, check('crowdsec', 'decisions.summary', REPLIES['crowdsec'])['status_counts'])
        self.assertEqual(0, check('crowdsec', 'decisions.summary', None)['records_in_response'])

    def test_schema_mismatch_fails_closed(self):
        bad = {'vllm': {'models': []}, 'grist': {'orgs': []}, 'cube': [], 'sendportal': {'items': []},
               'android-sms-gateway': {'devices': []}, 'label-studio': {'results': [1] * 2},
               'datasette': [{'a': 1}] * 1001, 'clickhouse': {'data': [{'databases': 'x'}]},
               'dittofeed': {'items': []}}
        for sid, body in bad.items():
            with self.subTest(sid=sid), self.assertRaises(VerdugoError):
                check(sid, EXPECTED[sid][0], body)

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
        self.assertEqual({'conectado': 59, 'pieza_de_construccion': 56, 'pendiente': 185, 'excluido': 22},
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
        self.assertEqual(59, status['connection_states']['conectado'])
        row = next(r for r in status['integrations'] if r['id'] == 'vllm')
        self.assertEqual(('servicio', 'conectado'), (row['connection_kind'], row['connection_state']))


if __name__ == '__main__':
    unittest.main()
