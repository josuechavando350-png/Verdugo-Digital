"""Six fixed marketing read contracts; no publishing, SQL or arbitrary GraphQL.

POST is permitted only for the three code-owned read operations below. Secrets
never enter the public plan. Vendor payloads are reduced before persistence.
"""
import base64
from datetime import date, datetime
import hashlib
import hmac
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode

from .common import VerdugoError, digest, encode, fields, integer

SPECS = {
    'postiz': {'channels.list': ('GET', '/public/v1/integrations')},
    'payload': {'documents.list': ('GET', '/api/{content_collection}')},
    'ghost': {'posts.list': ('GET', '/ghost/api/admin/posts/')},
    'plausible': {'traffic.summary': ('POST', '/api/v2/query')},
    'matomo': {'visits.summary': ('POST', '/index.php')},
    'saleor': {'products.list': ('POST', '/graphql/')},
}
READ_POSTS = frozenset((sid, op) for sid, ops in SPECS.items()
                       for op, (method, _) in ops.items() if method == 'POST')
METRICS = ['visitors', 'visits', 'pageviews']
PRODUCT_QUERY = ('query VerdugoProducts($channel: String!) { '
                 'products(first: 20, channel: $channel) { '
                 'edges { node { id } } pageInfo { hasNextPage } } }')
STATUS_VALUES = ('draft', 'published', 'scheduled')


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', value):
        raise VerdugoError('Reviewed lowercase collection or channel slug required')
    return value


def period(params, cfg):
    fields(params, (), ('start_date', 'end_date'))
    if bool('start_date' in params) != bool('end_date' in params):
        raise VerdugoError('Both dates must be supplied together')
    values = [params.get(k, cfg.get('report_' + k)) for k in ('start_date', 'end_date')]
    try:
        if any(not isinstance(v, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) for v in values):
            raise ValueError()
        start, end = map(date.fromisoformat, values)
        if not 0 <= (end - start).days <= 92:
            raise ValueError()
    except (ValueError, TypeError):
        raise VerdugoError('Explicit ISO dates in order, at most 93 days, required') from None
    return values


def _b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def ghost_token(token):
    if not re.fullmatch(r'[0-9a-fA-F]{24}:[0-9a-fA-F]{64}', token):
        raise VerdugoError('Ghost admin key must contain a 24-hex ID and 64-hex secret')
    kid, secret = token.split(':')
    now = int(time.time())
    parts = [_b64(encode({'alg': 'HS256', 'typ': 'JWT', 'kid': kid}).encode()),
             _b64(encode({'iat': now, 'exp': now + 300, 'aud': '/admin/'}).encode())]
    signing = '.'.join(parts)
    sig = hmac.new(bytes.fromhex(secret), signing.encode(), hashlib.sha256).digest()
    return signing + '.' + _b64(sig)


def authorization(service, cfg, token):
    if service == 'postiz':
        if cfg.get('api_surface') not in ('cloud', 'self_hosted'):
            raise VerdugoError('Postiz cloud or self_hosted API surface required')
        return {'Authorization': token}
    if service == 'payload':
        auth = slug(cfg.get('auth_collection'))
        content = slug(cfg.get('content_collection'))
        if auth == content or content.startswith('payload-'):
            raise VerdugoError('Payload content must be separate from auth/system collections')
        return {'Authorization': auth + ' API-Key ' + token}
    if service == 'ghost':
        version = cfg.get('api_version')
        if not isinstance(version, str) or not re.fullmatch(r'v[1-9][0-9]?\.[0-9]{1,2}', version):
            raise VerdugoError('Explicit Ghost Accept-Version required')
        return {'Authorization': 'Ghost ' + ghost_token(token), 'Accept-Version': version}
    if service == 'saleor':
        slug(cfg.get('channel'))
    elif service == 'plausible':
        site = cfg.get('site_id')
        if not isinstance(site, str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', site) or '..' in site:
            raise VerdugoError('Reviewed Plausible site domain required')
    elif service == 'matomo':
        integer(cfg.get('site_id'), 1, 10**9)
        return {}  # token_auth goes only into the private form body, never the URL.
    return {'Authorization': 'Bearer ' + token}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Marketing read operation not implemented')
    method, path = SPECS[service][operation]
    query, body = {}, None
    if service in ('plausible', 'matomo'):
        start, end = period(params, cfg)
        if service == 'plausible':
            body = {'site_id': cfg['site_id'], 'metrics': METRICS[:],
                    'date_range': [start, end], 'dimensions': []}
        else:
            body = {'module': 'API', 'method': 'VisitsSummary.get', 'idSite': cfg['site_id'],
                    'period': 'range', 'date': start + ',' + end,
                    'format': 'JSON', 'format_metrics': 0}
    elif service == 'saleor':
        fields(params)
        body = {'query': PRODUCT_QUERY, 'variables': {'channel': cfg['channel']}}
    else:
        fields(params, (), ('page',))
        page = integer(params.get('page', 1), 1, 1000)
        if service == 'postiz':
            if page != 1:
                raise VerdugoError('Postiz channel pagination is not implemented')
            if cfg['api_surface'] == 'self_hosted':
                path = '/api' + path
        elif service == 'payload':
            path = path.format(content_collection=cfg['content_collection'])
            query = {'limit': 20, 'page': page, 'depth': 0}
        elif service == 'ghost':
            query = {'limit': 20, 'page': page, 'fields': 'id,status'}
    if body is not None:
        headers['Content-Type'] = ('application/x-www-form-urlencoded' if service == 'matomo'
                                   else 'application/json')
    # Bind the source key, not the ephemeral Ghost JWT; rotation invalidates plans,
    # while JWT renewal does not cause needless conflicts or duplicate calls.
    stable_headers = {k: v for k, v in headers.items() if k != 'Authorization'}
    public = {'service': service, 'operation': operation, 'method': method,
              'url': origin + path + ('?' + urlencode(query) if query else ''),
              'body': body, 'version': cfg.get('version'),
              'credential_binding': digest({'source_key': token, 'headers': stable_headers,
                                            'auth_collection': cfg.get('auth_collection')}),
              'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'read_only': True,
              'network_policy': {'private': cfg.get('allow_private_network') is True,
                                 'loopback': cfg.get('allow_local_http') is True}}
    secrets = [token] + [v for k, v in headers.items() if k == 'Authorization']
    if service == 'ghost':
        secrets.append(token.split(':')[1])
    request = {'public': public, 'headers': headers, 'mutates': False, 'secret_values': secrets}
    if service == 'matomo':
        request['private_form'] = {'token_auth': token}
    return request


def form_bytes(request):
    """Serialize only our Matomo read; never accept a generic private body override."""
    p = request['public']
    body = p['body']
    if ((p['service'], p['operation']) != ('matomo', 'visits.summary') or p['method'] != 'POST'
            or not isinstance(body, dict) or body.get('method') != 'VisitsSummary.get'):
        raise VerdugoError('Unsupported private form operation')
    private = request.get('private_form')
    fields(private, ('token_auth',))
    return urlencode(body | private).encode()


def _objects(value, limit=20):
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(x, dict) for x in value):
        raise VerdugoError('Provider must return a bounded object collection')
    return value


