"""Bounded API recipes. No arbitrary URL, shell command, or message-send action."""
import base64
import os
import re
from urllib.parse import urlencode, urlsplit
from .common import VerdugoError, fields, text, integer, identifier, digest, encode

# API-contract implementations; live compatibility is NOT established by this list.
SPECS = {
 'twenty': {'people.list': ('GET', '/rest/people'), 'people.create': ('POST', '/rest/people')},
 'chatwoot': {'conversations.list': ('GET', '/api/v1/accounts/{account_id}/conversations'),
              'contacts.create': ('POST', '/api/v1/accounts/{account_id}/contacts')},
 'listmonk': {'lists.list': ('GET', '/api/lists')},
 'umami': {'websites.list': ('GET', '/api/websites')},
 'meilisearch': {'indexes.list': ('GET', '/indexes')},
 'qdrant': {'collections.list': ('GET', '/collections')},
 'metabase': {'dashboards.list': ('GET', '/api/dashboard')},
 'grafana': {'dashboards.list': ('GET', '/api/search')},
 'prometheus': {'query': ('GET', '/api/v1/query')},
 'shlink': {'links.list': ('GET', '/rest/v3/short-urls')},
 'activepieces': {'flows.list': ('GET', '/api/v1/flows')},
 'n8n': {'workflows.list': ('GET', '/api/v1/workflows')},
 'frappe-crm': {'leads.list': ('GET', '/api/resource/CRM%20Lead')},
 'erpnext': {'customers.list': ('GET', '/api/resource/Customer')},
 'posthog': {'dashboards.list': ('GET', '/api/projects/{project_id}/dashboards/')},
 'lago': {'customers.list': ('GET', '/api/v1/customers')},
 'langfuse': {'projects.list': ('GET', '/api/public/projects')},
 'changedetection': {'watches.list': ('GET', '/api/v1/watch')},
}
HEADERS = {'qdrant': 'api-key', 'metabase': 'X-API-Key',
           'shlink': 'X-Api-Key', 'n8n': 'X-N8N-API-KEY',
           'changedetection': 'x-api-key'}


def service_config(config, tenant, service):
    return config.get('tenants', {}).get(tenant, {}).get('services', {}).get(service, {})


def validate_origin(cfg):
    origin = cfg.get('base_url', '')
    u = urlsplit(origin)
    if (not u.hostname or u.username or u.password or u.query or u.fragment
            or u.path not in ('', '/') or origin != origin.strip()):
        raise VerdugoError('base_url must be an origin, without credentials or a path')
    if u.scheme != 'https':
        if not (cfg.get('allow_local_http') is True and u.scheme == 'http'
                and u.hostname in ('127.0.0.1', '::1', 'localhost')):
            raise VerdugoError('HTTPS required; HTTP allowed only for explicit loopback tests')
    try:
        _ = u.port
    except ValueError as exc:
        raise VerdugoError('Invalid port') from exc
    return origin.rstrip('/')


def connection(service, cfg):
    """Validate destination/auth independently of workflow-dependent parameters."""
    origin = validate_origin(cfg)
    env_name = cfg.get('token_env', '')
    if not isinstance(env_name, str) or not re.fullmatch(r'VERDUGO_[A-Z0-9_]+', env_name):
        raise VerdugoError('A VERDUGO_* secret environment reference is required')
    token = os.environ.get(env_name, '')
    if not token or len(token) > 8192 or any(not 33 <= ord(c) <= 126 for c in token):
        raise VerdugoError('Missing or invalid service credential: ' + env_name)
    headers = {'Accept': 'application/json', 'User-Agent': 'Verdugo-Digital/0.2'}
    if service in HEADERS:
        headers[HEADERS[service]] = token
    elif service in ('listmonk', 'langfuse'):
        username = text(cfg.get('username'), 200)
        if ':' in username: raise VerdugoError('Invalid API username')
        headers['Authorization'] = 'Basic ' + base64.b64encode(
            (username + ':' + token).encode()).decode()
    elif service in ('frappe-crm', 'erpnext'):
        if token.count(':') != 1 or not all(token.split(':')):
            raise VerdugoError('Frappe credential must contain api_key:api_secret')
        headers['Authorization'] = 'token ' + token
    elif service == 'chatwoot' and cfg.get('auth_mode') == 'api_access_token':
        headers['api_access_token'] = token
    else:
        if service == 'chatwoot' and cfg.get('auth_mode', 'bearer') != 'bearer':
            raise VerdugoError('Unsupported Chatwoot auth mode')
        headers['Authorization'] = 'Bearer ' + token
    return origin, token, headers


