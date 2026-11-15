"""Original self-hosted knowledge inventories; only counts survive projection."""
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields

SPECS = {'ragflow': {'datasets.summary': ('GET', '/api/v1/datasets?page=1&page_size=100')},
         'infinity': {'models.summary': ('GET', '/models')}}
PINNED_COMMITS = {'ragflow': 'f9a53a3779a12b5abb8a254ec9384c2af7fae4b4',
                  'infinity': 'f25b80850a7fc9736310496b64faf9903c01ac97'}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-knowledge-reads666.json'


def auth_policy(service, cfg):
    surface = 'self_hosted_community' if service == 'ragflow' else 'self_hosted_python_v2'
    if (service not in SPECS or cfg.get('api_surface') != surface
            or cfg.get('auth_mode') != 'native_api_key_bearer'):
        raise VerdugoError('Only the reviewed original self-hosted API is supported')
    gates = ('native_auth_enforced_reviewed', 'dedicated_instance_reviewed')
    if service == 'ragflow': gates += ('community_build_reviewed',)
    for gate in gates:
        if cfg.get(gate) is not True:
            raise VerdugoError('Review the required native authentication and dedicated instance safeguards')
    return {'mode': 'native_api_key_bearer', 'upstream_native_auth': True,
            **{gate: True for gate in gates}}


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    return {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unknown bounded knowledge observation')
    fields(params, ())
    policy = auth_policy(service, cfg)
    method, path = SPECS[service][operation]
    binding = hashlib.sha256(Path(__file__).read_bytes() + CONTRACT.read_bytes()).hexdigest()
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path, 'body': None, 'version': cfg.get('version'),
              'credential_binding': digest(headers), 'authentication_policy': policy,
              'contract_source_commit': PINNED_COMMITS[service], 'implementation_binding': binding,
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False,
            'secret_values': [token, headers['Authorization']]}


def check(service, operation, response, request=None):
    if service == 'infinity':
        if (operation not in SPECS[service] or not isinstance(response, dict)
                or response.get('object') != 'list' or not isinstance(response.get('data'), list)
                or len(response['data']) > 1000):
            raise VerdugoError('Infinity model inventory schema mismatch')
        for row in response['data']:
            if (not isinstance(row, dict) or type(row.get('id')) is not str or len(row['id']) > 1024
                    or row.get('object') != 'model' or row.get('owned_by') != 'infinity'
                    or not isinstance(row.get('stats'), dict)):
                raise VerdugoError('Infinity model inventory schema mismatch')
        return {'service': service, 'operation': operation, 'scope': 'dedicated_instance_python_v2_root_models',
                'models_in_response': len(response['data']), 'model_quality_verified': False,
                'raw_provider_payload_retained': False, 'models_called': 0,
                'model_weights_downloaded': 0, 'embeddings_created': 0, 'rerankings_executed': 0,
                'live_verified': False, 'production_certified': False}
    if (operation not in SPECS.get(service, {}) or not isinstance(response, dict)
            or type(response.get('code')) is not int or response['code'] != 0):
        raise VerdugoError('RAGFlow inventory response schema mismatch')
    rows, total = response.get('data'), response.get('total_datasets')
    if (not isinstance(rows, list) or len(rows) > 100
            or type(total) is not int or not len(rows) <= total <= 10**12
            or any(not isinstance(r, dict) or type(r.get('id')) is not str
                   or not 1 <= len(r['id']) <= 128 or type(r.get('name')) is not str
                   or len(r['name']) > 4096 for r in rows)):
        raise VerdugoError('RAGFlow inventory response schema mismatch')
    return {'service': service, 'operation': operation,
            'scope': 'first_100_visible_datasets_for_fixed_credential_identity',
            'datasets_in_response': len(rows), 'datasets_total_reported': total,
            'more_reported': total > len(rows), 'complete_export_verified': False,
            'raw_provider_payload_retained': False, 'models_called': 0,
            'documents_ingested': 0, 'retrievals_executed': 0,
            'live_verified': False, 'production_certified': False}
