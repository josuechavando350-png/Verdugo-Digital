"""Tenant-scoped aliases backed by successful, validated creation runs."""
import json
import time
from .adapters import remote_id
from .common import VerdugoError, fields, identifier

ACTIONS = {'identity.bind', 'identity.summary'}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS identities (
 tenant TEXT NOT NULL, lead_id TEXT NOT NULL, dataset TEXT NOT NULL,
 service TEXT NOT NULL, scope TEXT NOT NULL, remote_id TEXT NOT NULL,
 source_key TEXT NOT NULL, created REAL NOT NULL,
 PRIMARY KEY(tenant,lead_id,service,scope),
 UNIQUE(tenant,service,scope,remote_id), UNIQUE(tenant,source_key));
'''


def validate(operation, params):
    required = ('lead_id', 'dataset')
    if operation == 'identity.bind': required += ('service', 'source_key')
    fields(params, required)
    identifier(params['lead_id'])
    if params['dataset'] not in ('demo', 'real'):
        raise VerdugoError('Explicit demo or real dataset required')
    if operation == 'identity.bind':
        identifier(params['source_key'])
        if params['service'] not in ('twenty', 'chatwoot'):
            raise VerdugoError('Only validated contact creation sources can bind identities')


def apply(engine, operation, params):
    """Called within the engine transaction; never makes a network request."""
    lead = engine.record('lead', params['lead_id'])
    if not lead or lead['dataset'] != params['dataset']:
        raise VerdugoError('Lead/dataset not found in this tenant')
    if operation == 'identity.summary':
        rows = engine.db.execute(
            'SELECT service,scope,remote_id,source_key FROM identities '
            'WHERE tenant=? AND lead_id=? AND dataset=? ORDER BY service,scope',
            (engine.tenant, params['lead_id'], params['dataset']))
        return {'lead_id': params['lead_id'], 'dataset': params['dataset'],
                'aliases': [dict(row) for row in rows], 'bidirectional_sync': False}
    row = engine.db.execute(
        'SELECT r.state,r.result,p.document FROM runs r JOIN plans p '
        'ON r.tenant=p.tenant AND r.key=p.key WHERE r.tenant=? AND r.key=?',
        (engine.tenant, params['source_key'])).fetchone()
    if not row or row['state'] != 'succeeded':
        raise VerdugoError('Identity source must be a successful creation in the same tenant')
    request, response = json.loads(row['document']), json.loads(row['result'])
    expected = 'people.create' if params['service'] == 'twenty' else 'contacts.create'
    if request.get('service') != params['service'] or request.get('operation') != expected:
        raise VerdugoError('Identity source has the wrong service or action')
    body = request.get('body', {})
    email = (body.get('emails', {}).get('primaryEmail') if params['service'] == 'twenty'
             else body.get('email'))
    if email != lead['email']:
        raise VerdugoError('Identity source does not match the canonical contact email')
    rid = remote_id(response, request.get('result_id_path'))
    scope = request.get('identity_scope')
    if not isinstance(scope, str) or len(scope) != 64:
        raise VerdugoError('Creation has no verified identity scope; legacy result cannot be bound')
    existing = engine.db.execute(
        'SELECT * FROM identities WHERE tenant=? AND lead_id=? AND service=? AND scope=?',
        (engine.tenant, params['lead_id'], params['service'], scope)).fetchone()
    if existing:
        if (existing['remote_id'] != rid or existing['dataset'] != params['dataset']
                or existing['source_key'] != params['source_key']):
            raise VerdugoError('Canonical identity is already bound to another creation')
    else:
        conflict = engine.db.execute(
            'SELECT 1 FROM identities WHERE tenant=? AND '
            '((service=? AND scope=? AND remote_id=?) OR source_key=?)',
            (engine.tenant, params['service'], scope, rid, params['source_key'])).fetchone()
        if conflict:
            raise VerdugoError('Remote identity is already assigned to another canonical lead')
        engine.db.execute('INSERT INTO identities VALUES(?,?,?,?,?,?,?,?)',
            (engine.tenant, params['lead_id'], params['dataset'], params['service'],
             scope, rid, params['source_key'], time.time()))
    return {'lead_id': params['lead_id'], 'service': params['service'],
            'remote_id': rid, 'scope': scope, 'source_key': params['source_key'],
            'dataset': params['dataset']}
