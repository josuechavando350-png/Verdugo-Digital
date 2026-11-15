"""v0.18: pinned, bounded GET contracts for two pending first-batch services.

Uptime Kuma uses the native bearer-key API (not legacy /metrics Basic auth).
Gotenberg /health skips upstream auth, so an explicitly reviewed authenticating
proxy is mandatory. No monitors, alerts, documents or server settings are changed.
Counts describe the returned snapshot only; they do not certify a deployment.
"""
import hashlib
from datetime import datetime
from pathlib import Path

from .common import VerdugoError, digest, fields, integer

SPECS = {
    'uptime-kuma': {'monitors.summary': ('GET', '/api/monitors')},
    'gotenberg': {'health.summary': ('GET', '/health')},
}
PINNED_COMMITS = {
    'uptime-kuma': '4f6661cfa83a06be0353d5536ef3d9ee0064f534',
    'gotenberg': '4d577e1467aaffa080b1e89d64ecb86c2fba4e98',
}
MAX_MONITORS = 1000
MAX_HEALTH_CHECKS = 32


def auth_policy(service, cfg):
    if service == 'uptime-kuma':
        if (cfg.get('auth_mode') != 'native_api_key_bearer'
                or cfg.get('api_access_reviewed') is not True):
            raise VerdugoError('Reviewed Uptime Kuma native API key and enabled API required')
        return {'mode': 'native_api_key_bearer', 'upstream_native_auth': True,
                'operator_api_access_reviewed': True}
    if service == 'gotenberg':
        if (cfg.get('auth_mode') != 'reviewed_proxy_bearer'
                or cfg.get('proxy_auth_reviewed') is not True):
            raise VerdugoError('Reviewed authenticating reverse proxy required: gotenberg')
        return {'mode': 'reviewed_proxy_bearer', 'upstream_native_auth': False,
                'operator_proxy_reviewed': True}
    raise VerdugoError('Unknown readiness provider')


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    return {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Adapter/action not implemented: %s.%s' % (service, operation))
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1:
        raise VerdugoError('Only one bounded response is implemented')
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': None, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service],
              'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, headers['Authorization']]}


def _bad():
    # Do not include any raw response values (names, hosts, errors or credentials).
    raise VerdugoError('Readiness provider response schema mismatch')


def _string(value, limit=128):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}) or not isinstance(response, dict):
        _bad()
    result = {'service': service, 'operation': operation,
              'scope': 'one_bounded_response_not_a_complete_export',
              'raw_provider_payload_retained': False,
              'live_verified': False, 'production_certified': False}
    if service == 'uptime-kuma':
        rows = response.get('monitors')
        if (response.get('ok') is not True or not isinstance(rows, list)
                or len(rows) > MAX_MONITORS):
            _bad()
        seen, enabled = set(), 0
        for row in rows:
            if not isinstance(row, dict):
                _bad()
            sid, active = row.get('id'), row.get('active')
            if (type(sid) is not int or not 1 <= sid <= 9007199254740991 or sid in seen
                    or type(active) is not bool or not _string(row.get('type'))
                    or not _string(row.get('name'), 1000)):
                _bad()
            seen.add(sid)
            enabled += int(active)
        # `active` means enabled monitoring; it says NOTHING about the target's UP/DOWN state.
        return result | {'monitors_in_response': len(rows), 'enabled_monitors': enabled,
                         'paused_monitors': len(rows) - enabled,
                         'target_availability_verified': False}
    # Gotenberg's health dependency returns 503 for down, which transport rejects.
    # A successful HTTP 200 must have an internally consistent up report.
    details = response.get('details')
    if (response.get('status') != 'up' or not isinstance(details, dict)
            or len(details) > MAX_HEALTH_CHECKS):
        _bad()
    for name, row in details.items():
        if (not _string(name) or not isinstance(row, dict) or row.get('status') != 'up'
                or row.get('error') not in (None, '')):
            _bad()
        stamp = row.get('timestamp')
        if not isinstance(stamp, str) or len(stamp) > 64:
            _bad()
        try:
            value = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if value.tzinfo is None:
                _bad()
        except (ValueError, TypeError):
            _bad()
    return result | {'reported_status': 'up', 'dependency_checks_in_response': len(details),
                     'document_conversion_verified': False}