def _number(value):
    if type(value) not in (int, float) or not 0 <= value <= 10**15 or not math.isfinite(value):
        raise VerdugoError('Provider metric must be finite, numeric and nonnegative')
    return value


def _bool(value):
    if type(value) is not bool:
        raise VerdugoError('Provider pagination/disabled flag must be boolean')
    return value


def check(service, operation, response, request=None):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Marketing read response operation mismatch')
    out = {'service': service, 'operation': operation, 'live_verified': False,
           'raw_provider_payload_retained': False,
           'scope': 'one_response_not_complete_export'}
    if service == 'postiz':
        rows = _objects(response, 1000)
        disabled = sum(_bool(row.get('disabled')) for row in rows)
        return out | {'records_in_response': len(rows), 'disabled_channels': disabled,
                      'enabled_channels': len(rows) - disabled}
    if not isinstance(response, dict) or response.get('errors'):
        raise VerdugoError('Provider response missing or contains errors')
    if service in ('payload', 'ghost'):
        rows = _objects(response.get('docs' if service == 'payload' else 'posts'))
        counts = {}
        for row in rows:
            status = row.get('_status' if service == 'payload' else 'status')
            label = status if type(status) is str and status in STATUS_VALUES else 'other'
            counts[label] = counts.get(label, 0) + 1
        out.update(records_in_response=len(rows), status_counts=counts)
        if service == 'payload':
            out['has_next_page'] = _bool(response.get('hasNextPage'))
        else:
            meta = response.get('meta')
            pag = meta.get('pagination') if isinstance(meta, dict) else None
            if not isinstance(pag, dict):
                raise VerdugoError('Ghost pagination schema mismatch')
            nxt = pag.get('next')
            if nxt is not None:
                integer(nxt, 1, 10**9)
            out['has_next_page'] = nxt is not None
        return out
    if service == 'saleor':
        if 'errors' in response and response['errors'] != []:
            raise VerdugoError('Saleor returned GraphQL errors or an invalid error envelope')
        data = response.get('data')
        products = data.get('products') if isinstance(data, dict) else None
        if not isinstance(products, dict):
            raise VerdugoError('Saleor products schema mismatch')
        rows = _objects(products.get('edges'))
        for edge in rows:
            node = edge.get('node')
            if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
                raise VerdugoError('Saleor product node is missing')
        page_info = products.get('pageInfo')
        if not isinstance(page_info, dict):
            raise VerdugoError('Saleor pagination missing')
        return out | {'records_in_response': len(rows),
                      'has_next_page': _bool(page_info.get('hasNextPage'))}
    if not isinstance(request, dict) or not isinstance(request.get('body'), dict):
        raise VerdugoError('Metric response must be bound to its request')
    expected = request['body']
    if service == 'plausible':
        query = response.get('query')
        if (not isinstance(query, dict) or query.get('site_id') != expected['site_id']
                or query.get('metrics') != METRICS or query.get('dimensions') != []):
            raise VerdugoError('Plausible response does not match requested site/metrics')
        echoed_dates = query.get('date_range')
        try:
            if not isinstance(echoed_dates, list) or len(echoed_dates) != 2:
                raise ValueError()
            normalized = [(date.fromisoformat(v) if len(v) == 10 else
                           datetime.fromisoformat(v.replace('Z', '+00:00')).date()).isoformat()
                          for v in echoed_dates if isinstance(v, str)]
            if normalized != expected['date_range']:
                raise ValueError()
        except (ValueError, TypeError):
            raise VerdugoError('Plausible response date range mismatch') from None
        rows = _objects(response.get('results'), 1)
        if len(rows) != 1 or rows[0].get('dimensions') != []:
            raise VerdugoError('Plausible aggregate row missing')
        values = rows[0].get('metrics')
        if not isinstance(values, list) or len(values) != len(METRICS):
            raise VerdugoError('Plausible metric arity mismatch')
        metrics = {name: _number(value) for name, value in zip(METRICS, values)}
        dates = expected['date_range']
    else:
        metrics = {name: _number(response.get(name)) for name in ('nb_visits', 'nb_actions')}
        dates = expected['date'].split(',')
    return out | {'metrics': metrics, 'requested_dates': dates,
                  'basis': 'provider_reported_not_revenue_or_causal_attribution'}
