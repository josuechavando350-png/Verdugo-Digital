"""Contract and loopback acceptance with synthetic providers, not deployments."""
import copy
from contextlib import closing, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo import operations_reads as batch, source_evidence
from verdugo.read_contracts import check

TOKEN = 'synthetic-v019-credential'
PRIVATE = 'private-person@example.invalid'
REPLIES = {
    'apache-answer': {'code': 200, 'data': {'inbox': 5, 'achievement': 2, 'revision': 3,
        'can_revision': True, 'badge_award': {'name': PRIVATE, 'icon': TOKEN}}},
    'caddy': {'private-server': {'listen': ['127.0.0.1:8080'], 'routes': [{'private': PRIVATE}],
                                'private_metadata': TOKEN}},
    'seaweedfs': {'Version': 'synthetic', 'TopologyId': PRIVATE, 'Topology': {
        'Max': 100, 'Free': 67, 'DataCenters': [{'Id': PRIVATE}], 'Layouts': [{'Collection': TOKEN}]}},
    'dagster': {'data': {'repositoriesOrError': {'__typename': 'RepositoryConnection',
        'nodes': [{'__typename': 'Repository', 'name': PRIVATE}, {'__typename': 'Repository', 'debug': TOKEN}]}}},
}


def configured(tenant='nexus'):
    config, env = template(tenant), {}
    for sid in batch.SPECS:
        cfg = config['tenants'][tenant]['services'][sid]
        cfg.update(enabled=True, license_reviewed=True, version='synthetic-v019')
        if sid in batch.PROXY_ONLY:
            cfg['proxy_auth_reviewed'] = True
        env[cfg['token_env']] = TOKEN
    return config, env


def command(sid, key=None, params=None):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])),
            'params': params if params is not None else {}, 'key': key or sid+'-read'}


@contextmanager
def wire(config, replies=None, specs=None, auth_headers=None):
    replies = replies if replies is not None else REPLIES
    specs = specs if specs is not None else batch.SPECS
    state = {'calls': [], 'status': 200, 'raw': None}
    routes = {next(iter(ops.values()))[1]: sid for sid, ops in specs.items()}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def handle_read(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            sid = routes.get(self.path)
            state['calls'].append({'service': sid, 'method': self.command, 'path': self.path,
                                   'body': body, 'headers': dict(self.headers)})
            header, value = (auth_headers or {}).get(sid, ('Authorization', 'Bearer '+TOKEN))
            authorized = self.headers.get(header) == value
            self.send_response(state['status'] if authorized and sid else 401)
            content = state['raw'] if state['raw'] is not None else json.dumps(replies.get(sid, {})).encode()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            if state['status'] == 302: self.send_header('Location', '/forbidden-redirect')
            self.end_headers()
            try: self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError): pass
        do_GET = handle_read
        do_POST = handle_read
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.02), daemon=True)
    thread.start()
    for tenant in config['tenants'].values():
        for sid in specs:
            tenant['services'][sid].update(base_url='http://127.0.0.1:%d' % server.server_port,
                                           allow_local_http=True)
    try: yield state
    finally:
        server.shutdown(); server.server_close(); thread.join(2)


