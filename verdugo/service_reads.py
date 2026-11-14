"""v0.15: thirteen bounded read-only service contracts for the 300 portfolio.

Every route below was taken from the upstream source or OpenAPI file at the
pinned commit in sources/parts (see docs/CONECTORES_V015.md). Only GET is used,
parameters are fixed in code, pagination is a single first page and the
response is reduced to counts before Engine persists anything. No prompt,
inference, message, payment, sandbox creation or other write is possible.

Only free, self-hostable services are connected (paid providers were removed by
the operator). FIXED_ORIGINS stays available to bind any future cloud provider
to its official origin. A successful read proves a response shape,
never a production deployment or a business result.
"""
import base64
import re

from .common import VerdugoError, fields, integer

SPECS = {
    'vllm': {'models.list': ('GET', '/v1/models')},
    'ollama': {'models.list': ('GET', '/api/tags')},
    'label-studio': {'projects.list': ('GET', '/api/projects/')},
    'grist': {'orgs.list': ('GET', '/api/orgs')},
    'datasette': {'databases.list': ('GET', '/-/databases.json')},
    'svix': {'applications.list': ('GET', '/api/v1/app')},
    'cube': {'cubes.list': ('GET', '/cubejs-api/v1/meta')},
    'langflow': {'flows.list': ('GET', '/api/v1/flows/')},
    # Android SMS Gateway local server (the phone itself); counts devices/SIMs only.
    'android-sms-gateway': {'devices.list': ('GET', '/devices')},
    # SendPortal API (sendportal-core): campaign counts by status, no content.
    'sendportal': {'campaigns.summary': ('GET', '/api/v1/campaigns')},
    # CrowdSec LAPI bouncer read. Note: upstream updates the bouncer's last_pull time.
    'crowdsec': {'decisions.summary': ('GET', '/v1/decisions')},
    # ClickHouse HTTP GET runs readonly; the only query is the fixed one below.
    'clickhouse': {'databases.count': ('GET', '/')},
    'dittofeed': {'segments.list': ('GET', '/api/admin/segments')},
}
CLICKHOUSE_QUERY = 'SELECT count() AS databases FROM system.databases FORMAT JSON'
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

# Official API origins; configuration cannot redirect these credentials.
FIXED_ORIGINS = {}

QUERIES = {
    'label-studio': {'page': 1, 'page_size': 30},
    'svix': {'limit': 50},
    'langflow': {'get_all': 'false', 'header_flows': 'true', 'remove_example_flows': 'true',
                 'page': 1, 'size': 50},
}

# Where the bounded list lives in each response (None: the body is the list).
LIST_PATHS = {
    'vllm': ('data',), 'ollama': ('models',), 'label-studio': ('results',),
    'grist': None, 'datasette': None, 'svix': ('data',), 'cube': ('cubes',),
    'langflow': ('items',), 'crowdsec': None, 'dittofeed': ('segments',),
    'android-sms-gateway': None, 'sendportal': ('data',),
}
STATUS_FIELDS = {
    'crowdsec': ('type', frozenset(('ban', 'captcha', 'throttle'))),
}
SENDPORTAL_STATUS = {1: 'draft', 2: 'queued', 3: 'sending', 4: 'sent', 5: 'cancelled'}


