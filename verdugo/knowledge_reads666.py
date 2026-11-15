"""Original self-hosted knowledge inventories; only counts survive projection."""
import base64
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields

SPECS = {'jena': {'datasets.summary': ('GET', '/$/server')}, 'ragflow': {'datasets.summary': ('GET', '/api/v1/datasets?page=1&page_size=100')},
         'infinity': {'models.summary': ('GET', '/models')}}
PINNED_COMMITS = {'jena': 'd5b47b73e3e260bf1db62c776efb960bc758a93d', 'ragflow': 'f9a53a3779a12b5abb8a254ec9384c2af7fae4b4',
                  'infinity': 'f25b80850a7fc9736310496b64faf9903c01ac97'}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-knowledge-reads666.json'


def auth_policy(service, cfg):
    if service == 'jena':
        if cfg.get('api_surface') != 'self_hosted_fuseki_admin' or cfg.get('auth_mode') != 'native_basic':
            raise VerdugoError('Only the reviewed Fuseki admin Basic authentication surface is supported')
        gates = ('native_auth_enforced_reviewed', 'dedicated_instance_reviewed', 'status_route_basic_auth_reviewed')
        if any(cfg.get(gate) is not True for gate in gates):
            raise VerdugoError('Review Basic protection of the otherwise anonymous Fuseki status route')
        return {'mode':'native_basic', 'upstream_native_auth':True, **{gate:True for gate in gates}}
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
    if service == 'jena':
        username, separator, password = token.partition(':')
        if not separator or not username or not password:
            raise VerdugoError('Fuseki requires a username:password credential')
        return {'Authorization':'Basic '+base64.b64encode(token.encode('ascii')).decode('ascii')}
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
    if service == 'jena':
        return check_jena(operation, response)
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


def check_jena(operation, response):
    def bounded_text(value, size=4096, optional=False):
        return (optional and value is None) or (type(value) is str and len(value)<=size)
    if (operation != 'datasets.summary' or not isinstance(response,dict)
            or not bounded_text(response.get('version'),128)
            or not bounded_text(response.get('startDateTime'),128)
            or type(response.get('uptime')) is not int or not 0<=response['uptime']<=10**12
            or not isinstance(response.get('datasets'),list) or len(response['datasets'])>1000):
        raise VerdugoError('Fuseki server inventory schema mismatch')
    names=set(); active=services=endpoints=0
    for row in response['datasets']:
        if (not isinstance(row,dict) or not bounded_text(row.get('ds.name'))
                or not row['ds.name'] or row['ds.name'] in names
                or type(row.get('ds.state')) is not bool
                or not isinstance(row.get('ds.services'),list) or len(row['ds.services'])>128):
            raise VerdugoError('Fuseki dataset schema mismatch')
        names.add(row['ds.name']); active+=row['ds.state']
        services+=len(row['ds.services'])
        for item in row['ds.services']:
            if (not isinstance(item,dict) or 'srv.type' not in item or 'srv.description' not in item
                    or not bounded_text(item['srv.type'],optional=True)
                    or not bounded_text(item['srv.description'],optional=True)
                    or not isinstance(item.get('srv.endpoints'),list) or len(item['srv.endpoints'])>128
                    or any(not bounded_text(x,optional=True) for x in item['srv.endpoints'])):
                raise VerdugoError('Fuseki service schema mismatch')
            endpoints+=len(item['srv.endpoints'])
    return {'service':'jena','operation':operation,'scope':'dedicated_fuseki_admin_registry_snapshot',
            'datasets_in_response':len(names),'datasets_accepting_requests':active,
            'datasets_not_accepting_requests':len(names)-active,'services_described':services,
            'endpoints_described':endpoints,'dataset_contents_inspected':False,
            'sparql_queries_executed':0,'datasets_modified':0,'raw_provider_payload_retained':False,
            'live_verified':False,'production_certified':False}
