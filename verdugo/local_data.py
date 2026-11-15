"""Queries over original pinned datasets and explicit source rules; no network."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re

DISTRIBUTION = 'verdugo-bundled-data'
SPECS = {
    'local-seo-skills': ('nap.compare', DISTRIBUTION, 'c3b7a25b7d5cc370752d74cfea240ccf992a24db'),
    'ipranges': ('address.match', DISTRIBUTION, 'd4ea6c582a509538907480e641bcee6821746bc3'),
    'the-great-gpt-firewall': ('domains.observe', DISTRIBUTION, '60b2214d7b2cbd2c1b9d175afb31ad3024c085bb'),
}
FILES = {
    'local-seo-skills': ('local-citations.md', '30b25200928df3b94e68e2506f384195b1e0e372'),
    'ipranges': ('googlebot-ipv4.txt', 'e7844f5449514bbd3c01399601a8590bb5e48d5a'),
    'the-great-gpt-firewall': ('gpt-firewall-2026-11.json', 'f1bf68b108d7f860ac244606a5eeca3f0e678477'),
}


def source_bytes(service):
    name, expected = FILES[service]
    data = (Path(__file__).parent/'data'/name).read_bytes()
    blob = hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
    if blob != expected: raise ValueError('Bundled data does not match upstream Git blob')
    if service == 'local-seo-skills':
        license_data = (Path(__file__).parent/'data/local-citations.LICENSE').read_bytes()
        if hashlib.sha256(license_data).hexdigest() != '00b6ea72daef47b0e9bd355fe397526999cb417d4103cc413d0a28f1055380db':
            raise ValueError('Bundled guidance license changed')
    return data


def validate(service, operation, p):
    from .common import fields, VerdugoError
    if service not in SPECS or SPECS[service][0] != operation: raise VerdugoError('Unsupported dataset operation')
    if service == 'local-seo-skills':
        from .common import identifier
        from .local_native_tools import private_json
        fields(p,('dataset','secret_text'))
        if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
        data=private_json(p);fields(data,('reference','listings'));fields(data['reference'],('name','address','phone'))
        if not isinstance(data['listings'],list) or not 1<=len(data['listings'])<=50:raise VerdugoError('Provide 1..50 supplied NAP listings')
        seen=set()
        for row in data['listings']:
            fields(row,('id','name','address','phone'));identifier(row['id'])
            if row['id'] in seen:raise VerdugoError('Duplicate listing identifier')
            seen.add(row['id'])
        for row in [data['reference'],*data['listings']]:
            for field in ('name','address'):
                if not isinstance(row[field],str) or not 1<=len(row[field])<=500:raise VerdugoError('Bounded canonical NAP text required')
            if not isinstance(row['phone'],str) or not re.fullmatch(r'\+[0-9]{8,15}',row['phone']):raise VerdugoError('Canonical international phone numbers required')
        return
    key = 'addresses' if service == 'ipranges' else 'domains'
    try: fields(p, ('dataset', key))
    except (ValueError, TypeError, OverflowError) as exc: raise VerdugoError('Bounded finite JSON required') from exc
    if p['dataset'] not in ('demo', 'real'): raise VerdugoError('Explicit dataset required')
    if not isinstance(p[key], list) or not 1 <= len(p[key]) <= 100: raise VerdugoError('Provide 1..100 values')
    for value in p[key]:
        if not isinstance(value, str): raise VerdugoError('String values required')
        if service == 'ipranges':
            try: ipaddress.IPv4Address(value)
            except ValueError as exc: raise VerdugoError('Only canonical IPv4 literals supported') from exc
        elif len(value) > 253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', value):
            raise VerdugoError('Lowercase ASCII domain name required')


def run(service, p):
    data = source_bytes(service)
    base = {'snapshot_commit': SPECS[service][2], 'live_verified': False, 'network_calls': 0}
    if service == 'local-seo-skills':
        from .local_native_tools import private_json
        supplied=private_json(p);reference=supplied['reference']
        results=[{'id':row['id'],'mismatched_fields':[key for key in ('name','address','phone') if row[key]!=reference[key]]} for row in supplied['listings']]
        return base | {'listings':results,'consistent':sum(not row['mismatched_fields'] for row in results),
                       'checked':len(results),'directory_presence_verified':False,'rankings_measured':False,
                       'method':'first-party implementation of exact NAP rules from pinned local-citations guidance',
                       'source_kind':'instructions interpreted as rules; not an upstream executable or MCP server'}
    if service == 'ipranges':
        ranges = [ipaddress.IPv4Network(row) for row in data.decode().splitlines()]
        return base | {'provider': 'googlebot', 'address_family': 'IPv4', 'ranges_in_snapshot': len(ranges),
            'matches': [any(ipaddress.IPv4Address(value) in network for network in ranges) for value in p['addresses']],
            'crawler_identity_verified': False, 'firewall_changed': False}
    records = {r['domain']: r for r in json.loads(data)}
    return base | {'snapshot_label': '2026-11', 'domains': [
        {'domain': value, 'in_snapshot': value in records,
         'recorded_gptbot_block': records[value]['breakdown']['gptbot'] if value in records else None}
        for value in p['domains']], 'permission_granted': False, 'robots_fetched': False}
