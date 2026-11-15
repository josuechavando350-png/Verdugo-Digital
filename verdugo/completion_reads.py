"""Fixed read contracts verified against the remaining pinned upstream sources.

Text is accepted only for explicitly listed operations. Raw text and JSON are
projected before SQLite persistence. Proxy review flags do not create proxies.
"""
import base64
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import time

from .common import VerdugoError, digest, fields, identifier, integer, text

SPECS = {
    'openhands': {'health.summary': ('GET', '/health')},
    'anubis': {'health.summary': ('GET', '/healthz')},
    'postal': {'health.summary': ('GET', '/health')},
    'tusd': {'metrics.summary': ('GET', '/metrics')},
    'nlweb': {'health.summary': ('GET', '/health')},
    'openprospector': {'readiness.summary': ('GET', '/api/health')},
    'openseo': {'projects.summary': ('GET', '/api/projects')},
    'google-ads': {'accounts.summary': ('GET', '/v26/customers:listAccessibleCustomers')},
    'temporal': {'namespaces.summary': ('GET', '/api/v1/namespaces?pageSize=50')},
    'otel-collector': {'metrics.summary': ('GET', '/metrics')},
    'debezium': {'connector.summary': ('GET', '/connectors/{connector_id}/status')},
    'huginn': {'agents.summary': ('GET', '/agents.json?page=1')},
    'opengmb': {'actions.summary': ('GET', '/api/v1/actions')},
    'livekit': {'rooms.summary': ('POST', '/twirp/livekit.RoomService/ListRooms')},
    'webmention-io': {'mentions.summary': ('GET', '/api/mentions.jf2?per-page=50&page=0')},
    'datosmex': {'fix.latest': ('GET', '/SieAPIRest/service/v1/series/SF43718/datos/oportuno')},
    'mcp-gsc': {'sites.summary': ('GET', '/webmasters/v3/sites')},
    'praw': {'posts.summary': ('GET', '/r/{subreddit}/hot?limit=25&raw_json=1')},
    'python-podcastindex': {'index.summary': ('GET', '/api/1.0/stats/current')},
    'letta': {'health.summary': ('GET', '/healthz')},
    'krayin-crm': {'dashboard.summary': ('GET', '/admin/dashboard/stats?type=over-all')},
    'humanlayer': {'health.summary': ('GET', '/health')},
}
READ_POSTS = frozenset({('livekit', 'rooms.summary')})
PINS = {
    'openhands': '685eb42ded117ba0321aa8c3019e6677e5474317',
    'krayin-crm': 'ed6deebfcb8c616eaf352c893a10a6d8e666fc6e',
    'humanlayer': 'b7ad8e1d383ff0f5fbec7bdc30425e4a59d5f789',
    'anubis': 'f197f9a6235d255000c7b654ac478354a6e4bd02',
    'postal': 'd96eddbadeda600595d6247486f9ceb8e99cbc15',
    'tusd': 'cec39980890809a9e7202872ec32f736f3b4a3f5',
    'nlweb': 'b423f15d9aeaa023ce75993ac9deed2354597043',
    'openprospector': 'dad0e778ff4e1438b69574ff9cbb7663a3bda6e6',
    'openseo': '12b525400539f980668d088ff7154236a2376e88',
    'google-ads': 'f253b400dc5924b731fcb42dbcd99e485200581e',
    'temporal': '03ecd1d228d2b8d9d433da55785afc9aeeead918',
    'otel-collector': 'e366bb7fb49a67fd117332fff93795a0050744ff',
    'debezium': 'a4c282ea70d3f913df699464f3e42f9ddb7eb03e',
    'huginn': '639c050b2bf4e14ef9983012af99dfc1dc68b334',
    'livekit': '59753ba7d759621ffb256b8023ebf2ddf70ffa9a',
    'opengmb': '8f399472e9d484cfcad77eef33b0da341e469577',
    'webmention-io': '9183deed829c2399e6cd7f594ab8f1d84492e86b',
    'datosmex': '4179265209ca8345cc2de533f82612a6ca45314f',
    'mcp-gsc': '45291df024c7873b2042c83d7add70ced7bb621f',
    'praw': '4590cb5b0ad2f9afbab983d60d792fc3c74d1f45',
    'python-podcastindex': '63fdb84b76b5d65c99e9c92428af55cc51aff04e',
    'letta': '8816d3a8516893bfdc0fa14bfb1235226012e295',
}
AUTH_MODES = {sid: 'reviewed_proxy_bearer' for sid in SPECS}
AUTH_MODES.update({'anubis': 'native_metrics_basic', 'openseo': 'native_api_bearer',
                   'google-ads': 'native_oauth_developer_token',
                   'huginn': 'native_session_cookie', 'opengmb': 'native_api_bearer', 'livekit': 'native_roomlist_jwt',
                   'webmention-io': 'native_api_bearer', 'datosmex': 'native_bmx_token',
                   'mcp-gsc': 'native_oauth_bearer', 'praw': 'native_oauth_bearer',
                   'python-podcastindex': 'native_sha1_timestamp'})
