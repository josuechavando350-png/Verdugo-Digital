"""Cooperative single-host recovery. No remote retry or success inference."""
import json
from .common import VerdugoError, digest, fields, identifier

WRITES = {('twenty', 'people.create'), ('chatwoot', 'contacts.create')}


def source(engine, key, fingerprint, states=('uncertain',)):
    identifier(key)
    row = engine.db.execute('SELECT r.state,r.hash,r.result,p.document FROM runs r JOIN plans p '
        'ON r.tenant=p.tenant AND r.key=p.key WHERE r.tenant=? AND r.key=?', (engine.tenant, key)).fetchone()
    if not row or row['state'] not in states or row['hash'] != fingerprint:
        raise VerdugoError('Exact contact run in the required state not found')
    req = json.loads(row['document'])
    if (req.get('service'), req.get('operation')) not in WRITES:
        raise VerdugoError('Recovery supports only the two contact creation actions')
    if digest({'tenant': engine.tenant, 'key': key, 'request': req}) != fingerprint:
        raise VerdugoError('Stored plan integrity mismatch')
    return row, req


def recover_running(engine, request, execute=False):
    if engine.role != 'approver': raise VerdugoError('Separate local approver role required')
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    fields(request, ('key', 'fingerprint'))
    key = request['key']
    source(engine, key, request['fingerprint'], ('running',))
    engine.guards.require_record(engine, key)
    with engine.guards.hold(engine.tenant, key):
        with engine.transaction():
            source(engine, key, request['fingerprint'], ('running',))
            engine.guards.require_record(engine, key)
            if not execute:
                return {'state': 'planned', 'key': key, 'local_lock_available': True,
                        'remote_effect_unknown': True, 'external_call_made': False}
            engine.finish(key, 'uncertain', {'reconciliation_required': True,
                'reason': 'local_execution_no_longer_holds_guard', 'remote_effect_unknown': True})
            engine.event(key, 'action.running_recovered', {'actor': engine.actor,
                'fingerprint': request['fingerprint'], 'guard_scope': engine.guards.scope,
                'remote_effect_unknown': True, 'post_retry_authorized': False})
    return {'state': 'uncertain', 'key': key, 'external_call_made': False,
            'remote_effect_unknown': True, 'post_retry_authorized': False}
