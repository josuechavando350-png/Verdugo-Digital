"""Fixed self-hosted index inventories; no embedding, retrieval or vector writes."""
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields

SPECS = {
    'kernel-memory': {'indexes.summary': ('GET', '/indexes')},
    'chroma': {'collections.summary': ('GET', '/api/v2/tenants/default_tenant/databases/default_database/collections_count')},
    'milvus': {'collections.summary': ('POST', '/v2/vectordb/collections/list')},
}
PINNED_COMMITS = {
    'kernel-memory': '8fc4e16f31257faa34c5e368f8e99b45df7e4049',
    'chroma': '1a3ac2c7c623adbd03ed2508dc27b98cdf26016d',
    'milvus': 'efb4bc44e460c4fac2c196a6842cf5537f2e714d',
}
READ_POSTS = frozenset({('milvus', 'collections.summary')})
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-vector-reads666.json'


def auth_policy(service, cfg):
    if service not in SPECS or cfg.get('api_surface') != 'self_hosted':
        raise VerdugoError('Only the reviewed self-hosted index API is supported')
    if cfg.get('dedicated_instance_reviewed') is not True:
        raise VerdugoError('Review the dedicated company instance before reading inventories')
    mode = {'kernel-memory': 'native_authorization_key', 'chroma': 'reviewed_proxy_bearer',
            'milvus': 'native_bearer'}[service]
    gate = 'proxy_auth_reviewed' if service == 'chroma' else 'native_auth_enforced_reviewed'
    if cfg.get('auth_mode') != mode or cfg.get(gate) is not True:
        raise VerdugoError('Review and enable the required inventory authentication')
    return {'mode': mode, 'upstream_native_auth': service != 'chroma',
            gate: True, 'dedicated_instance_reviewed': True}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    if service == 'kernel-memory':
        valid = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.;:_-!@#$^*~=|[]{}()')
        if len(token) < 32 or any(c not in valid for c in token):
            raise VerdugoError('Kernel Memory requires an original-format key of at least 32 characters')
        return {'Authorization': token}
    return {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unknown bounded index observation')
    fields(params, ())
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    body = {'dbName': 'default'} if service == 'milvus' else None
    if body is not None:
        headers = headers | {'Content-Type': 'application/json'}
    binding = hashlib.sha256(Path(__file__).read_bytes() + CONTRACT.read_bytes()).hexdigest()
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': body, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service], 'implementation_binding': binding,
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, headers['Authorization']]}


def _bad():
    raise VerdugoError('Index observation response schema mismatch')


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}):
        _bad()
    result = {'service': service, 'operation': operation,
              'raw_provider_payload_retained': False, 'live_verified': False,
              'production_certified': False, 'models_called': 0,
              'vectors_written': 0, 'retrievals_executed': 0,
              'index_contents_verified': False}
    if service == 'chroma':
        if type(response) is not int or not 0 <= response <= 2**32 - 1:
            _bad()
        return result | {'scope': 'dedicated_instance_default_tenant_default_database',
                         'collections_reported': response}
    if not isinstance(response, dict):
        _bad()
    if service == 'kernel-memory':
        rows = response.get('results')
        if (not isinstance(rows, list) or len(rows) > 1000
                or any(not isinstance(r, dict) or type(r.get('name')) is not str
                       or len(r['name']) > 1024 for r in rows)):
            _bad()
        return result | {'scope': 'dedicated_instance_visible_indexes', 'indexes_in_response': len(rows)}
    if type(response.get('code')) is not int or response['code'] != 0:
        _bad()
    names = response.get('data')
    if (not isinstance(names, list) or len(names) > 1000
            or any(type(name) is not str or not 1 <= len(name) <= 1024 for name in names)):
        _bad()
    return result | {'scope': 'dedicated_instance_default_database_visible_collections',
                     'collections_in_response': len(names)}
