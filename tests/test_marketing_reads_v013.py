"""HTTP contract acceptance; fixtures are synthetic, not production certification."""
import base64
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo import marketing_reads as mr, workflow
from verdugo.mcp import invoke
from verdugo.transport import send

PRIVATE = 'never-retain-this@example.invalid'
TOKEN = 'contract-token-never-real'
GHOST_KEY = '1' * 24 + ':' + '2' * 64


def config():
    cfg = template('nexus')
    for sid in mr.SPECS:
        cfg['tenants']['nexus']['services'][sid].update(
            enabled=True, license_reviewed=True, version='contract-fixture-only')
    for sid in ('plausible', 'matomo'):
        cfg['tenants']['nexus']['services'][sid].update(
            site_id='example.invalid' if sid == 'plausible' else 1,
            report_start_date='2026-10-01', report_end_date='2026-10-07')
    return cfg


def reply(sid, body=None):
    if sid == 'postiz':
        return [{'id': 'one', 'name': PRIVATE, 'disabled': False},
                {'id': 'two', 'profile': PRIVATE, 'disabled': True}]
    if sid == 'payload':
        return {'docs': [{'_status': 'draft', 'id': 'one', 'content': PRIVATE}],
                'hasNextPage': True, 'totalDocs': 8000}
    if sid == 'ghost':
        return {'posts': [{'id': 'one', 'status': 'published', 'html': PRIVATE}],
                'meta': {'pagination': {'next': None}}}
    if sid == 'saleor':
        return {'data': {'products': {'edges': [{'node': {'id': 'one', 'name': PRIVATE}}],
                                      'pageInfo': {'hasNextPage': True}}}}
    if sid == 'matomo':
        return {'nb_visits': 12, 'nb_actions': 20, 'extra': PRIVATE}
    return {'results': [{'metrics': [9, 12, 20], 'dimensions': []}],
            'query': copy.deepcopy(body), 'private_extra': PRIVATE}


class MarketingReadsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'db.sqlite3'
        self.config = config()
        self.env = patch.dict(os.environ, {c['token_env']: GHOST_KEY if sid == 'ghost' else TOKEN
            for sid, c in self.config['tenants']['nexus']['services'].items() if sid in mr.SPECS})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def cmd(self, sid, params=None, key=None):
        return {'service': sid, 'operation': next(iter(mr.SPECS[sid])),
                'params': params or {}, 'key': key or 'marketing-' + sid}

    def request(self, sid, params=None):
        command = self.cmd(sid, params)
        return build(sid, command['operation'], command['params'],
                     self.config['tenants']['nexus']['services'][sid])

    def test_fixed_methods_and_read_only_flags(self):
        for sid in mr.SPECS:
            with self.subTest(service=sid):
                req = self.request(sid)
                self.assertFalse(req['mutates'])
                self.assertTrue(req['public']['read_only'])
                self.assertNotIn(TOKEN, json.dumps(req['public']))
                self.assertNotIn(GHOST_KEY, json.dumps(req['public']))
                method = req['public']['method']
                self.assertEqual('POST' if sid in ('matomo', 'plausible', 'saleor') else 'GET', method)
                self.assertEqual(64, len(req['public']['implementation_binding']))

    def test_postiz_cloud_and_self_hosted_have_distinct_fixed_paths(self):
        cfg = self.config['tenants']['nexus']['services']['postiz']
        for surface, path in [('cloud', '/public/v1/integrations'),
                              ('self_hosted', '/api/public/v1/integrations')]:
            cfg['api_surface'] = surface
            req = self.request('postiz')
            self.assertEqual(path, urlsplit(req['public']['url']).path)
            self.assertEqual(TOKEN, req['headers']['Authorization'])
        cfg['api_surface'] = 'custom'
        with self.assertRaises(VerdugoError): self.request('postiz')

    def test_payload_auth_and_path_are_operator_owned(self):
        req = self.request('payload')
        self.assertEqual('users API-Key ' + TOKEN, req['headers']['Authorization'])
        self.assertEqual('/api/posts', urlsplit(req['public']['url']).path)
        cfg = self.config['tenants']['nexus']['services']['payload']
        for collection in ('../users', 'users', 'posts?key=bad', 'payload-preferences', 'x/y'):
            cfg['content_collection'] = collection
            with self.subTest(collection=collection), self.assertRaises(VerdugoError):
                self.request('payload')
        cfg['content_collection'] = 'pages'
        self.assertEqual('/api/pages', urlsplit(self.request('payload')['public']['url']).path)

    def test_ghost_jwt_hs256_and_five_minute_expiry(self):
        req = self.request('ghost')
        self.assertEqual('v6.0', req['headers']['Accept-Version'])
        header, payload, signature = req['headers']['Authorization'].split(' ', 1)[1].split('.')
        unpack = lambda x: json.loads(base64.urlsafe_b64decode(x + '=' * (-len(x) % 4)))
        self.assertEqual({'alg': 'HS256', 'kid': '1'*24, 'typ': 'JWT'}, unpack(header))
        data = unpack(payload)
        self.assertEqual('/admin/', data['aud'])
        self.assertEqual(300, data['exp'] - data['iat'])
        sig = hmac.new(bytes.fromhex('2'*64), (header+'.'+payload).encode(), hashlib.sha256).digest()
        self.assertEqual(base64.urlsafe_b64encode(sig).decode().rstrip('='), signature)

    def test_ghost_renewed_jwt_preserves_fingerprint_but_key_rotation_does_not(self):
        engine = Engine(':memory:', self.config)
        try:
            with patch.object(mr.time, 'time', return_value=100000):
                first = engine.plan(self.cmd('ghost'))
            with patch.object(mr.time, 'time', return_value=100700):
                second = engine.plan(self.cmd('ghost'))
            self.assertEqual(first['fingerprint'], second['fingerprint'])
            name = self.config['tenants']['nexus']['services']['ghost']['token_env']
            with patch.dict(os.environ, {name: '1'*24+':'+'3'*64}):
                with self.assertRaises(VerdugoError): engine.plan(self.cmd('ghost'))
        finally: engine.close()

    def test_invalid_ghost_keys_and_header_versions_are_rejected(self):
        cfg = self.config['tenants']['nexus']['services']['ghost']
        for value in ('bad', 'a:b', 'z'*24+':'+'2'*64, '1'*24+':'+'2'*63):
            with patch.dict(os.environ, {cfg['token_env']: value}), self.assertRaises(VerdugoError):
                self.request('ghost')
        cfg['api_version'] = 'v6.0\r\nAuthorization: injected'
        with self.assertRaises(VerdugoError): self.request('ghost')

    def test_matomo_secret_is_only_in_private_form(self):
        req = self.request('matomo')
        self.assertNotIn('Authorization', req['headers'])
        public = json.dumps(req['public'])
        self.assertNotIn(TOKEN, public)
        self.assertNotIn('token_auth', public)
        wire = parse_qs(mr.form_bytes(req).decode())
        self.assertEqual([TOKEN], wire['token_auth'])
        self.assertEqual(['VisitsSummary.get'], wire['method'])
        self.assertEqual(['1'], wire['idSite'])
        invalid = copy.deepcopy(req)
        invalid['public']['body']['method'] = 'UsersManager.deleteUser'
        with self.assertRaises(VerdugoError): mr.form_bytes(invalid)

    def test_fixed_graphql_query_has_no_user_selected_code(self):
        req = self.request('saleor')
        self.assertEqual(mr.PRODUCT_QUERY, req['public']['body']['query'])
        self.assertNotIn('mutation', mr.PRODUCT_QUERY)
        self.assertIn('first: 20', mr.PRODUCT_QUERY)
        self.assertEqual({'channel': 'default-channel'}, req['public']['body']['variables'])
        self.assertEqual('Bearer '+TOKEN, req['headers']['Authorization'])

    def test_arbitrary_parameters_cannot_change_destinations_or_operations(self):
        for sid in mr.SPECS:
            for params in ({'url': 'https://evil.invalid'}, {'query': 'mutation Delete {}'},
                           {'headers': {}}, {'token': TOKEN}, {'site_id': 2},
                           {'collection': 'users'}, {'body': {}}, {'method': 'DELETE'},
                           {'tenant': 'other'}, {'channel': 'other'}):
                with self.subTest(sid=sid, params=params), self.assertRaises(VerdugoError):
                    self.request(sid, params)
            with self.assertRaises(VerdugoError):
                build(sid, 'publish.now', {}, self.config['tenants']['nexus']['services'][sid])

    def test_dates_are_explicit_bounded_and_real_calendar_days(self):
        for sid in ('plausible', 'matomo'):
            for params in ({'start_date': '2026-01-01'}, {'end_date': '2026-01-02'},
                           {'start_date': '2026-02-30', 'end_date': '2026-03-01'},
                           {'start_date': '2026-10-02', 'end_date': '2026-10-01'},
                           {'start_date': '2026-01-01', 'end_date': '2026-12-31'},
                           {'start_date': True, 'end_date': '2026-01-01'}):
                with self.subTest(sid=sid, params=params), self.assertRaises(VerdugoError):
                    self.request(sid, params)
            self.request(sid, {'start_date': '2024-02-29', 'end_date': '2024-03-01'})

    def test_pagination_is_bounded_and_no_cursors_followed(self):
        for sid in ('payload', 'ghost'):
            req = self.request(sid, {'page': 2})
            query = parse_qs(urlsplit(req['public']['url']).query)
            self.assertEqual(['2'], query['page'])
            self.assertEqual(['20'], query['limit'])
            for value in (0, True, '2', 1001):
                with self.assertRaises(VerdugoError): self.request(sid, {'page': value})
        with self.assertRaises(VerdugoError): self.request('postiz', {'page': 2})
        with self.assertRaises(VerdugoError): self.request('saleor', {'after': 'arbitrary'})

    def test_response_projection_preserves_useful_counts_not_private_content(self):
        for sid in mr.SPECS:
            req = self.request(sid)
            response = mr.check(sid, self.cmd(sid)['operation'], reply(sid, req['public']['body']), req['public'])
            self.assertFalse(response['raw_provider_payload_retained'])
            self.assertFalse(response['live_verified'])
            self.assertNotIn(PRIVATE, json.dumps(response))
            if sid == 'postiz':
                self.assertEqual((1, 1), (response['enabled_channels'], response['disabled_channels']))
            if sid == 'plausible': self.assertEqual({'visitors': 9, 'visits': 12, 'pageviews': 20}, response['metrics'])
            if sid == 'matomo': self.assertEqual({'nb_visits': 12, 'nb_actions': 20}, response['metrics'])

    def test_failed_graphql_and_wrong_site_dates_or_metrics_never_succeed(self):
        req = self.request('plausible')
        for field, value in [('site_id', 'other.invalid'), ('metrics', ['visitors']),
                             ('dimensions', ['visit:city']), ('date_range', ['2020-01-01','2020-01-02'])]:
            data = reply('plausible', req['public']['body'])
            data['query'][field] = value
            with self.subTest(field=field), self.assertRaises(VerdugoError):
                mr.check('plausible', 'traffic.summary', data, req['public'])
        for errors in ([{'message': PRIVATE}], {'message': PRIVATE}, None, ''):
            data = reply('saleor'); data['errors'] = errors
            with self.assertRaises(VerdugoError): mr.check('saleor', 'products.list', data)
        data = reply('plausible', req['public']['body'])
        data['query']['date_range'] = ['2026-10-01T00:00:00+00:00','2026-10-07T23:59:59+00:00']
        self.assertEqual(9, mr.check('plausible','traffic.summary',data,req['public'])['metrics']['visitors'])

    def test_invalid_shapes_nonfinite_metrics_and_missing_objects_fail_closed(self):
        for sid in mr.SPECS:
            for value in (None, 'text', {'error': 'bad'}, {'data': []}, [1]):
                with self.subTest(sid=sid, value=value), self.assertRaises(VerdugoError):
                    mr.check(sid, self.cmd(sid)['operation'], value, self.request(sid)['public'])
        for value in (True, float('nan'), float('inf'), -1, '20', None, 10**400):
            data = reply('matomo'); data['nb_visits'] = value
            with self.assertRaises(VerdugoError):
                mr.check('matomo','visits.summary',data,self.request('matomo')['public'])
        with self.assertRaises(VerdugoError):
            mr.check('payload','documents.list',{'docs': [],'hasNextPage': 'true'})
        with self.assertRaises(VerdugoError):
            mr.check('postiz','channels.list',[{'disabled': 'false'}])

    def test_previews_roles_licenses_and_disabled_defaults(self):
        fresh = template('nexus')
        for sid in mr.SPECS: self.assertFalse(fresh['tenants']['nexus']['services'][sid]['enabled'])
        engine = Engine(':memory:', self.config, transport=lambda *_: self.fail('unexpected network'))
        try:
            for sid in mr.SPECS:
                self.assertFalse(engine.plan(self.cmd(sid))['requires_approval'])
                cfg = self.config['tenants']['nexus']['services'][sid]
                cfg['license_reviewed'] = False
                with self.assertRaises(VerdugoError): engine.plan(self.cmd(sid))
                cfg['license_reviewed'] = True
                cfg['enabled'] = False
                with self.assertRaises(VerdugoError): engine.plan(self.cmd(sid))
                cfg['enabled'] = True
        finally: engine.close()
        viewer = Engine(':memory:', self.config, role='viewer')
        try:
            for sid in mr.SPECS:
                with self.assertRaises(VerdugoError): viewer.execute(self.cmd(sid), True)
        finally: viewer.close()

    def test_missing_credentials_and_configured_scope_changes_invalidate(self):
        with patch.dict(os.environ, {}, clear=True):
            for sid in mr.SPECS:
                with self.assertRaises(VerdugoError): self.request(sid)
        engine = Engine(':memory:', self.config)
        try:
            for sid, field, value in [('plausible','site_id','other.invalid'),('matomo','site_id',2),
                                      ('saleor','channel','other-channel'),('payload','content_collection','pages'),
                                      ('postiz','api_surface','cloud'),('ghost','api_version','v5.0')]:
                engine.plan(self.cmd(sid))
                self.config['tenants']['nexus']['services'][sid][field] = value
                with self.assertRaises(VerdugoError): engine.plan(self.cmd(sid))
        finally: engine.close()

    def test_mcp_cli_and_six_step_workflow_use_existing_engine(self):
        engine = Engine(self.state, self.config, transport=lambda req, cfg: reply(req['public']['service'], req['public']['body']))
        spec = {'id': 'marketing-fixture', 'steps': [dict(id=sid, service=sid,
                operation=next(iter(mr.SPECS[sid])), params={}) for sid in mr.SPECS]}
        try:
            plan = invoke(engine, 'verdugo_workflow', {'workflow': spec})
            self.assertEqual([], plan['approval_batch'])
            result = workflow.run(engine, spec, True)
            self.assertEqual('succeeded', result['state'])
            self.assertEqual(6, len(result['steps']))
            self.assertNotIn(PRIVATE, json.dumps(result))
        finally: engine.close()
        engine = Engine(self.state, self.config, transport=lambda *_: self.fail('replayed workflow made network call'))
        try: self.assertEqual(result, workflow.run(engine, spec, True))
        finally: engine.close()
        cfg_file = Path(self.tmp.name) / 'config.local.json'; cfg_file.write_text(json.dumps(self.config))
        proc = subprocess.run([sys.executable,'-m','verdugo','--state',':memory:',
                               '--config',str(cfg_file),'plan',json.dumps(self.cmd('saleor'))],
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)['requires_approval'])

    def test_http_errors_and_redirects_fail_without_retries_or_leaks(self):
        called = []
        selected = [401]
        class FailureServer(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def fail(self):
                self.rfile.read(int(self.headers.get('Content-Length', '0')))
                called.append(self.path)
                data = json.dumps({'message': PRIVATE}).encode()
                self.send_response(selected[0])
                if selected[0] == 302: self.send_header('Location', '/do-not-follow')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                try: self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError): pass
            do_GET = fail
            do_POST = fail
        server = HTTPServer(('127.0.0.1', 0), FailureServer)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            for sid in ('ghost', 'plausible', 'matomo', 'saleor'):
                self.config['tenants']['nexus']['services'][sid].update(
                    base_url='http://127.0.0.1:'+str(server.server_port), allow_local_http=True)
            engine = Engine(':memory:', self.config, transport=send)
            try:
                for status in (401, 403, 429, 302, 202, 204):
                    selected[0] = status
                    for sid in ('ghost','plausible','matomo','saleor'):
                        cmd = self.cmd(sid, key='http-'+str(status)+'-'+sid)
                        result = engine.execute(cmd, True)
                        self.assertEqual('failed', result['state'])
                        self.assertNotIn(PRIVATE, json.dumps(result))
                        self.assertFalse(result['result']['reconciliation_required'])
                        self.assertTrue(engine.execute(cmd, True)['replayed'])
                self.assertEqual(24, len(called))
                self.assertNotIn('/do-not-follow', called)
            finally: engine.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(3)

    def test_same_key_is_scoped_to_tenant_and_provider_scope(self):
        self.config['tenants']['other'] = copy.deepcopy(self.config['tenants']['nexus'])
        self.config['tenants']['other']['services']['plausible']['site_id'] = 'other.invalid'
        def transport(req, cfg):
            result = reply('plausible', req['public']['body'])
            result['results'][0]['metrics'][0] = 1 if req['public']['body']['site_id']=='example.invalid' else 2
            return result
        for tenant, expected in (('nexus',1), ('other',2), ('nexus',1)):
            engine = Engine(self.state, self.config, tenant=tenant, transport=transport)
            try:
                value = engine.execute(self.cmd('plausible'), True)
                self.assertEqual(expected, value['result']['metrics']['visitors'])
            finally: engine.close()

    def test_marketing_implementation_changes_invalidate_existing_plans(self):
        engine = Engine(':memory:', self.config)
        original = Path.read_bytes
        def altered(path):
            content = original(path)
            return content + b'\n# change' if path.name == 'marketing_reads.py' else content
        try:
            engine.plan(self.cmd('postiz'))
            with patch.object(Path, 'read_bytes', altered), self.assertRaises(VerdugoError):
                engine.plan(self.cmd('postiz'))
        finally: engine.close()

    def test_synthetic_wire_get_post_form_auth_and_sqlite_replay(self):
        paths = {'/api/public/v1/integrations':'postiz','/api/posts':'payload',
                 '/ghost/api/admin/posts/':'ghost','/api/v2/query':'plausible',
                 '/index.php':'matomo','/graphql/':'saleor'}
        seen = []
        class Server(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def _respond(self):
                sid = paths.get(urlsplit(self.path).path)
                raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                if sid == 'matomo':
                    body = parse_qs(raw.decode())
                else: body = json.loads(raw) if raw else None
                seen.append((sid, self.command, self.path, dict(self.headers), body))
                data = json.dumps(reply(sid, body)).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data)
            do_GET = _respond
            do_POST = _respond
        server = HTTPServer(('127.0.0.1',0), Server)
        thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            for sid in mr.SPECS:
                self.config['tenants']['nexus']['services'][sid].update(
                    base_url='http://127.0.0.1:'+str(server.server_port), allow_local_http=True)
            engine = Engine(self.state, self.config, transport=send)
            try:
                for sid in mr.SPECS:
                    result = engine.execute(self.cmd(sid), True)
                    self.assertEqual('succeeded', result['state'], result)
                    self.assertFalse(result['replayed'])
                    self.assertNotIn(PRIVATE, json.dumps(result))
                dump = '\n'.join(engine.db.iterdump())
                for value in (PRIVATE, TOKEN, GHOST_KEY, 'Ghost ey'): self.assertNotIn(value, dump)
            finally: engine.close()
            self.assertEqual(6, len(seen))
            for sid, method, path, headers, body in seen:
                if sid == 'matomo':
                    self.assertEqual('POST', method)
                    self.assertEqual([TOKEN], body['token_auth'])
                    self.assertNotIn(TOKEN, path)
                    self.assertNotIn('Authorization', headers)
                if sid == 'saleor': self.assertEqual(mr.PRODUCT_QUERY, body['query'])
                if sid == 'ghost': self.assertTrue(headers['Authorization'].startswith('Ghost '))
            engine = Engine(self.state, self.config, transport=send)
            try:
                for sid in mr.SPECS: self.assertTrue(engine.execute(self.cmd(sid),True)['replayed'])
            finally: engine.close()
            self.assertEqual(6, len(seen))
        finally:
            server.shutdown(); server.server_close(); thread.join(3)


if __name__ == '__main__': unittest.main()
