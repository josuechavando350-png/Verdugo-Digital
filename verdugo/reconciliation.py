"""Out-of-band human attestations, not automatic upstream or bank verification."""
import json
import os
import time
from .adapters import remote_id
from .common import VerdugoError, digest, encode, fields, identifier, sanitize, text

SCHEMA = '''
CREATE TABLE IF NOT EXISTS reconciliations (
 tenant TEXT NOT NULL, key TEXT NOT NULL, fingerprint TEXT NOT NULL,
 actor TEXT NOT NULL, evidence_ref TEXT NOT NULL, response_hash TEXT NOT NULL,
 at REAL NOT NULL, PRIMARY KEY(tenant,key));
'''


def pending(engine):
    rows = engine.db.execute("SELECT r.key,r.hash fingerprint,r.state,r.started,p.document FROM runs r "
        "JOIN plans p ON r.tenant=p.tenant AND r.key=p.key WHERE r.tenant=? AND r.state IN ('uncertain','running') "
        'ORDER BY r.started LIMIT 200', (engine.tenant,)).fetchall()
    return {'tenant': engine.tenant, 'items': [{k: r[k] for k in ('key','fingerprint','state','started')} |
        {'service': json.loads(r['document']).get('service'), 'operation': json.loads(r['document']).get('operation')}
        for r in rows], 'limit': 200, 'upstream_verified': False}


def confirm(engine, evidence):
    if engine.role != 'approver': raise VerdugoError('Separate local approver role required')
    fields(evidence, ('key', 'fingerprint', 'response', 'verified_email', 'evidence_ref'))
    key = identifier(evidence['key'])
    ref = text(evidence['evidence_ref'], 500)
    email = text(evidence['verified_email'], 254)
    if not isinstance(evidence['response'], dict): raise VerdugoError('Response evidence must be an object')
    with engine.transaction():
        row = engine.db.execute('SELECT r.state,r.hash,r.result,p.document FROM runs r JOIN plans p '
              'ON r.tenant=p.tenant AND r.key=p.key WHERE r.tenant=? AND r.key=?', (engine.tenant, key)).fetchone()
        if not row or row['state'] != 'uncertain' or row['hash'] != evidence['fingerprint']:
            raise VerdugoError('Exact uncertain run required; running actions cannot be reconciled while possibly active')
        req = json.loads(row['document'])
        if (req.get('service'), req.get('operation')) not in (('twenty','people.create'), ('chatwoot','contacts.create')):
            raise VerdugoError('Only supported contact creation can be attested')
        expected = (req['body']['emails']['primaryEmail'] if req['service']=='twenty' else req['body']['email'])
        if email != expected: raise VerdugoError('Verified email does not match the planned contact')
        cfg = engine.config['tenants'][engine.tenant].get('services', {}).get(req['service'], {})
        known_secret = os.environ.get(cfg.get('token_env', ''), '')
        response = sanitize(evidence['response'], [known_secret])
        ref = sanitize(ref, [known_secret])
        remote_id(response, req['result_id_path'])
        engine.db.execute('INSERT INTO reconciliations VALUES(?,?,?,?,?,?,?)',
            (engine.tenant, key, row['hash'], engine.actor, ref, digest(response), time.time()))
        engine.finish(key, 'succeeded', response)
        engine.event(key, 'action.reconciled_by_human', {'actor': engine.actor, 'evidence_ref': ref,
                    'response_hash': digest(response), 'prior_result_hash': digest(row['result']), 'upstream_verified_by_code': False})
    return {'state': 'succeeded', 'key': key, 'basis': 'human_attestation',
            'upstream_verified_by_code': False, 'external_call_made': False}
