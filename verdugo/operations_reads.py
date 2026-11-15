"""Pinned batch-one reads: community, routing, storage and orchestration.

Only Apache Answer authenticates this route natively. The other three require
an explicitly reviewed Bearer proxy. A review flag does not install a proxy.
Dagster accepts exactly one static read query, never supplied GraphQL.
"""
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields, integer

SPECS = {
    'apache-answer': {'notifications.summary': ('GET', '/answer/api/v1/notification/status')},
    'caddy': {'http_servers.summary': ('GET', '/config/apps/http/servers')},
    'seaweedfs': {'topology.summary': ('GET', '/dir/status')},
    'dagster': {'repositories.summary': ('POST', '/graphql')},
}
PINNED_COMMITS = {
    'apache-answer': '6744295fa888e0621fc9f9a8ace04f1a4daf8554',
    'caddy': '7591cff1fb03202ce022982af020197f3f387220',
    'seaweedfs': 'e0890391acff2e8cac6dea79c28e931ab1dfb70e',
    'dagster': '93e5f51da49420d3e06d9399471070acedb554ca',
}
PROXY_ONLY = frozenset(('caddy', 'seaweedfs', 'dagster'))
READ_POSTS = frozenset((('dagster', 'repositories.summary'),))
DAGSTER_QUERY = ('query VerdugoRepositories { repositoriesOrError { __typename '
                 '... on RepositoryConnection { nodes { __typename } } } }')
MAX_ITEMS = 1000


def auth_policy(service, cfg):
    if service in PROXY_ONLY:
        if (cfg.get('auth_mode') != 'reviewed_proxy_bearer'
                or cfg.get('proxy_auth_reviewed') is not True):
            raise VerdugoError('Reviewed authenticating reverse proxy required: ' + service)
        return {'mode': 'reviewed_proxy_bearer', 'operator_proxy_reviewed': True,
                'upstream_native_auth': False}
    if service != 'apache-answer' or cfg.get('auth_mode') != 'native_user_bearer':
        raise VerdugoError('Apache Answer requires a native active-user bearer credential')
    return {'mode': 'native_user_bearer', 'upstream_native_auth': True}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    return {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Operation not implemented for this provider')
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1:
        raise VerdugoError('Only one bounded response is implemented')
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    body = {'query': DAGSTER_QUERY, 'operationName': 'VerdugoRepositories'} if service == 'dagster' else None
    if body is not None:
        headers = headers | {'Content-Type': 'application/json'}
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': body, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service],
              'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, headers['Authorization']]}


def _bad():
    raise VerdugoError('Operations provider response schema mismatch')


def _count(value, low=0):
    if type(value) is not int or not low <= value <= 10**12:
        _bad()
    return value


def _rows(value, nullable=False):
    if value is None and nullable:
        return []  # Go nil slices serialize to null; missing keys are checked by caller.
    if not isinstance(value, list) or len(value) > MAX_ITEMS or any(not isinstance(r, dict) for r in value):
        _bad()
    return value


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}) or not isinstance(response, dict):
        _bad()
    base = {'service': service, 'operation': operation,
            'scope': 'one_bounded_response_not_a_complete_export',
            'raw_provider_payload_retained': False, 'live_verified': False,
            'production_certified': False}
    if service == 'apache-answer':
        data = response.get('data')
        if type(response.get('code')) is not int or response['code'] != 200 or not isinstance(data, dict):
            _bad()
        if type(data.get('can_revision')) is not bool:
            _bad()
        return base | {'inbox_unread': _count(data.get('inbox')),
                       'achievements_unread': _count(data.get('achievement')),
                       'revisions_pending': _count(data.get('revision')),
                       'can_review_revisions': data['can_revision'],
                       'notifications_sent': False}
    if service == 'caddy':
        if len(response) > MAX_ITEMS:
            _bad()
        listeners, routes = 0, 0
        for name, server in response.items():
            if not isinstance(name, str) or not name.strip() or len(name) > 1000 or not isinstance(server, dict):
                _bad()
            addresses = server.get('listen', [])
            if (not isinstance(addresses, list) or len(addresses) > MAX_ITEMS
                    or any(not isinstance(a, str) or not a.strip() or len(a) > 4096 for a in addresses)):
                _bad()
            listeners += len(addresses)
            routes += len(_rows(server.get('routes', [])))
            if listeners > MAX_ITEMS or routes > MAX_ITEMS:
                _bad()
        return base | {'http_servers_in_response': len(response),
                       'listeners_in_response': listeners, 'routes_in_response': routes,
                       'traffic_serving_verified': False}
    if service == 'seaweedfs':
        top = response.get('Topology')
        if (not isinstance(response.get('Version'), str) or not response['Version'].strip()
                or len(response['Version']) > 256 or not isinstance(top, dict)
                or not {'Max', 'Free', 'DataCenters', 'Layouts'} <= top.keys()):
            _bad()
        # Max and Free are volume slots, NOT bytes or available customer storage.
        return base | {'volume_slots_max': _count(top['Max']),
                       'volume_slots_free': _count(top['Free'], low=-(10**12)),
                       'data_centers_in_response': len(_rows(top['DataCenters'], nullable=True)),
                       'layouts_in_response': len(_rows(top['Layouts'], nullable=True)),
                       'file_access_verified': False}
    if response.get('errors') not in (None, []):
        _bad()  # Partial GraphQL data never becomes a successful observation.
    data = response.get('data')
    repositories = data.get('repositoriesOrError') if isinstance(data, dict) else None
    if not isinstance(repositories, dict) or repositories.get('__typename') != 'RepositoryConnection':
        _bad()
    nodes = _rows(repositories.get('nodes'))
    if any(n.get('__typename') != 'Repository' for n in nodes):
        _bad()
    return base | {'repositories_in_response': len(nodes), 'jobs_executed': False}