def authorization(service, cfg, token):
    if service == 'label-studio':
        # Label Studio legacy access token: "Authorization: Token <key>".
        return {'Authorization': 'Token ' + token}
    if service in ('langflow', 'crowdsec'):
        return {'x-api-key' if service == 'langflow' else 'X-Api-Key': token}
    if service == 'clickhouse':
        user = cfg.get('username')
        if not isinstance(user, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', user):
            raise VerdugoError('ClickHouse requires a reviewed read-only username')
        return {'X-ClickHouse-User': user, 'X-ClickHouse-Key': token}
    if service == 'android-sms-gateway':
        user = cfg.get('username')
        if not isinstance(user, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', user):
            raise VerdugoError('Android SMS Gateway requires the reviewed local-server username')
        return {'Authorization': 'Basic ' + base64.b64encode((user + ':' + token).encode()).decode()}
    return {'Authorization': 'Bearer ' + token}


def check_origin(service, origin):
    expected = FIXED_ORIGINS.get(service)
    if expected is not None and origin != expected:
        raise VerdugoError('%s credentials may only be sent to %s' % (service, expected))


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS[service]:
        raise VerdugoError('Adapter/action not implemented: %s.%s' % (service, operation))
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1:
        raise VerdugoError('Only the first page is implemented for this provider')
    check_origin(service, origin)
    method, path = SPECS[service][operation]
    query = dict(QUERIES.get(service, {}))
    if service == 'clickhouse':
        query = {'query': CLICKHOUSE_QUERY}
    if service == 'dittofeed':
        workspace = cfg.get('workspace_id')
        if not isinstance(workspace, str) or not UUID.fullmatch(workspace):
            raise VerdugoError('Dittofeed requires a reviewed workspace_id (UUID)')
        query = {'workspaceId': workspace}
    from urllib.parse import urlencode
    url = origin + path + ('?' + urlencode(query) if query else '')
    from .common import digest
    public = {'service': service, 'operation': operation, 'method': method,
              'url': url, 'body': None, 'version': cfg.get('version'),
              'credential_binding': digest(headers),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token] + [v for k, v in headers.items()
                                        if k not in ('Accept', 'User-Agent', 'Content-Type')]}


def _rows(service, response):
    path = LIST_PATHS[service]
    rows = response
    for key in path or ():
        if not isinstance(rows, dict) or key not in rows:
            raise VerdugoError('Provider collection schema mismatch')
        rows = rows[key]
    if not isinstance(rows, list) or len(rows) > 1000 or not all(isinstance(r, dict) for r in rows):
        raise VerdugoError('Provider read requires a bounded list of objects')
    return rows


def check(service, operation, response, request=None):
    """Reduce the provider body to counts; raw payloads are never retained."""
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Provider read operation mismatch')
    base = {'service': service, 'operation': operation,
            'raw_provider_payload_retained': False,
            'scope': 'one_provider_response_not_a_complete_export',
            'live_verified': False}
    if service == 'clickhouse':
        data = response.get('data') if isinstance(response, dict) else None
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise VerdugoError('ClickHouse JSON result schema mismatch')
        value = data[0].get('databases')
        try:
            count = int(value) if isinstance(value, (int, str)) and not isinstance(value, bool) else None
        except ValueError:
            count = None
        if count is None or not 0 <= count <= 100000:
            raise VerdugoError('ClickHouse count schema mismatch')
        return base | {'databases': count}
    if service == 'crowdsec' and response is None:
        response = []  # Go encodes an empty decision slice as JSON null.
    rows = _rows(service, response)
    result = base | {'records_in_response': len(rows)}
    if service in STATUS_FIELDS:
        key, allowed = STATUS_FIELDS[service]
        counts = {}
        for row in rows:
            value = row.get(key)
            label = value if isinstance(value, str) and value in allowed else 'OTHER'
            counts[label] = counts.get(label, 0) + 1
        result['status_counts'] = counts
    if service == 'sendportal':
        counts = {}
        for row in rows:
            label = SENDPORTAL_STATUS.get(row.get('status_id'), 'OTHER') if type(row.get('status_id')) is int else 'OTHER'
            counts[label] = counts.get(label, 0) + 1
        result['status_counts'] = counts
    if service == 'android-sms-gateway':
        sims = sum(len(r['simCards']) for r in rows if isinstance(r.get('simCards'), list))
        result['sim_cards'] = sims
    if service == 'svix' and isinstance(response, dict):
        result['more_pages'] = response.get('done') is False
    return result