AUTH_MODES['krayin-crm'] = 'native_session_cookie'
PROXY_ONLY = frozenset(sid for sid, mode in AUTH_MODES.items() if mode == 'reviewed_proxy_bearer')
TEXT_READS = frozenset((sid, next(iter(SPECS[sid]))) for sid in ('anubis', 'postal', 'tusd', 'otel-collector', 'letta'))


def auth_policy(service, cfg):
    if service == 'openhands' and cfg.get('api_surface') != 'openhands_agent_server_1_62':
        raise VerdugoError('Only the reviewed official OpenHands Agent Server API is supported')
    if service == 'krayin-crm' and cfg.get('admin_path') != 'admin':
        raise VerdugoError('Only the native default admin path is supported')
    if service == 'humanlayer' and cfg.get('api_surface') != 'riptide_api':
        raise VerdugoError('Only the pinned HumanLayer Riptide API is supported')
    if service == 'letta' and cfg.get('api_surface') != 'letta_code_app_server':
        raise VerdugoError('Only the current Letta Code App Server is supported')
    if cfg.get('auth_mode') != AUTH_MODES[service]:
        raise VerdugoError('Explicit completion-provider authentication mode required')
    if service in PROXY_ONLY and cfg.get('proxy_auth_reviewed') is not True:
        raise VerdugoError('A reviewed authenticating proxy is required')
    if service == 'anubis' and cfg.get('native_auth_enforced_reviewed') is not True:
        raise VerdugoError('Review native metrics Basic authentication enforcement')
    if service in ('google-ads', 'mcp-gsc', 'praw') and cfg.get('oauth_scope_reviewed') is not True:
        raise VerdugoError('Review OAuth account scope and developer access')
    if service == 'debezium' and cfg.get('debezium_connector_reviewed') is not True:
        raise VerdugoError('Review that the configured Kafka Connect connector is Debezium')
    if service == 'otel-collector' and cfg.get('default_metrics_names_reviewed') is not True:
        raise VerdugoError('Review default collector metrics names without type or unit suffixes')
    if service in ('huginn', 'krayin-crm', 'opengmb', 'livekit', 'webmention-io', 'datosmex', 'python-podcastindex') and cfg.get('account_scope_reviewed') is not True:
        raise VerdugoError('Review native provider account and read permissions')
    if service == 'praw' and cfg.get('free_api_access_reviewed') is not True:
        raise VerdugoError('Review approved Reddit API access, usage terms and zero-cost scope')
    return {'mode': AUTH_MODES[service], 'upstream_native_auth': service not in PROXY_ONLY}


