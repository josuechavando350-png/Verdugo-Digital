"""Explicit credential-free reads at two fixed public data origins.

These are REST adapters for the APIs wrapped by the catalogued clients. They
do not claim to execute those Python clients or to certify live availability.
"""
import hashlib
import math
from pathlib import Path
import re
from urllib.parse import urlencode

from .common import VerdugoError, digest, fields, integer

SPECS = {'gdeltdoc': {'articles.summary': ('GET', '/api/v2/doc/doc')},
         'wbgapi': {'population.read': ('GET', '/v2/country/{country}/indicator/SP.POP.TOTL')}}
ORIGINS = {'gdeltdoc': 'https://api.gdeltproject.org', 'wbgapi': 'https://api.worldbank.org'}
PINS = {'gdeltdoc': '41220163fbab99982e4dca3a05d25a95b49896d7', 'wbgapi': '4d0d2c925a8dac359df5a2d9e82001ff6feeecda'}


def connection(service, cfg, origin):
    if (origin != ORIGINS[service] or cfg.get('auth_mode') != 'public_no_credentials'
            or cfg.get('public_access_reviewed') is not True or cfg.get('token_env') is not None):
        raise VerdugoError('Review this fixed public API; credentials and custom origins are prohibited')
    return origin, None, {'Accept': 'application/json', 'User-Agent': 'Verdugo-Digital/0.21'}


def build(service, operation, params, cfg, origin, token, headers):
    if operation not in SPECS.get(service, {}):
        raise VerdugoError('Unsupported public read')
    fields(params, (), ('page',))
    if integer(params.get('page', 1), 1, 1000) != 1:
        raise VerdugoError('Only the first bounded response is implemented')
    connection(service, cfg, origin)
    method, path = SPECS[service][operation]
    scope = {}
    if service == 'gdeltdoc':
        terms = cfg.get('query_terms')
        if not isinstance(terms, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9 ]{2,79}', terms):
            raise VerdugoError('Administrator-supplied plain English topic required')
        query = {'query': '"' + terms + '"', 'mode': 'artlist', 'format': 'json', 'maxrecords': 50, 'timespan': '24h'}
    else:
        country, year = cfg.get('country'), integer(cfg.get('year'), 1960, 2025)
        if not isinstance(country, str) or not re.fullmatch('[A-Z]{3}', country):
            raise VerdugoError('An administrator-supplied ISO3 country is required')
        path = path.format(country=country)
        query = {'format': 'json', 'date': year, 'per_page': 1, 'page': 1}
        scope = {'country': country, 'year': year}
    public = {'service': service, 'operation': operation, 'method': method, 'url': origin + path + '?' + urlencode(query),
              'body': None, 'version': cfg.get('version'), 'credential_binding': digest(headers),
              'authentication_policy': {'mode': 'public_no_credentials'}, 'query_scope': scope,
              'contract_source_commit': PINS[service], 'implementation_binding': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'network_policy': {'private': False, 'loopback': cfg.get('allow_local_http') is True}}
    return {'public': public, 'headers': headers, 'mutates': False, 'secret_values': []}


def check(service, operation, response, request=None):
    def bad():
        raise VerdugoError('Public data response schema mismatch')
    if operation not in SPECS.get(service, {}):
        bad()
    result = {'service': service, 'operation': operation, 'raw_provider_payload_retained': False,
              'live_verified': False, 'production_certified': False, 'scope': 'one_bounded_response'}
    if service == 'gdeltdoc':
        rows = response.get('articles') if isinstance(response, dict) else None
        # Upstream returns {} for zero matches, but an arbitrary missing field
        # or provider error must never become a successful empty observation.
        if response == {}:
            rows = []
        if not isinstance(rows, list) or len(rows) > 50:
            bad()
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('url'), str) or not row['url'].startswith(('https://', 'http://')) or row['url'] in seen:
                bad()
            seen.add(row['url'])
        return result | {'articles_in_response': len(rows), 'daily_total_coverage': False,
                         'article_content_retrieved': False, 'sources_fact_checked': False}
    if not isinstance(response, list) or len(response) != 2 or not isinstance(response[0], dict):
        bad()
    header, rows = response
    if type(header.get('page')) is not int or header['page'] != 1 or type(header.get('total')) is not int or header['total'] not in (0, 1):
        bad()
    if rows is None and header['total'] == 0:
        rows = []
    if not isinstance(rows, list) or len(rows) != header['total']:
        bad()
    if not rows:
        return result | {'observation_available': False, 'population_reported': None}
    row = rows[0]
    if not isinstance(row, dict) or not isinstance(row.get('indicator'), dict) or row['indicator'].get('id') != 'SP.POP.TOTL':
        bad()
    country, date, value = row.get('countryiso3code'), row.get('date'), row.get('value')
    if not isinstance(country, str) or not re.fullmatch('[A-Z]{3}', country) or not isinstance(date, str) or not re.fullmatch(r'\d{4}', date):
        bad()
    if request and {'country': country, 'year': int(date)} != request['query_scope']:
        bad()
    if value is not None and (type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 10**11 or int(value) != value):
        bad()
    return result | {'country': country, 'year': int(date), 'observation_available': value is not None,
                     'population_reported': int(value) if value is not None else None,
                     'current_population_estimate': False}
