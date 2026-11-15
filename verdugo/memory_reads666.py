"""Fixed self-hosted memory counters, without retrieval, ingestion or inference."""
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields

SPECS = {
    'memos': {'scheduler.summary': ('GET', '/product/scheduler/allstatus')},
    'lightrag': {'documents.summary': ('GET', '/documents/status_counts')},
}
PINNED_COMMITS = {
    'memos': '3a16e5fe3048a209f722806f4123fa2e533588fd',
    'lightrag': 'c515065405929202c4068e66230f1a19069196ff',
}
TASK_STATES = ('waiting', 'in_progress', 'pending', 'completed', 'failed', 'cancelled', 'total')
DOC_STATES = ('pending', 'parsing', 'analyzing', 'processing', 'preprocessed',
              'processed', 'failed', 'deleting')
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-memory-reads666.json'


def auth_policy(service, cfg):
    if service not in SPECS or cfg.get('api_surface') != 'self_hosted':
        raise VerdugoError('Only the reviewed self-hosted memory API is supported')
    if cfg.get('dedicated_instance_reviewed') is not True:
        raise VerdugoError('Review the dedicated company instance before reading counters')
    if service == 'memos':
        if (cfg.get('auth_mode') != 'reviewed_proxy_bearer'
                or cfg.get('proxy_auth_reviewed') is not True
                or cfg.get('proxy_strips_credentials_reviewed') is not True):
            raise VerdugoError('MemOS requires a reviewed authenticating proxy that strips credentials upstream')
        return {'mode': 'reviewed_proxy_bearer', 'upstream_native_auth': False,
                'operator_proxy_reviewed': True, 'proxy_strips_credentials_reviewed': True,
                'dedicated_instance_reviewed': True}
    if (cfg.get('auth_mode') != 'native_x_api_key'
            or cfg.get('native_auth_enforced_reviewed') is not True
            or cfg.get('status_storage') != 'JsonDocStatusStorage'
            or cfg.get('status_storage_reviewed') is not True):
        raise VerdugoError('LightRAG requires an API key, a protected route and reviewed JsonDocStatusStorage')
    return {'mode': 'native_x_api_key', 'upstream_native_auth': True,
            'native_auth_enforced_reviewed': True, 'dedicated_instance_reviewed': True,
            'status_storage': 'JsonDocStatusStorage', 'status_storage_reviewed': True}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    return {'X-API-Key': token} if service == 'lightrag' else {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unknown bounded memory observation')
    fields(params, ())
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    binding = hashlib.sha256(Path(__file__).read_bytes() + CONTRACT.read_bytes()).hexdigest()
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': None, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service],
              'implementation_binding': binding,
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, 'Bearer ' + token]}


def _bad():
    raise VerdugoError('Memory observation response schema mismatch')


def _counts(value, names, exact=False):
    if not isinstance(value, dict) or (exact and set(value) != set(names)):
        _bad()
    result = {}
    for name in names:
        count = value.get(name)
        if type(count) is not int or not 0 <= count <= 10**12:
            _bad()
        result[name] = count
    return result


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}) or not isinstance(response, dict):
        _bad()
    result = {'service': service, 'operation': operation,
              'raw_provider_payload_retained': False, 'live_verified': False,
              'production_certified': False, 'models_called': 0,
              'documents_ingested': 0, 'retrievals_executed': 0}
    if service == 'memos':
        if type(response.get('code')) is not int or response['code'] != 200:
            _bad()
        data = response.get('data')
        if not isinstance(data, dict):
            _bad()
        # pending can alias waiting; these two views are not disjoint populations.
        return result | {'scope': 'instance_scheduler_and_tracker_reported_counts',
                         'scheduler_summary': _counts(data.get('scheduler_summary'), TASK_STATES),
                         'all_tasks_summary': _counts(data.get('all_tasks_summary'), TASK_STATES),
                         'counts_are_disjoint': False, 'complete_history_verified': False}
    counts = _counts(response.get('status_counts'), DOC_STATES + ('all',), exact=True)
    if counts['all'] != sum(counts[name] for name in DOC_STATES):
        _bad()
    return result | {'scope': 'configured_instance_workspace_json_status_records',
                     'status_counts': counts, 'document_contents_verified': False}