def remote_id(result, path):
    """Administrator-selected JSON path, not an expression or inferred schema."""
    if not isinstance(path, str) or not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){0,11}', path):
        raise VerdugoError('Explicit bounded result_id_path required for contact writes')
    value = result
    for part in path.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise VerdugoError('Creation response has no ID at the configured path; reconcile before retrying')
    if type(value) is int and value > 0: return str(value)
    if isinstance(value, str): return identifier(value)
    raise VerdugoError('Creation response contains an invalid remote ID')


def build(service, operation, params, cfg):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Adapter/action not implemented: %s.%s' % (service, operation))
    method, path = SPECS[service][operation]
    query, body = {}, None
    if operation.endswith('.create'):
        fields(params, ('first_name', 'email'), ('last_name',))
        first = text(params['first_name'], 100)
        last = text(params.get('last_name', ' '), 100) if params.get('last_name') else ''
        email = text(params['email'], 254)
        if email.count('@') != 1 or ' ' in email:
            raise VerdugoError('Invalid email')
        if service == 'twenty':
            body = {'name': {'firstName': first, 'lastName': last},
                    'emails': {'primaryEmail': email}}
        else:
            body = {'name': (first + ' ' + last).strip(), 'email': email,
                    'inbox_id': integer(cfg.get('inbox_id'), 1)}
    elif service == 'prometheus':
        fields(params, ('query',))
        # Administrator-authored allowlist, not arbitrary expensive PromQL from an agent.
        q = text(params['query'], 500)
        if q not in cfg.get('allowed_queries', []):
            raise VerdugoError('Prometheus query is not allowlisted')
        query = {'query': q, 'timeout': '5s', 'limit': 100}
    else:
        fields(params, (), ('page',))
        page = integer(params.get('page', 1), 1, 1000)
        if service in ('frappe-crm', 'erpnext'):
            selected = ['name', 'lead_name', 'email'] if service == 'frappe-crm' else ['name', 'customer_name']
            query = {'fields': encode(selected), 'limit_page_length': 50,
                     'limit_start': (page-1)*50, 'order_by': 'name asc'}
        elif service == 'posthog':
            query = {'limit': 50, 'offset': (page-1)*50}
        elif service == 'lago':
            query = {'page': page, 'per_page': 50}
        elif service == 'twenty':
            if page != 1:
                raise VerdugoError('Twenty cursor pagination is not implemented')
            query = {'limit': 50}
        elif service in ('chatwoot', 'listmonk', 'umami', 'shlink', 'grafana'):
            query = {'page': page}
            if service == 'listmonk': query['per_page'] = 50
            if service == 'grafana': query.update(type='dash-db', limit=50)
        elif page != 1:
            raise VerdugoError('Pagination not implemented for this adapter')
        if service in ('n8n', 'activepieces'): query['limit'] = 50
        if service == 'meilisearch': query.update(offset=0, limit=50)
    if service == 'chatwoot':
        path = path.format(account_id=integer(cfg.get('account_id'), 1))
    if service == 'posthog':
        path = path.format(project_id=integer(cfg.get('project_id'), 1))
    if service == 'activepieces':
        query['projectId'] = identifier(cfg.get('project_id'))
    origin, token, headers = connection(service, cfg)
    if body is not None: headers['Content-Type'] = 'application/json'
    url = origin + path + ('?' + urlencode(query) if query else '')
    public = {'service': service, 'operation': operation, 'method': method,
              'url': url, 'body': body, 'version': cfg.get('version'),
              'credential_binding': digest(headers),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    if method != 'GET':
        result_path = cfg.get('result_id_path')
        if not isinstance(result_path, str) or not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){0,11}', result_path):
            raise VerdugoError('result_id_path must be verified against the deployed API schema')
        public['result_id_path'] = result_path
        scope = (identifier(cfg.get('workspace_id')) if service == 'twenty'
                 else str(integer(cfg.get('account_id'), 1)))
        public['identity_scope'] = digest({'origin': origin, 'workspace': scope})
    return {'public': public, 'headers': headers, 'mutates': method != 'GET',
            'secret_values': [token] + [v for k, v in headers.items() if k not in ('Accept', 'User-Agent', 'Content-Type')]}
