"""v0.17: four bounded reads continuing Claude's first connection batch.

Contracts were inspected at the exact commits in PINNED_COMMITS (not latest).
Three upstream routes have no native authentication: require an operator-reviewed
Bearer reverse proxy; a configured flag is NOT evidence that a proxy exists.
Only Fides authenticates natively. No browsing, inference, project edits, privacy
requests, deletion, or messaging is performed. Results contain counts only.
"""
import hashlib
from pathlib import Path
import re
from urllib.parse import urlencode

from .common import VerdugoError, digest, fields, integer

SPECS = {
    'openrefine': {'projects.count': ('GET', '/command/core/get-all-project-metadata')},
    'steel-browser': {'sessions.summary': ('GET', '/v1/sessions')},
    'crawl4ai': {'hooks.summary': ('GET', '/hooks/info')},
    'fides': {'policies.count': ('GET', '/api/v1/dsr/policy')},
}
PINNED_COMMITS = {
    'openrefine': 'd97abdabd4c172ddba3581a9259307c7f2b86b44',
    'steel-browser': '552550af79742a75fef24c24b1134e43e99e3d5e',
    'crawl4ai': 'cae74b203a33994f7e13b9052c3b0d5c93daa0e6',
    'fides': 'e87f3ff835af368defc1ec42dc29ec545a288585',
}
PROXY_ONLY = frozenset(('openrefine', 'steel-browser', 'crawl4ai'))
SESSION_STATES = frozenset(('idle', 'live', 'released', 'failed'))
UUID = re.compile(r'^[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$')
MAX_ITEMS = 1000


def auth_policy(service, cfg):
    if service not in SPECS:
        raise VerdugoError('Unknown batch-one provider')
    if service in PROXY_ONLY:
        if (cfg.get('auth_mode') != 'reviewed_proxy_bearer'
                or cfg.get('proxy_auth_reviewed') is not True):
            raise VerdugoError('Reviewed authenticating reverse proxy required: ' + service)
        return {'mode': 'reviewed_proxy_bearer', 'operator_proxy_reviewed': True,
                'upstream_native_auth': False}
    if cfg.get('auth_mode') != 'native_oauth_bearer':
        raise VerdugoError('Fides requires a reviewed native OAuth bearer token')
    return {'mode': 'native_oauth_bearer', 'upstream_native_auth': True}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    return {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Adapter/action not implemented: %s.%s' % (service, operation))
    # Page is accepted only as explicit 1 for compatibility with other reads.
    # No URL, method, query, tenant or credential can enter through parameters.
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1:
        raise VerdugoError('Only the first response/page is implemented')
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    query = {'page': 1, 'size': 50} if service == 'fides' else {}
    url = origin + path + ('?' + urlencode(query) if query else '')
    public = {'service': service, 'operation': operation, 'method': method,
              'url': url, 'body': None, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service],
              'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, headers['Authorization']]}


def _bad():
    raise VerdugoError('Batch-one provider response schema mismatch')


def _objects(value, limit=MAX_ITEMS):
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(r, dict) for r in value):
        _bad()
    return value


def _mapping(value):
    if not isinstance(value, dict) or len(value) > MAX_ITEMS:
        _bad()
    return value


def check(service, operation, response, request=None):
    """Discard raw payloads before persistence, including arbitrary errors/labels."""
    if operation not in SPECS.get(service, {}) or not isinstance(response, dict):
        _bad()
    result = {'service': service, 'operation': operation,
              'raw_provider_payload_retained': False,
              'scope': 'one_bounded_response_not_a_complete_export',
              'live_verified': False, 'production_certified': False}
    if service == 'openrefine':
        projects = _mapping(response.get('projects'))
        for key, metadata in projects.items():
            if (not isinstance(key, str) or not re.fullmatch(r'[1-9][0-9]{0,18}', key)
                    or int(key) > 9223372036854775807 or not isinstance(metadata, dict)):
                _bad()
        return result | {'projects_in_response': len(projects)}
    if service == 'steel-browser':
        sessions = _objects(response.get('sessions'))
        counts = {state: 0 for state in sorted(SESSION_STATES)}
        seen = set()
        for row in sessions:
            sid, state = row.get('id'), row.get('status')
            if (not isinstance(sid, str) or not UUID.fullmatch(sid)
                    or sid.lower() in seen or not isinstance(state, str) or state not in SESSION_STATES):
                _bad()
            seen.add(sid.lower())
            counts[state] += 1
        return result | {'sessions_in_response': len(sessions), 'status_counts': counts}
    if service == 'crawl4ai':
        actions = _mapping(response.get('available_actions'))
        for action, value in actions.items():
            if (not isinstance(action, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', action)
                    or not isinstance(value, dict) or not isinstance(value.get('hook_point'), str)
                    or not value['hook_point'] or not isinstance(value.get('description'), str)
                    or not isinstance(value.get('params_schema'), dict)):
                _bad()
        usage, limits = response.get('usage'), response.get('timeout_limits')
        if not isinstance(usage, dict) or usage.get('field') != 'hooks' or not isinstance(limits, dict):
            _bad()
        max_hooks = usage.get('max_hooks')
        low, default, high = (limits.get(k) for k in ('min', 'default', 'max'))
        if (type(max_hooks) is not int or not 1 <= max_hooks <= 1000
                or any(type(v) is not int for v in (low, default, high))
                or not 1 <= low <= default <= high <= 3600):
            _bad()
        return result | {'actions_available': len(actions), 'max_hooks_per_request': max_hooks,
                         'crawl_executed': False}
    # Native Fides pagination: fixed page=1,size=50; no follow of returned links.
    policies = _objects(response.get('items'), limit=50)
    total, page, size = (response.get(k) for k in ('total', 'page', 'size'))
    if (type(total) is not int or not len(policies) <= total <= 10**9
            or type(page) is not int or page != 1 or type(size) is not int or size != 50
            or len(policies) != min(total, size)):
        _bad()
    if any(not isinstance(p.get('name'), str) or not p['name'].strip() for p in policies):
        _bad()
    return result | {'policies_in_response': len(policies), 'more_pages': total > len(policies)}
