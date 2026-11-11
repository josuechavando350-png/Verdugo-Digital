"""Operator-gated contract observations for a first authorized provider pilot.

One bounded GET per selected provider. A matching response is NOT a live-production
certification. Raw response stays in the protected Engine store, not in this report.
"""
from collections import Counter
import json
import re
import time
from .common import VerdugoError, digest, encode, fields, identifier, text
from .adapters import SPECS, service_config

PROBES = {
    'twenty': 'people.list',
    'chatwoot': 'conversations.list',
    'listmonk': 'lists.list',
    'umami': 'websites.list',
    'mautic': 'contacts.list',
    'formbricks': 'surveys.list',
}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS pilot_manifests (
 tenant TEXT NOT NULL, probe_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
 created REAL NOT NULL, PRIMARY KEY(tenant,probe_id));
CREATE TABLE IF NOT EXISTS pilot_observations (
 tenant TEXT NOT NULL, probe_id TEXT NOT NULL, service TEXT NOT NULL,
 state TEXT NOT NULL, response_digest TEXT, count_items INTEGER,
 observed REAL NOT NULL, PRIMARY KEY(tenant,probe_id,service));
'''
PATH = re.compile(r'(?:\$|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){0,7})\Z')


def observation_contract(engine, service):
    if service not in PROBES: raise VerdugoError('Service has no bounded pilot contract')
    cfg = service_config(engine.config, engine.tenant, service)
    contract = cfg.get('acceptance')
    if not isinstance(contract, dict): raise VerdugoError('Pilot acceptance contract not configured: ' + service)
    fields(contract, ('reviewed', 'environment', 'collection_path', 'collection_type', 'contract_ref'))
    if contract['reviewed'] is not True: raise VerdugoError('Pilot contract review required: ' + service)
    if contract['environment'] not in ('fixture', 'sandbox'):
        raise VerdugoError('Production/unspecified pilot environment not allowed')
    path = contract['collection_path']
    if not isinstance(path, str) or not PATH.fullmatch(path):
        raise VerdugoError('Bounded collection path required')
    if contract['collection_type'] not in ('array', 'object'):
        raise VerdugoError('Explicit array/object collection type required')
    doc = text(contract['contract_ref'], 240)
    if doc.lower().startswith(('replace', 'todo', 'example')):
        raise VerdugoError('Reviewed contract reference required')
    engine.preflight(service, PROBES[service])
    if contract['environment'] == 'sandbox':
        from urllib.parse import urlsplit
        url = urlsplit(cfg['base_url'])
        if url.scheme != 'https' or url.hostname in ('example.invalid', 'localhost'):
            raise VerdugoError('Sandbox validation requires a real HTTPS origin')
    return dict(contract)


def _items(data, path, kind):
    current = data
    if path != '$':
        for key in path.split('.'):
            if not isinstance(current, dict) or key not in current:
                raise VerdugoError('Pilot response does not match the reviewed collection path')
            current = current[key]
    if kind == 'array':
        if not isinstance(current, list) or any(not isinstance(item, dict) for item in current):
            raise VerdugoError('Pilot response array contains invalid entries')
    else:
        if not isinstance(current, dict) or any(not isinstance(item, dict) for item in current.values()):
            raise VerdugoError('Pilot response collection contains invalid values')
    return len(current)


def check(engine, request, execute=False):
    fields(request, ('probe_id', 'services'))
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    if execute and engine.role != 'operator': raise VerdugoError('Operator role required for external pilot checks')
    pid = identifier(request['probe_id'])
    if len(pid) > 40: raise VerdugoError('Probe ID exceeds 40 characters')
    services = request['services']
    if (not isinstance(services, list) or not 1 <= len(services) <= 6 or
            any(not isinstance(s, str) or s not in PROBES for s in services) or
            len(set(services)) != len(services)):
        raise VerdugoError('Choose 1..6 distinct supported services')
    # Ensure no calls run before *all* destinations, credentials and contracts validate.
    manifest = []
    for sid in services:
        contract = observation_contract(engine, sid)
        command = {'service': sid, 'operation': PROBES[sid], 'params': {},
                   'key': 'pilot-' + digest([pid, sid])[:35]}
        plan = engine.plan(command)
        manifest.append({'service': sid, 'contract': contract, 'command': command,
                         'plan_fingerprint': plan['fingerprint']})
    fingerprint = digest({'tenant': engine.tenant, 'probe_id': pid, 'manifest': manifest})
    with engine.transaction():
        old = engine.db.execute('SELECT fingerprint FROM pilot_manifests WHERE tenant=? AND probe_id=?',
                                (engine.tenant, pid)).fetchone()
        if old and old['fingerprint'] != fingerprint:
            raise VerdugoError('Probe ID reused with different services/contract/configuration')
        engine.db.execute('INSERT OR IGNORE INTO pilot_manifests VALUES(?,?,?,?)',
                          (engine.tenant, pid, fingerprint, time.time()))
    if not execute:
        return {'state': 'planned', 'tenant': engine.tenant, 'probe_id': pid,
                'services': services, 'environment': {m['service']: m['contract']['environment'] for m in manifest},
                'external_call_made': False, 'live_verified': 0,
                'production_certified': False}
    rows = []
    for m in manifest:
        sid, contract = m['service'], m['contract']
        result = engine.execute(m['command'], True)
        state, count, rhash = 'read_failed', None, None
        if result['state'] == 'succeeded':
            rhash = digest(result['result'])
            try:
                count = _items(result['result'], contract['collection_path'], contract['collection_type'])
                state = 'schema_observed'
            except VerdugoError:
                state = 'schema_mismatch'
        elif result['state'] == 'running':
            state = 'pending'
        # Evidence is idempotently persisted. A pending concurrent read must not
        # be frozen as failure; another probe_id is required for a new observation.
        if state != 'pending':
            with engine.transaction():
                engine.db.execute('INSERT OR IGNORE INTO pilot_observations '
                    '(tenant,probe_id,service,state,response_digest,count_items,observed) VALUES(?,?,?,?,?,?,?)',
                    (engine.tenant, pid, sid, state, rhash, count, time.time()))
        row = engine.db.execute('SELECT state,response_digest,count_items,observed FROM pilot_observations '
                                'WHERE tenant=? AND probe_id=? AND service=?', (engine.tenant, pid, sid)).fetchone()
        if row: state, rhash, count, observed = row['state'], row['response_digest'], row['count_items'], row['observed']
        else: observed = None
        rows.append({'service': sid, 'environment': contract['environment'], 'state': state,
                     'observed_items_first_response': count, 'response_sha256': rhash,
                     'observed_at': observed, 'replayed': result.get('replayed', False),
                     'production_certified': False})
    return {'state': 'checked' if all(row['state']=='schema_observed' for row in rows) else 'incomplete',
            'tenant': engine.tenant, 'probe_id': pid, 'checks': rows,
            'counts': dict(Counter(r['state'] for r in rows)), 'live_verified': 0,
            'production_certified': False, 'full_dataset_checked': False,
            'message': 'Observed API response shape only. Does not certify production, tenancy, business results or origin authenticity.'}
