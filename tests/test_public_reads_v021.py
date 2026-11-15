import copy
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from verdugo import public_reads as reads, product
from verdugo.__main__ import template
from verdugo.adapters import build, connection
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.read_contracts import check
from verdugo.transport import send

PRIVATE = 'private-publisher@example.invalid'
REPLIES = {'gdeltdoc': {'articles': [{'url': 'https://news.example.invalid/a', 'title': PRIVATE}]},
           'wbgapi': [{'page': 1, 'pages': 1, 'per_page': 1, 'total': 1},
                      [{'indicator': {'id': 'SP.POP.TOTL', 'value': PRIVATE}, 'countryiso3code': 'MEX', 'date': '2024', 'value': 100}]]}


def configure(config):
    for sid in reads.SPECS:
        config['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True,
            version=reads.PINS[sid], public_access_reviewed=True, country='MEX', year=2024, query_terms='solar energy')


class PublicReads(unittest.TestCase):
    def setUp(self):
        self.config = template('nexus'); configure(self.config)

    def test_only_explicit_fixed_public_reads_can_omit_credentials(self):
        for sid in reads.SPECS:
            cfg = self.config['tenants']['nexus']['services'][sid]
            op = next(iter(reads.SPECS[sid]))
            req = build(sid, op, {}, cfg)
            self.assertEqual([], req['secret_values']); self.assertNotIn('Authorization', req['headers'])
            self.assertFalse(req['mutates'])
            for diff in ({'public_access_reviewed': False}, {'token_env': 'VERDUGO_SECRET'},
                         {'auth_mode': 'bearer'}, {'base_url': 'https://other.invalid'}):
                with self.assertRaises(VerdugoError): build(sid, op, {}, cfg | diff)
            for field in ('url', 'query', 'token', 'method', 'headers', 'tenant', 'page'):
                with self.assertRaises(VerdugoError): build(sid, op, {field: 'forbidden'}, cfg)
        with self.assertRaises(VerdugoError): connection('chatwoot', {'base_url': 'https://example.invalid', 'token_env': None})

    def test_query_scope_and_projection_are_strict(self):
        for sid in reads.SPECS:
            cfg = self.config['tenants']['nexus']['services'][sid]; op = next(iter(reads.SPECS[sid]))
            req = build(sid, op, {}, cfg)
            out = check(sid, op, REPLIES[sid], req['public'])
            self.assertNotIn(PRIVATE, json.dumps(out)); self.assertFalse(out['live_verified'])
            for bad in (None, {'error': 'failed'}, [None, None]):
                with self.assertRaises(VerdugoError): check(sid, op, bad, req['public'])
        cfg = self.config['tenants']['nexus']['services']['wbgapi']; op = 'population.read'
        req = build('wbgapi', op, {}, cfg)
        for change in ({'countryiso3code': 'USA'}, {'date': '2023'}, {'value': True}, {'value': -1}, {'value': float('nan')}):
            response = copy.deepcopy(REPLIES['wbgapi']); response[1][0].update(change)
            with self.assertRaises(VerdugoError): check('wbgapi', op, response, req['public'])
        self.assertEqual(0, check('gdeltdoc', 'articles.summary', {})['articles_in_response'])

    def test_transport_and_sqlite_restart(self):
        for sid, payload in REPLIES.items():
            calls = []
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args): pass
                def do_GET(self):
                    calls.append(dict(self.headers))
                    self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                    self.wfile.write(json.dumps(payload).encode())
            with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
                t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
                try:
                    cfg = self.config['tenants']['nexus']['services'][sid] | {'allow_local_http': True}
                    op = next(iter(reads.SPECS[sid])); request = build(sid, op, {}, cfg)
                    # Test-only destination after fixed-origin validation, never exposed by a tool.
                    request['public']['url'] = request['public']['url'].replace(reads.ORIGINS[sid], 'http://127.0.0.1:' + str(server.server_port))
                    projected = check(sid, op, send(request, cfg), request['public'])
                    self.assertNotIn(PRIVATE, json.dumps(projected)); self.assertEqual(1, len(calls))
                    self.assertNotIn('Authorization', calls[0]); self.assertNotIn('Cookie', calls[0])
                finally:
                    server.shutdown(); t.join()
        request = {'id': 'public-observations', 'services': sorted(reads.SPECS), 'dataset': 'demo', 'currency': 'MXN'}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)/'state.db'
            with closing(Engine(state, self.config, transport=lambda r, c: copy.deepcopy(REPLIES[r['public']['service']]))) as e:
                result = product.observe(e, request, True); self.assertEqual('succeeded', result['state'], result)
                self.assertEqual(2, result['new_observations']); self.assertNotIn(PRIVATE, '\n'.join(e.db.iterdump()))
            with closing(Engine(state, self.config, transport=lambda *a: self.fail('Replay called provider'))) as e:
                self.assertEqual(2, product.observe(e, request, True)['reused_observations'])