def _second_secret(cfg, field='developer_token_env'):
    key = cfg.get(field)
    if not isinstance(key, str) or not re.fullmatch(r'VERDUGO_[A-Z0-9_]+', key):
        raise VerdugoError('A separate VERDUGO_* credential reference is required')
    value = os.environ.get(key, '')
    if not value or len(value) > 4096 or any(not 33 <= ord(c) <= 126 for c in value):
        raise VerdugoError('Missing or invalid secondary provider credential')
    return value


def authorization(service, cfg, token):
    auth_policy(service, cfg)
    if service == 'krayin-crm':
        name = cfg.get('session_cookie_name')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}', name):
            raise VerdugoError('One administrator-selected native session cookie name is required')
        if not re.fullmatch(r'[a-zA-Z0-9_+/%=.-]{1,8192}', token):
            raise VerdugoError('A single encoded native session cookie is required')
        return {'Cookie': name + '=' + token, 'Accept': 'application/json'}
    if service == 'datosmex':
        return {'Bmx-Token': token}
    if service == 'python-podcastindex':
        key, timestamp = _second_secret(cfg, 'api_key_env'), str(int(time.time()))
        return {'X-Auth-Key': key, 'X-Auth-Date': timestamp,
                'Authorization': hashlib.sha1((key + token + timestamp).encode()).hexdigest()}
    if service == 'huginn':
        if not re.fullmatch(r'[a-zA-Z0-9_+/%=.-]{1,8192}', token):
            raise VerdugoError('A single encoded Rails session cookie is required')
        return {'Cookie': '_rails_session=' + token}
    if service == 'livekit':
        key = _second_secret(cfg, 'api_key_env')
        encode = lambda value: base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).rstrip(b'=')
        now = int(time.time())
        unsigned = encode({'alg': 'HS256', 'typ': 'JWT'}) + b'.' + encode(
            {'iss': key, 'nbf': now - 5, 'exp': now + 60, 'video': {'roomList': True}})
        jwt = unsigned + b'.' + base64.urlsafe_b64encode(hmac.new(token.encode(), unsigned, hashlib.sha256).digest()).rstrip(b'=')
        return {'Authorization': 'Bearer ' + jwt.decode(), 'Content-Type': 'application/json'}
    if service == 'anubis':
        username = text(cfg.get('username'), 128)
        if ':' in username or any(ord(c) < 33 or ord(c) > 126 for c in username):
            raise VerdugoError('A bounded Basic authentication username is required')
        return {'Authorization': 'Basic ' + base64.b64encode((username + ':' + token).encode()).decode(),
                'Accept': 'text/plain'}
    if service == 'google-ads':
        return {'Authorization': 'Bearer ' + token, 'developer-token': _second_secret(cfg)}
    if service == 'openseo' and not token.startswith('oseo_'):
        raise VerdugoError('OpenSEO requires a native oseo_ credential')
    headers = {'Authorization': 'Bearer ' + token}
    if (service, next(iter(SPECS[service]))) in TEXT_READS:
        headers['Accept'] = 'text/plain'
    return headers


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unsupported completion read')
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1:
        raise VerdugoError('Only one bounded response is supported')
    if service == 'google-ads' and origin != 'https://googleads.googleapis.com':
        raise VerdugoError('Google Ads uses its fixed official origin')
    fixed = {'webmention-io': 'https://webmention.io', 'datosmex': 'https://www.banxico.org.mx',
             'mcp-gsc': 'https://www.googleapis.com', 'praw': 'https://oauth.reddit.com',
             'python-podcastindex': 'https://api.podcastindex.org'}
    if service in fixed and origin != fixed[service]:
        raise VerdugoError('The official provider origin is fixed')
    method, path = SPECS[service][operation]
    if service == 'debezium':
        path = path.format(connector_id=identifier(cfg.get('connector_id')))
    if service == 'praw':
        subreddit = cfg.get('subreddit')
        if not isinstance(subreddit, str) or not re.fullmatch('[A-Za-z0-9_]{3,21}', subreddit):
            raise VerdugoError('One administrator-configured subreddit is required')
        path = path.format(subreddit=subreddit)
    binding = digest(headers)
    if service == 'livekit':
        binding = digest({'api_key': _second_secret(cfg, 'api_key_env'), 'api_secret': token,
                          'video': {'roomList': True}, 'headers': {k: v for k, v in headers.items() if k != 'Authorization'}})
    if service == 'python-podcastindex':
        binding = digest({'api_key': _second_secret(cfg, 'api_key_env'), 'api_secret': token,
                          'headers': {k: v for k, v in headers.items() if k not in ('Authorization', 'X-Auth-Date')}})
    public = {'service': service, 'operation': operation, 'method': method, 'url': origin + path,
              'body': {} if service == 'livekit' else None, 'version': cfg.get('version'), 'credential_binding': binding,
              'authentication_policy': auth_policy(service, cfg), 'contract_source_commit': PINS[service],
              'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    secrets = [token] + [v for k, v in headers.items() if k in ('Authorization', 'Cookie')]
    if service == 'google-ads':
        secrets.append(headers['developer-token'])
    if service in ('livekit', 'python-podcastindex'):
        secrets.append(_second_secret(cfg, 'api_key_env'))
    return {'public': public, 'headers': headers, 'mutates': False, 'secret_values': secrets}


def _bad():
    raise VerdugoError('Completion provider response schema mismatch')


def decode_text(service, operation, raw, content_type):
    if (service, operation) not in TEXT_READS or content_type.split(';', 1)[0].strip().lower() != 'text/plain':
        _bad()
    try:
        value = raw.decode('utf-8')
    except UnicodeError:
        _bad()
    if len(value) > 262144 or '\x00' in value:
        _bad()
    return {'bounded_text': value}


def check(service, operation, response, request=None):
    if service == 'huginn':
        if not isinstance(response, list):
            _bad()
        response = {'agents': response}
    if operation not in SPECS.get(service, {}) or not isinstance(response, dict):
        _bad()
    result = {'service': service, 'operation': operation, 'raw_provider_payload_retained': False,
              'live_verified': False, 'production_certified': False, 'scope': 'one_bounded_response'}
    if service == 'krayin-crm':
        stats = response.get('statistics')
        if not isinstance(stats, dict) or not isinstance(response.get('date_range'), str):
            _bad()
        counts = {}
        for key in ('total_leads', 'total_quotations', 'total_persons', 'total_organizations'):
            row = stats.get(key)
            if not isinstance(row, dict) or type(row.get('current')) is not int or not 0 <= row['current'] <= 10**12:
                _bad()
            counts[key] = row['current']
        return result | {'reported_counts': counts, 'scope': 'native dashboard configured date range and signed-in user scope',
                         'paid_clients_verified': False, 'rest_api_extension_used': False}
    if service == 'openhands':
        if not isinstance(response, dict) or response.get('status') != 'ok':
            raise VerdugoError('Unexpected OpenHands Agent Server health response')
        return result | {'process_health_reported': True, 'agent_execution_verified': False,
                         'initialization_readiness_verified': False}
    if service == 'humanlayer':
        from datetime import datetime
        value = response.get('timestamp')
        if response.get('status') != 'ok' or not isinstance(value, str) or len(value) > 40:
            _bad()
        try:
            if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                _bad()
        except ValueError:
            _bad()
        return result | {'process_and_database_health_reported': True, 'agent_execution_verified': False}
    if service == 'mcp-gsc':
        rows = response.get('siteEntry', [])
        if not isinstance(rows, list) or len(rows) > 1000 or set(response) - {'siteEntry'}:
            _bad()
        permissions = {'siteOwner', 'siteFullUser', 'siteRestrictedUser', 'siteUnverifiedUser'}
        seen, levels = set(), {}
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get('siteUrl'), str) or not row['siteUrl']
                    or len(row['siteUrl']) > 2048 or row['siteUrl'] in seen or row.get('permissionLevel') not in permissions):
                _bad()
            seen.add(row['siteUrl']); key = row['permissionLevel']; levels[key] = levels.get(key, 0) + 1
        return result | {'sites_in_response': len(rows), 'permission_levels': levels,
                         'search_performance_measured': False, 'site_verification_performed': False}
    if service == 'praw':
        data = response.get('data')
        rows = data.get('children') if isinstance(data, dict) else None
        if response.get('kind') != 'Listing' or not isinstance(rows, list) or len(rows) > 25:
            _bad()
        seen, comments, score = set(), 0, 0
        for row in rows:
            post = row.get('data') if isinstance(row, dict) else None
            if (not isinstance(post, dict) or row.get('kind') != 't3' or not isinstance(post.get('id'), str)
                    or not re.fullmatch('[a-z0-9]{1,20}', post['id']) or post['id'] in seen
                    or type(post.get('num_comments')) is not int or not 0 <= post['num_comments'] <= 10**8
                    or type(post.get('score')) is not int or not -10**9 <= post['score'] <= 10**9):
                _bad()
            seen.add(post['id']); comments += post['num_comments']; score += post['score']
        after = data.get('after')
        if after is not None and not isinstance(after, str):
            _bad()
        return result | {'posts_in_response': len(rows), 'comments_reported': comments, 'score_sum_reported': score,
                         'has_more': bool(after), 'unique_people_measured': False, 'content_retained': False}
    if service == 'python-podcastindex':
        stats = response.get('stats')
        if response.get('status') != 'true' or not isinstance(stats, dict):
            _bad()
        fields = ('feedCountTotal', 'episodeCountTotal', 'feedsWithNewEpisodes30days')
        if any(type(stats.get(k)) is not int or not 0 <= stats[k] <= 10**12 for k in fields):
            _bad()
        return result | {'feeds_reported': stats[fields[0]], 'episodes_reported': stats[fields[1]],
                         'feeds_with_new_episodes_30_days_reported': stats[fields[2]],
                         'feed_content_downloaded': False}
    if service == 'webmention-io':
        rows, paging = response.get('children'), response.get('paging')
        if response.get('type') != 'feed' or not isinstance(rows, list) or len(rows) > 50 or not isinstance(paging, dict):
            _bad()
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or type(row.get('wm-id')) is not int or row['wm-id'] <= 0 or row['wm-id'] in seen:
                _bad()
            seen.add(row['wm-id'])
        if type(paging.get('page')) is not int or paging['page'] != 0 or type(paging.get('per-page')) is not int or paging['per-page'] != 50 or type(paging.get('total')) is not int or not len(rows) <= paging['total'] <= 10**12:
            _bad()
        return result | {'mentions_in_response': len(rows), 'total_reported': paging['total'],
                         'has_more': paging['total'] > len(rows), 'private_mentions_content_retained': False}
    if service == 'datosmex':
        from datetime import datetime
        sie = response.get('bmx')
        series = sie.get('series') if isinstance(sie, dict) else None
        if not isinstance(series, list) or len(series) != 1 or not isinstance(series[0], dict) or series[0].get('idSerie') != 'SF43718':
            _bad()
        rows = series[0].get('datos')
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            _bad()
        value, date = rows[0].get('dato'), rows[0].get('fecha')
        if not isinstance(date, str) or not re.fullmatch(r'\d{2}/\d{2}/\d{4}', date):
            _bad()
        try:
            date = datetime.strptime(date, '%d/%m/%Y').date().isoformat()
        except ValueError:
            _bad()
        if value in ('N/E', 'N/D'):
            value = None
        elif not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,4}(?:\.[0-9]{1,8})?', value):
            _bad()
        return result | {'series': 'SF43718', 'observation_date': date, 'mxn_per_usd_reported': value,
                         'value_available': value is not None, 'market_executable_quote': False}
    if service == 'huginn':
        rows = response.get('agents')
        if not isinstance(rows, list) or len(rows) > 1000:
            _bad()
        seen, disabled = set(), 0
        for row in rows:
            if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] <= 0 or row['id'] in seen or type(row.get('disabled')) is not bool:
                _bad()
            seen.add(row['id']); disabled += row['disabled']
        return result | {'agents_in_response': len(rows), 'disabled': disabled, 'enabled': len(rows) - disabled,
                         'complete_inventory': False, 'agents_executed': False}
    if service == 'opengmb':
        data = response.get('data')
        rows = data.get('actions') if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) > 1000:
            _bad()
        seen, reads = set(), 0
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get('name'), str) or not row['name'] or row['name'] in seen
                    or row.get('kind') not in ('read', 'write') or type(row.get('needsPerson')) is not bool):
                _bad()
            seen.add(row['name']); reads += row['kind'] == 'read'
        return result | {'advertised_actions': len(rows), 'advertised_read_actions': reads,
                         'advertised_write_actions': len(rows) - reads, 'permission_to_execute_verified': False,
                         'actions_executed': 0}
    if service == 'livekit':
        rows = response.get('rooms', [])
        if not isinstance(rows, list) or len(rows) > 1000 or set(response) - {'rooms'}:
            _bad()
        seen, participants = set(), 0
        for row in rows:
            count = row.get('numParticipants', row.get('num_participants', 0)) if isinstance(row, dict) else None
            if (not isinstance(row, dict) or not isinstance(row.get('sid'), str) or not row['sid'] or row['sid'] in seen
                    or ('numParticipants' in row and 'num_participants' in row)
                    or type(count) is not int or not 0 <= count <= 10**6):
                _bad()
            seen.add(row['sid']); participants += count
        return result | {'rooms_in_response': len(rows), 'participants_reported': participants,
                         'rooms_created': 0, 'media_recorded': False}
    if service in ('anubis', 'postal', 'letta'):
        # Anubis emits a single newline; Postal emits no newline.
        expected = {'anubis': 'OK\n', 'postal': 'OK', 'letta': 'ok\n'}[service]
        if response != {'bounded_text': expected}:
            _bad()
        return result | {'process_health_reported': True, 'end_to_end_delivery_verified': False}
    if service == 'otel-collector':
        value = response.get('bounded_text')
        if not isinstance(value, str):
            _bad()
        rows = [line for line in value.splitlines() if line.startswith('otelcol_process_uptime')]
        labels = r'(?:\{[a-zA-Z_][a-zA-Z_0-9]*="(?:[^"\\\n]|\\[\\"n])*"(?:,[a-zA-Z_][a-zA-Z_0-9]*="(?:[^"\\\n]|\\[\\"n])*")*\})?'
        if len(rows) != 1 or not re.fullmatch(r'otelcol_process_uptime' + labels + r' ([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)', rows[0]):
            _bad()
        uptime = float(rows[0].rsplit(' ', 1)[1])
        if not math.isfinite(uptime) or not 0 <= uptime <= 10**12:
            _bad()
        return result | {'uptime_seconds_reported': uptime, 'export_delivery_verified': False}
    if service == 'debezium':
        connector, tasks = response.get('connector'), response.get('tasks')
        valid_states = {'UNASSIGNED', 'RUNNING', 'PAUSED', 'FAILED', 'DESTROYED', 'RESTARTING', 'STOPPED'}
        if (not isinstance(response.get('name'), str) or not isinstance(connector, dict)
                or connector.get('state') not in valid_states or not isinstance(tasks, list) or len(tasks) > 1000):
            _bad()
        if request and request['url'].split('/connectors/', 1)[1].split('/', 1)[0] != response['name']:
            _bad()
        seen, counts = set(), {}
        for task in tasks:
            if not isinstance(task, dict) or type(task.get('id')) is not int or not 0 <= task['id'] <= 10**6 or task['id'] in seen or task.get('state') not in valid_states:
                _bad()
            seen.add(task['id']); counts[task['state']] = counts.get(task['state'], 0) + 1
        return result | {'connector_state': connector['state'], 'tasks_in_response': len(tasks),
                         'task_states': counts, 'cdc_records_delivered_verified': False}
    if service == 'temporal':
        rows = response.get('namespaces', [])
        if not isinstance(rows, list) or len(rows) > 50 or set(response) - {'namespaces', 'nextPageToken'}:
            _bad()
        seen = set()
        for row in rows:
            info = row.get('namespaceInfo') if isinstance(row, dict) else None
            if not isinstance(info, dict) or not isinstance(info.get('id'), str) or not info['id'] or info['id'] in seen or not isinstance(info.get('name'), str):
                _bad()
            seen.add(info['id'])
        token = response.get('nextPageToken', '')
        if not isinstance(token, str) or len(token) > 4096:
            _bad()
        return result | {'namespaces_in_response': len(rows), 'has_more': bool(token), 'workflow_execution_verified': False}
    if service == 'tusd':
        value = response.get('bounded_text')
        if not isinstance(value, str):
            _bad()
        # The selected gauge is unlabeled in upstream. Do not retain or aggregate
        # arbitrary Prometheus labels (which can include paths or identifiers).
        rows = [line for line in value.splitlines() if line.startswith('tusd_connections_open')]
        if len(rows) != 1 or not re.fullmatch(r'tusd_connections_open [0-9]+(?:\.0+)?(?:e\+?[0-9]+)?', rows[0]):
            _bad()
        number = float(rows[0].split()[1])
        if not math.isfinite(number) or not 0 <= number <= 10**9 or not number.is_integer():
            _bad()
        return result | {'open_connections_reported': int(number), 'uploads_complete_verified': False}
    if service == 'nlweb':
        uptime = response.get('uptime_seconds')
        if (response.get('status') != 'healthy' or type(uptime) not in (int, float)
                or not math.isfinite(uptime) or not 0 <= uptime <= 10**12
                or not isinstance(response.get('version'), str) or not isinstance(response.get('mode'), str)):
            _bad()
        return result | {'process_health_reported': True, 'uptime_seconds_reported': uptime,
                         'retrieval_or_llm_verified': False}
    if service == 'openprospector':
        count = response.get('configured_providers')
        if response.get('ok') is not True or type(response.get('queue_available')) is not bool or type(count) is not int or not 0 <= count <= 1000:
            _bad()
        return result | {'configured_providers': count, 'queue_configuration_present': response['queue_available'],
                         'provider_connectivity_verified': False, 'prospects_collected': 0}
    if service == 'openseo':
        rows = response.get('data')
        if response.get('ok') is not True or not isinstance(rows, list) or len(rows) > 1000:
            _bad()
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not re.fullmatch(r'[0-9a-fA-F-]{36}', row['id']) or row['id'] in seen:
                _bad()
            seen.add(row['id'])
        return result | {'projects_in_response': len(rows), 'api_key_last_used_updated_by_provider': True,
                         'seo_checks_executed': False}
    rows = response.get('resourceNames', [])
    # Protobuf JSON omits an empty repeated field, so {} is a valid zero result.
    if (not isinstance(rows, list) or len(rows) > 1000 or any(not isinstance(x, str) or not re.fullmatch(r'customers/[0-9]{1,20}', x) for x in rows)
            or len(set(rows)) != len(rows) or set(response) - {'resourceNames'}):
        _bad()
    return result | {'directly_accessible_accounts': len(rows), 'complete_account_hierarchy': False,
                     'campaigns_changed': False, 'advertising_spend_incurred': False}
