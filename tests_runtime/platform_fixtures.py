"""Synthetic HTTP servers only; never evidence of original service execution."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from verdugo import platform_reads

TOKEN = 'synthetic-v020-credential'
PRIVATE = 'private-person@example.invalid'
PATHS = {
    'datahub': '/openapi/v1/entities/dataset/count', 'jitsu': '/health',
    'magentic-ui': '/api/sessions/?user_id=demo-user', 'operately': '/api/external/v1/companies/list',
    'signoz': '/api/v2/dashboards?limit=50&offset=0', 'bifrost': '/api/providers',
    'killbill': '/1.0/kb/accounts/pagination?offset=0&limit=50',
    'taguette': '/api/project/1/document/2', 'ckanapi': '/api/action/package_search?q=%2A%3A%2A&rows=0',
}
REPLIES = {
    'datahub': {'entityType': 'dataset', 'keyAspect': 'datasetKey', 'activeCount': 7, 'softDeletedCount': 2, 'computedAtMillis': 1, 'cacheHit': True, 'private': PRIVATE},
    'jitsu': {'status': 'pass', 'private': PRIVATE},
    'magentic-ui': {'status': True, 'data': [{'session_id': 1, 'name': PRIVATE, 'latest_run': {'run_id': 3, 'status': 'complete'}}]},
    'operately': {'companies': [{'id': 'demo-company', 'name': PRIVATE, 'setup_completed': True}]},
    'signoz': {'status': 'success', 'data': {'dashboards': [{'locked': True, 'legacy': False, 'spec': {'private': PRIVATE}}], 'total': 3}},
    'bifrost': {'providers': [{'name': 'ollama', 'proxy_config': {'password': TOKEN}, 'description': PRIVATE}], 'total': 1},
    'killbill': [{'accountId': '00000000-0000-4000-8000-000000000001', 'name': PRIVATE}],
    'taguette': {'text_direction': 'LEFT_TO_RIGHT', 'highlights': [{'id': 1, 'start_offset': 0, 'end_offset': 10, 'tags': [1, 2], 'private': PRIVATE}]},
    'ckanapi': {'success': True, 'result': {'count': 15, 'results': [], 'facets': {'private': PRIVATE}}},
}
EXPECTED = {'datahub': {'active_datasets': 7, 'soft_deleted_datasets': 2},
    'jitsu': {'kafka_configuration_present': True, 'dependency_connectivity_verified': False},
    'magentic-ui': {'sessions_in_response': 1, 'sessions_with_latest_run': 1},
    'operately': {'companies_in_response': 1, 'setup_completed_in_response': 1},
    'signoz': {'dashboards_in_response': 1, 'matching_dashboards_reported': 3},
    'bifrost': {'configured_providers_in_response': 1, 'inference_calls_made': 0},
    'killbill': {'accounts_in_response': 1, 'billing_changed': False},
    'taguette': {'highlights_in_response': 1, 'tag_assignments_in_response': 2},
    'ckanapi': {'matching_packages_reported': 15, 'package_records_requested': 0}}


def configure(config, tenant='nexus'):
    for sid in platform_reads.SPECS:
        cfg = config['tenants'][tenant]['services'][sid]
        cfg.update(enabled=True, license_reviewed=True, version='synthetic-v020')
        if sid in platform_reads.PROXY_ONLY: cfg['proxy_auth_reviewed'] = True
        if sid in ('datahub', 'bifrost'): cfg['native_auth_enforced_reviewed'] = True
    services = config['tenants'][tenant]['services']
    services['killbill']['proxy_tenant_binding_reviewed'] = True
    services['magentic-ui'].update(user_id='demo-user', user_scope_reviewed=True)
    services['taguette'].update(project_id=1, document_id=2)
    return {services[sid]['token_env']: TOKEN for sid in platform_reads.SPECS}


@contextmanager
def wire(config):
    state = {'calls': [], 'status': 200, 'raw': None}
    routes = {path: sid for sid, path in PATHS.items()}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            sid = routes.get(self.path)
            state['calls'].append({'service': sid, 'path': self.path, 'headers': dict(self.headers)})
            if sid == 'signoz': authorized = self.headers.get('SIGNOZ-API-KEY') == TOKEN
            elif sid == 'taguette': authorized = self.headers.get('Cookie') == 'user='+TOKEN
            elif sid == 'ckanapi': authorized = self.headers.get('Authorization') == TOKEN and self.headers.get('X-CKAN-API-Key') == TOKEN
            else: authorized = self.headers.get('Authorization') == 'Bearer '+TOKEN
            self.send_response(state['status'] if sid and authorized else 401)
            content = state['raw'] if state['raw'] is not None else json.dumps(REPLIES.get(sid, {})).encode()
            self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(content)))
            if state['status'] == 302: self.send_header('Location', '/forbidden')
            self.end_headers()
            try: self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.02), daemon=True); thread.start()
    for tenant in config['tenants'].values():
        for sid in PATHS: tenant['services'][sid].update(base_url='http://127.0.0.1:'+str(server.server_port), allow_local_http=True)
    try: yield state
    finally: server.shutdown(); server.server_close(); thread.join(2)
