"""Observe one existing KAG task without submitting work or retaining its ID/result."""
import hashlib
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
import uuid

from .common import VerdugoError, digest, encode, fields

SPECS = {'kag': {'task.summary': ('POST', '/process')}}
READ_POSTS = frozenset({('kag', 'task.summary')})
PINNED_COMMITS = {'kag': 'fdab15b3929d2ee40dfcdd388f90233096a6afc9'}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-task-reads666.json'
GATES = ('proxy_auth_reviewed', 'proxy_strips_credentials_reviewed',
         'dedicated_instance_reviewed', 'task_scope_reviewed')


def auth_policy(service, cfg):
    if (service != 'kag' or cfg.get('api_surface') != 'self_hosted_solver_server'
            or cfg.get('auth_mode') != 'reviewed_proxy_bearer'
            or any(cfg.get(gate) is not True for gate in GATES)):
        raise VerdugoError('KAG requires a reviewed authenticating proxy and dedicated task scope')
    return {'mode': 'reviewed_proxy_bearer', 'upstream_native_auth': False,
            **{gate: True for gate in GATES}}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    return {'Authorization': 'Bearer ' + token}


def valid_task_id(value):
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return False
    return str(parsed) == value and parsed.version == 4 and parsed.variant == uuid.RFC_4122


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unknown bounded task observation')
    fields(params, ())
    policy = auth_policy(service, cfg)
    name = cfg.get('task_id_env')
    if not isinstance(name, str) or not re.fullmatch(r'VERDUGO_[A-Z0-9_]+', name):
        raise VerdugoError('Configure a private VERDUGO_* reference for the existing task ID')
    task_id = os.environ.get(name, '')
    if not valid_task_id(task_id):
        raise VerdugoError('The configured KAG task ID must be a canonical UUID4')
    headers = headers | {'Content-Type': 'application/json'}
    method, path = SPECS[service][operation]
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': None, 'version': cfg.get('version'),
              'task_binding': digest(task_id), 'query_command': 'query',
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service],
              'implementation_binding': hashlib.sha256(Path(__file__).read_bytes() + CONTRACT.read_bytes()).hexdigest(),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    # The task ID is kept out of public plans. It is compared with the response
    # before projection, which removes both the ID and the arbitrary result.
    return {'public': public, 'headers': headers, 'mutates': False,
            'private_task': {'task_id': task_id},
            'secret_values': [token, headers['Authorization']]}


def body_bytes(request):
    """One exact original query envelope, never a generic private-body override."""
    p = request['public']
    if ((p.get('service'), p.get('operation'), p.get('method')) != ('kag', 'task.summary', 'POST')
            or urlsplit(p.get('url', '')).path != '/process'
            or urlsplit(p.get('url', '')).query or urlsplit(p.get('url', '')).fragment
            or p.get('body') is not None
            or p.get('query_command') != 'query' or request.get('mutates') is not False):
        raise VerdugoError('Unsupported private task query')
    private = request.get('private_task')
    fields(private, ('task_id',))
    task_id = private['task_id']
    if not valid_task_id(task_id) or digest(task_id) != p.get('task_binding'):
        raise VerdugoError('Private task query binding mismatch')
    # Request.parse_in_string_to_task_req requires JSON inside a JSON string.
    # Only cmd=query is emitted; no query text, callbacks, model config or submit.
    task = {'req_id': task_id, 'cmd': 'query', 'app_id': 0, 'project_id': 0,
            'req': '{}', 'config': '{}'}
    return encode({'features': {'in_string': encode(task)}}).encode()


def check(service, operation, response, request=None):
    if (operation not in SPECS.get(service, {}) or not isinstance(response, dict)
            or not isinstance(request, dict) or request.get('query_command') != 'query'
            or not valid_task_id(response.get('task_id'))
            or digest(response['task_id']) != request.get('task_binding')
            or response.get('status') not in ('running', 'completed', 'failed')
            or 'result' not in response
            or (response['status'] == 'running' and response['result'] is not None)
            or (response['status'] == 'failed' and not isinstance(response['result'], str))):
        raise VerdugoError('KAG task response schema or identity mismatch')
    state = response['status']
    return {'service': service, 'operation': operation,
            'scope': 'one_configured_task_in_dedicated_solver_cache',
            'tasks_observed': 1, 'running_reported': int(state == 'running'),
            'completed_reported': int(state == 'completed'), 'failed_reported': int(state == 'failed'),
            'failed_may_mean_missing_or_expired': state == 'failed',
            'completion_verified': False, 'result_quality_verified': False,
            'tasks_submitted': 0, 'models_called': 0,
            'task_identifier_retained': False, 'raw_provider_payload_retained': False,
            'live_verified': False, 'production_certified': False}
