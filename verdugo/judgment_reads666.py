"""Fixed self-hosted evaluation observations; no inference or evaluator runs."""
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields

SPECS = {
    'tensorzero': {'inferences.summary': ('POST', '/v1/inferences/list_inferences')},
    'opik': {'projects.summary': ('GET', '/v1/private/projects?page=1&size=100')},
}
PINNED_COMMITS = {
    'tensorzero': '62eb8f63e8ec62018d70420dbf1a8c5d1c026315',
    'opik': '5ea60d2633a022f0ddb31d2ec81ef21810e0fe52',
}
READ_POSTS = frozenset({('tensorzero', 'inferences.summary')})
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-judgment-reads666.json'


def auth_policy(service, cfg):
    if service not in SPECS or cfg.get('api_surface') != 'self_hosted':
        raise VerdugoError('Only the reviewed self-hosted evaluation API is supported')
    if cfg.get('dedicated_instance_reviewed') is not True:
        raise VerdugoError('Review the dedicated company instance before reading observations')
    if service == 'tensorzero':
        if (cfg.get('auth_mode') != 'native_api_key_bearer'
                or cfg.get('native_auth_enforced_reviewed') is not True):
            raise VerdugoError('TensorZero native gateway authentication must be reviewed and enabled')
        return {'mode': 'native_api_key_bearer', 'upstream_native_auth': True,
                'dedicated_instance_reviewed': True}
    if (cfg.get('auth_mode') != 'reviewed_proxy_bearer'
            or cfg.get('proxy_auth_reviewed') is not True):
        raise VerdugoError('Opik self-hosted default workspace requires a reviewed authenticating proxy')
    return {'mode': 'reviewed_proxy_bearer', 'upstream_native_auth': False,
            'operator_proxy_reviewed': True, 'dedicated_instance_reviewed': True}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    headers = {'Authorization': 'Bearer ' + token}
    if service == 'opik':
        headers['Comet-Workspace'] = 'default'
    return headers


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unknown bounded evaluation observation')
    fields(params, ())
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    body = {'limit': 100, 'offset': 0} if service == 'tensorzero' else None
    if body is not None:
        headers = headers | {'Content-Type': 'application/json'}
    binding = hashlib.sha256(Path(__file__).read_bytes() + CONTRACT.read_bytes()).hexdigest()
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': body, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service],
              'implementation_binding': binding,
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, headers['Authorization']]}


def _bad():
    raise VerdugoError('Evaluation observation response schema mismatch')


def _rows(value):
    if not isinstance(value, list) or len(value) > 100 or any(not isinstance(r, dict) for r in value):
        _bad()
    return value


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}) or not isinstance(response, dict):
        _bad()
    result = {'service': service, 'operation': operation,
              'scope': 'first_100_records_not_a_complete_export',
              'raw_provider_payload_retained': False, 'live_verified': False,
              'production_certified': False, 'inferences_created': 0,
              'evaluations_executed': 0, 'models_called': 0}
    if service == 'tensorzero':
        rows = _rows(response.get('inferences'))
        counts = {'chat': 0, 'json': 0}
        for row in rows:
            kind = row.get('type')
            if type(kind) is not str or kind not in counts:
                _bad()
            counts[kind] += 1
        return result | {'inferences_in_response': len(rows), 'type_counts': counts,
                         'result_quality_evaluated': False}
    rows = _rows(response.get('content'))
    for name in ('page', 'size', 'total'):
        value = response.get(name)
        if type(value) is not int or not 0 <= value <= 10**12:
            _bad()
    if response['page'] != 1 or response['size'] != len(rows) or response['total'] < len(rows):
        _bad()
    return result | {'projects_in_response': len(rows),
                     'projects_total_reported': response['total'],
                     'more_reported': response['total'] > len(rows),
                     'traces_evaluated': False}
