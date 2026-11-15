"""Nine pinned reads, reduced to counts before persistence.

Jitsu and Kill Bill require an operator-reviewed authenticating proxy. Kill
Bill's proxy must also bind its native user and tenant credentials. No proxy,
account, sandbox, model inference, billing change or dataset export is created.
"""
import hashlib
from pathlib import Path
import re
from urllib.parse import urlencode

from .common import VerdugoError, fields, integer, identifier, digest

SPECS = {
    'datahub': {'datasets.count': ('GET', '/openapi/v1/entities/dataset/count')},
    'jitsu': {'ingest.configuration': ('GET', '/health')},
    'magentic-ui': {'sessions.summary': ('GET', '/api/sessions/')},
    'operately': {'companies.summary': ('GET', '/api/external/v1/companies/list')},
    'signoz': {'dashboards.summary': ('GET', '/api/v2/dashboards')},
    'bifrost': {'providers.summary': ('GET', '/api/providers')},
    'killbill': {'accounts.summary': ('GET', '/1.0/kb/accounts/pagination')},
    'taguette': {'annotations.summary': ('GET', '/api/project/{project_id}/document/{document_id}')},
    'ckanapi': {'packages.count': ('GET', '/api/action/package_search')},
}
PINNED_COMMITS = {
    'datahub': '164ce58a867afb6ee6ceac64c1c7aa9b526c1841', 'jitsu': '6c0d189a55c9e6c7b47d024d046e091ff1636565',
    'magentic-ui': 'd3c9d13c39288257286a66daabf7c5b5fb72ee69', 'operately': '9fa8692fb61cec13730fb4523daf57c29261be45',
    'signoz': 'ca7daf8ea974b879379101c7f7d8cb420da6acc7', 'bifrost': 'ff2e69f7f0143ab79c9de5258b90bd9c70cf347b',
    'killbill': '52e2f55f103baf0703ddee71e10a7036595fc851', 'taguette': '52fcdce95709375a4085cb10852bf7dd251ccb3d',
    'ckanapi': '94b8c24a21a185c270a01bcbcfa72ff4e1b78b1c',
}
AUTH_MODES = {'datahub': 'native_bearer', 'jitsu': 'reviewed_proxy_bearer',
    'magentic-ui': 'native_session_bearer', 'operately': 'native_api_bearer', 'signoz': 'native_api_key',
    'bifrost': 'native_management_bearer', 'killbill': 'reviewed_proxy_bearer',
    'taguette': 'native_signed_cookie', 'ckanapi': 'native_api_key'}
PROXY_ONLY = frozenset(('jitsu', 'killbill'))


