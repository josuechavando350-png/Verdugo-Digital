"""Queries over two original, pinned, bundled public datasets; no network."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re

DISTRIBUTION = 'verdugo-bundled-data'
SPECS = {
    'ipranges': ('address.match', DISTRIBUTION, 'd4ea6c582a509538907480e641bcee6821746bc3'),
    'the-great-gpt-firewall': ('domains.observe', DISTRIBUTION, '60b2214d7b2cbd2c1b9d175afb31ad3024c085bb'),
}
FILES = {
    'ipranges': ('googlebot-ipv4.txt', 'e7844f5449514bbd3c01399601a8590bb5e48d5a'),
    'the-great-gpt-firewall': ('gpt-firewall-2026-11.json', 'f1bf68b108d7f860ac244606a5eeca3f0e678477'),
}


def source_bytes(service):
    name, expected = FILES[service]
    data = (Path(__file__).parent/'data'/name).read_bytes()
    blob = hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
    if blob != expected: raise ValueError('Bundled data does not match upstream Git blob')
    return data


def validate(service, operation, p):
    from .common import fields, VerdugoError
    if service not in SPECS or SPECS[service][0] != operation: raise VerdugoError('Unsupported dataset operation')
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