class OperationsContracts(unittest.TestCase):
    def setUp(self):
        self.config, env = configured()
        self.env = patch.dict(os.environ, env); self.env.start()
        self.addCleanup(self.env.stop)
        self.services = self.config['tenants']['nexus']['services']

    def test_exact_routes_static_graphql_and_header_credentials(self):
        expected = {'apache-answer': ('GET', '/answer/api/v1/notification/status'),
                    'caddy': ('GET', '/config/apps/http/servers'),
                    'seaweedfs': ('GET', '/dir/status'), 'dagster': ('POST', '/graphql')}
        for sid, (method, path) in expected.items():
            req = build(sid, command(sid)['operation'], {}, self.services[sid])
            self.assertEqual((method, 'https://example.invalid'+path), (req['public']['method'], req['public']['url']))
            self.assertEqual('Bearer '+TOKEN, req['headers']['Authorization'])
            self.assertFalse(req['mutates'])
            self.assertNotIn(TOKEN, json.dumps(req['public']))
            if sid == 'dagster':
                self.assertEqual('application/json', req['headers']['Content-Type'])
                self.assertEqual({'query': 'query VerdugoRepositories { repositoriesOrError { __typename ... on RepositoryConnection { nodes { __typename } } } }',
                                  'operationName': 'VerdugoRepositories'}, req['public']['body'])
            else: self.assertIsNone(req['public']['body'])

    def test_fixed_sources_and_all_evidence_files_have_real_blob_ids(self):
        manifest = json.loads((Path(__file__).resolve().parents[1]/'sources/contracts-v019.json').read_text())
        self.assertEqual(set(batch.SPECS), {r['id'] for r in manifest['records']})
        for row in manifest['records']:
            self.assertEqual(source_evidence.report(row['id'])['source_commit_sha'], row['commit'])
            self.assertEqual(batch.PINNED_COMMITS[row['id']], row['commit'])
            self.assertFalse(row['live_verified'])
            for f in row['files']:
                self.assertRegex(f['git_blob_sha'], r'^[a-f0-9]{40}$')
                self.assertIn('/blob/'+row['commit']+'/', f['source_url'])

    def test_template_never_enables_or_approves_new_services(self):
        for sid in batch.SPECS:
            cfg = template('nexus')['tenants']['nexus']['services'][sid]
            self.assertIs(False, cfg['enabled']); self.assertIs(False, cfg['license_reviewed'])
            self.assertNotIn('license_policy_exception', cfg)
            if sid in batch.PROXY_ONLY: self.assertIs(False, cfg['proxy_auth_reviewed'])

    def test_proxy_review_and_native_auth_are_not_interchangeable(self):
        for sid in batch.SPECS:
            original = dict(self.services[sid])
            for value in (None, 'bearer', 'native_oauth_bearer'):
                cfg = original | {'auth_mode': value}
                with self.assertRaises(VerdugoError): build(sid, command(sid)['operation'], {}, cfg)
            if sid in batch.PROXY_ONLY:
                for value in (False, None, 1, 'true'):
                    with self.assertRaises(VerdugoError):
                        build(sid, command(sid)['operation'], {}, original | {'proxy_auth_reviewed': value})

    def test_no_arbitrary_graphql_urls_tokens_tenants_or_pagination(self):
        for sid in batch.SPECS:
            for params in ({'query': 'mutation { delete }'}, {'url': 'https://evil.invalid'},
                           {'token': TOKEN}, {'tenant': 'other'}, {'method': 'DELETE'},
                           {'page': 2}, {'page': True}, {'page': '1'}, {'namespace': 'other'}):
                with self.subTest(sid=sid, params=params), self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], params, self.services[sid])
            with self.assertRaises(VerdugoError): build(sid, 'delete', {}, self.services[sid])

    def test_expected_counts_only_no_raw_personal_or_infrastructure_data(self):
        expected = {'apache-answer': {'inbox_unread':5, 'achievements_unread':2, 'revisions_pending':3},
                    'caddy': {'http_servers_in_response':1, 'listeners_in_response':1, 'routes_in_response':1},
                    'seaweedfs': {'volume_slots_max':100, 'volume_slots_free':67, 'data_centers_in_response':1},
                    'dagster': {'repositories_in_response':2}}
        for sid, values in expected.items():
            r = check(sid, command(sid)['operation'], REPLIES[sid])
            for key, value in values.items(): self.assertEqual(value, r[key])
            for secret in (PRIVATE, TOKEN, 'private-server', '127.0.0.1'): self.assertNotIn(secret, json.dumps(r))
            self.assertFalse(r['raw_provider_payload_retained']); self.assertFalse(r['live_verified'])

    def test_bad_envelopes_fail_without_returning_provider_error_messages(self):
        for sid in batch.SPECS:
            for data in (None, [], True, {'error': PRIVATE}):
                with self.subTest(sid=sid), self.assertRaises(VerdugoError) as err:
                    check(sid, command(sid)['operation'], data)
                self.assertNotIn(PRIVATE, str(err.exception))

    def test_answer_rejects_non_success_or_invalid_count_and_boolean(self):
        for key, value in [('inbox', True), ('achievement', -1), ('revision', '3'),
                           ('revision', 10**12+1), ('can_revision', 1)]:
            data = copy.deepcopy(REPLIES['apache-answer']); data['data'][key] = value
            with self.assertRaises(VerdugoError): check('apache-answer', 'notifications.summary', data)
        for code in (True, '200', 401, None):
            data = copy.deepcopy(REPLIES['apache-answer']); data['code'] = code
            with self.assertRaises(VerdugoError): check('apache-answer', 'notifications.summary', data)

    def test_caddy_checks_servers_listener_routes_and_total_bound(self):
        for data in ({'x':None}, {'x':{'listen':'bad'}}, {'x':{'listen':[1]}}, {'x':{'routes':[True]}},
                     {'x':{'listen':['x']*1001}}, {'x':{'routes':[{}]*1001}},
                     {str(i): {} for i in range(1001)}, {'x':{'listen':['x']*600}, 'y':{'listen':['y']*600}}):
            with self.assertRaises(VerdugoError): check('caddy', 'http_servers.summary', data)
        self.assertEqual(0, check('caddy', 'http_servers.summary', {})['http_servers_in_response'])

    def test_storage_empty_go_slices_are_zero_but_missing_keys_are_errors(self):
        data = {'Version':'synthetic', 'Topology':{'Max':0, 'Free':-2, 'DataCenters':None, 'Layouts':None}}
        r = check('seaweedfs', 'topology.summary', data)
        self.assertEqual(0, r['data_centers_in_response']); self.assertEqual(-2,r['volume_slots_free'])
        for key in data['Topology']:
            bad = copy.deepcopy(data); del bad['Topology'][key]
            with self.assertRaises(VerdugoError): check('seaweedfs', 'topology.summary', bad)

    def test_storage_wrong_types_and_overflow_fail(self):
        for key, value in [('Max',True), ('Free','1'), ('DataCenters',{}), ('Layouts',[{}]*1001)]:
            data = copy.deepcopy(REPLIES['seaweedfs']); data['Topology'][key] = value
            with self.assertRaises(VerdugoError): check('seaweedfs', 'topology.summary', data)

    def test_graphql_partial_errors_union_errors_and_wrong_nodes_fail(self):
        for data in ({'errors':[{'message':PRIVATE}], **REPLIES['dagster']},
                     {'data': {'repositoriesOrError': {'__typename':'PythonError', 'message':PRIVATE}}},
                     {'data': {'repositoriesOrError': {'__typename':'RepositoryConnection', 'nodes':None}}},
                     {'data': {'repositoriesOrError': {'__typename':'RepositoryConnection', 'nodes':[{'__typename':'Fake'}]}}},
                     {'data': {'repositoriesOrError': {'__typename':'RepositoryConnection', 'nodes':[{}]*1001}}}):
            with self.assertRaises(VerdugoError): check('dagster','repositories.summary',data)
        data = {'data':{'repositoriesOrError':{'__typename':'RepositoryConnection','nodes':[]}}}
        self.assertEqual(0,check('dagster','repositories.summary',data)['repositories_in_response'])

    def test_changed_versions_credentials_and_proxy_revocation_block_replay(self):
        for sid in batch.SPECS:
            cfg = self.services[sid]
            with closing(Engine(':memory:', self.config, transport=lambda *a: REPLIES[sid])) as engine:
                self.assertEqual('succeeded',engine.execute(command(sid),True)['state'])
                with patch.dict(os.environ,{cfg['token_env']:'changed-credential'}):
                    with self.assertRaises(VerdugoError): engine.execute(command(sid),True)
                cfg['version']='changed'
                with self.assertRaises(VerdugoError): engine.execute(command(sid),True)
                cfg['version']='synthetic-v019'
                cfg['enabled']=False
                with self.assertRaises(VerdugoError): engine.execute(command(sid),True)

    def test_real_http_all_four_routes_and_only_static_post_body(self):
        with wire(self.config) as state, closing(Engine(':memory:', self.config)) as engine:
            for sid in batch.SPECS: self.assertEqual('succeeded',engine.execute(command(sid),True)['state'])
            self.assertEqual(4,len(state['calls']))
            post = [r for r in state['calls'] if r['method']=='POST']
            self.assertEqual(1,len(post)); self.assertEqual('dagster',post[0]['service'])
            self.assertEqual(batch.DAGSTER_QUERY,json.loads(post[0]['body'])['query'])
            self.assertEqual('application/json',post[0]['headers']['Content-Type'])
            dump='\n'.join(engine.db.iterdump())
            self.assertNotIn(PRIVATE,dump); self.assertNotIn(TOKEN,dump)

    def test_http_redirect_async_unauthorized_and_error_are_failures(self):
        with wire(self.config) as state:
            for sid in batch.SPECS:
                for status in (202,204,302,401,403,429,500):
                    state['status']=status
                    with closing(Engine(':memory:',self.config)) as engine:
                        self.assertEqual('failed',engine.execute(command(sid),True)['state'])
            self.assertEqual(28,len(state['calls']))

    def test_oversize_and_invalid_json_never_persist(self):
        with wire(self.config) as state:
            for body in (b' '*(1024*1024+1), ('<html>'+PRIVATE).encode()):
                state['raw']=body
                with closing(Engine(':memory:',self.config)) as engine:
                    self.assertEqual('failed',engine.execute(command('dagster'),True)['state'])
                    self.assertNotIn(PRIVATE,'\n'.join(engine.db.iterdump()))


if __name__ == '__main__': unittest.main()