def auth_policy(service, cfg):
    if cfg.get('auth_mode') != AUTH_MODES[service]: raise VerdugoError('Explicit provider authentication mode required')
    if service in PROXY_ONLY and cfg.get('proxy_auth_reviewed') is not True:
        raise VerdugoError('An authenticating proxy must be reviewed')
    if service == 'killbill' and cfg.get('proxy_tenant_binding_reviewed') is not True:
        raise VerdugoError('Kill Bill proxy native-user and tenant binding must be reviewed')
    if service in ('datahub', 'bifrost') and cfg.get('native_auth_enforced_reviewed') is not True:
        raise VerdugoError('Provider authentication enforcement must be reviewed')
    return {'mode': AUTH_MODES[service], 'upstream_native_auth': service not in PROXY_ONLY}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    if service == 'signoz': return {'SIGNOZ-API-KEY': token}
    if service == 'ckanapi': return {'X-CKAN-API-Key': token, 'Authorization': token}
    if service == 'taguette':
        if not re.fullmatch(r'[A-Za-z0-9_=:|+/-]{8,4096}', token): raise VerdugoError('Unquoted native signed cookie value required')
        return {'Cookie': 'user='+token}
    return {'Authorization': 'Bearer '+token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}): raise VerdugoError('Unsupported platform read')
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1: raise VerdugoError('Only a bounded first response is supported')
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    query = {}
    if service == 'magentic-ui':
        user = identifier(cfg.get('user_id'))
        if cfg.get('user_scope_reviewed') is not True: raise VerdugoError('Fixed session user scope must be reviewed')
        query = {'user_id': user}
    elif service == 'taguette':
        path = path.format(project_id=integer(cfg.get('project_id'), 1, 10**9), document_id=integer(cfg.get('document_id'), 1, 10**9))
    elif service == 'signoz': query = {'limit': 50, 'offset': 0}
    elif service == 'killbill': query = {'offset': 0, 'limit': 50}
    elif service == 'ckanapi': query = {'q': '*:*', 'rows': 0}
    public = {'service': service, 'operation': operation, 'method': method,
        'url': origin+path+('?' + urlencode(query) if query else ''), 'body': None,
        'version': cfg.get('version'), 'credential_binding': digest(headers), 'authentication_policy': policy,
        'contract_source_commit': PINNED_COMMITS[service],
        'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'network_policy': {'private': cfg.get('allow_private_network') is True, 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, *[v for k, v in headers.items() if k in ('Authorization', 'Cookie', 'X-CKAN-API-Key', 'SIGNOZ-API-KEY')]]}


def _bad(): raise VerdugoError('Platform response schema mismatch')


def _count(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 10**12: _bad()
    return value


def _rows(value, limit=1000):
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(r, dict) for r in value): _bad()
    return value


def _identifiers(rows, key, numeric=False):
    seen = set()
    for row in rows:
        value = row.get(key)
        if numeric: _count(value, 1)
        elif not isinstance(value, str) or not value.strip() or len(value) > 256: _bad()
        if value in seen: _bad()
        seen.add(value)


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}): _bad()
    base = {'service': service, 'operation': operation, 'scope': 'one_bounded_response_not_a_complete_export',
            'raw_provider_payload_retained': False, 'live_verified': False, 'production_certified': False}
    if service == 'killbill':
        rows = _rows(response, 50); _identifiers(rows, 'accountId')
        return base | {'accounts_in_response': len(rows), 'billing_changed': False, 'balances_read': False}
    if not isinstance(response, dict): _bad()
    if service == 'datahub':
        if response.get('entityType') != 'dataset' or response.get('keyAspect') != 'datasetKey' or type(response.get('cacheHit')) is not bool: _bad()
        _count(response.get('computedAtMillis'))
        return base | {'active_datasets': _count(response.get('activeCount')), 'soft_deleted_datasets': _count(response.get('softDeletedCount')),
                       'cached_count': response['cacheHit'], 'dataset_content_read': False}
    if service == 'jitsu':
        if response.get('status') != 'pass': _bad()
        return base | {'kafka_configuration_present': True, 'dependency_connectivity_verified': False, 'events_delivered_verified': False}
    if service == 'magentic-ui':
        if response.get('status') is not True: _bad()
        rows = _rows(response.get('data')); _identifiers(rows, 'session_id', True)
        for row in rows:
            if 'latest_run' not in row: _bad()
            if row['latest_run'] is not None:
                if not isinstance(row['latest_run'], dict): _bad()
                _count(row['latest_run'].get('run_id'), 1)
        return base | {'sessions_in_response': len(rows), 'sessions_with_latest_run': sum(r['latest_run'] is not None for r in rows), 'agents_started': 0}
    if service == 'operately':
        rows = _rows(response.get('companies')); _identifiers(rows, 'id')
        if any(type(r.get('setup_completed')) is not bool for r in rows): _bad()
        return base | {'companies_in_response': len(rows), 'setup_completed_in_response': sum(r['setup_completed'] for r in rows), 'api_key_last_used_updated_by_provider': True}
    if service == 'signoz':
        if response.get('status') != 'success' or not isinstance(response.get('data'), dict): _bad()
        data = response['data']; rows = _rows(data.get('dashboards'), 50)
        for row in rows:
            if any(type(row.get(key)) is not bool for key in ('locked', 'legacy')): _bad()
        total = _count(data.get('total'))
        if total < len(rows): _bad()
        return base | {'dashboards_in_response': len(rows), 'matching_dashboards_reported': total,
                       'locked_in_response': sum(r['locked'] for r in rows), 'telemetry_queries_executed': False}
    if service == 'bifrost':
        rows = _rows(response.get('providers')); _identifiers(rows, 'name')
        total = _count(response.get('total'))
        if total != len(rows): _bad()
        return base | {'configured_providers_in_response': len(rows), 'inference_calls_made': 0, 'provider_availability_verified': False}
    if service == 'taguette':
        if response.get('text_direction') not in ('LEFT_TO_RIGHT', 'RIGHT_TO_LEFT'): _bad()
        rows = _rows(response.get('highlights')); _identifiers(rows, 'id', True)
        assignments = 0
        for row in rows:
            start, end = _count(row.get('start_offset')), _count(row.get('end_offset'))
            if end < start or not isinstance(row.get('tags'), list) or len(row['tags']) > 1000: _bad()
            for tag in row['tags']: _count(tag, 1)
            if len(set(row['tags'])) != len(row['tags']): _bad()
            assignments += len(row['tags'])
            if assignments > 10000: _bad()
        return base | {'highlights_in_response': len(rows), 'tag_assignments_in_response': assignments, 'document_text_read': False}
    if response.get('success') is not True or not isinstance(response.get('result'), dict): _bad()
    result = response['result']
    if result.get('results') != []: _bad()
    return base | {'matching_packages_reported': _count(result.get('count')), 'package_records_requested': 0, 'resources_downloaded': 0}
