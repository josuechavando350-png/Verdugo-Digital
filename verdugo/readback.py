"""Persisted provider readback evidence. A matching record is not proof of creation.

No source write is retried or completed by verify(). A separate local approver
must review a recent immutable observation before confirm() can resolve it.
"""
import json
import re
import time
from urllib.parse import urlsplit
from .adapters import remote_id, validate_origin, connection
from .common import VerdugoError, digest, encode, fields, identifier, sanitize, text

MAX_AGE = 300
SCHEMA = '''
CREATE TABLE IF NOT EXISTS contact_readbacks (
 tenant TEXT NOT NULL, check_id TEXT NOT NULL, source_key TEXT NOT NULL,
 source_hash TEXT NOT NULL, hash TEXT NOT NULL, document TEXT NOT NULL,
 read_key TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'planned',
 response_hash TEXT, observed REAL, outcome TEXT,
 PRIMARY KEY(tenant,check_id));
'''
SUPPORTED = {'twenty': ('people.create', 'people.get'),
             'chatwoot': ('contacts.create', 'contacts.get')}


def extract(document, path):
    if not isinstance(path, str) or not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){0,11}', path):
        raise VerdugoError('Explicit bounded readback_record_path required')
    value = document
    for part in path.split('.'):
        if not isinstance(value, dict) or part not in value:
            raise VerdugoError('Readback response does not match the reviewed schema')
        value = value[part]
    if not isinstance(value, dict): raise VerdugoError('Readback record must be an object')
    return value


def source(engine, key, fingerprint):
    identifier(key)
    row = engine.db.execute('SELECT r.state,r.hash,r.result,r.finished,p.document FROM runs r JOIN plans p '
        'ON r.tenant=p.tenant AND r.key=p.key WHERE r.tenant=? AND r.key=?', (engine.tenant, key)).fetchone()
    if not row or row['state'] != 'uncertain' or row['hash'] != fingerprint:
        raise VerdugoError('Exact uncertain creation required; running actions remain blocked')
    req = json.loads(row['document'])
    pair = SUPPORTED.get(req.get('service'))
    if not pair or req.get('operation') != pair[0]:
        raise VerdugoError('Only supported contact creations can use readback')
    return row, req


def context(engine, req):
    sid = req['service']
    cfg = engine.preflight(sid, SUPPORTED[sid][1])
    if cfg.get('readback_reviewed') is not True:
        raise VerdugoError('Readback schema must be reviewed for this deployed instance')
    record_path = cfg.get('readback_record_path')
    if not isinstance(record_path, str) or not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){0,11}', record_path):
        raise VerdugoError('Explicit bounded readback_record_path required')
    origin = validate_origin(cfg)
    old = urlsplit(req['url'])
    if origin != old.scheme+'://'+old.netloc:
        raise VerdugoError('Readback origin differs from the uncertain creation')
    scope = str(cfg.get('account_id')) if sid == 'chatwoot' else identifier(cfg.get('workspace_id'))
    if digest({'origin': origin, 'workspace': scope}) != req.get('identity_scope'):
        raise VerdugoError('Readback account/workspace differs from the uncertain creation')
    if cfg.get('result_id_path') != req.get('result_id_path'):
        raise VerdugoError('Creation result contract changed; review separately')
    if sid == 'chatwoot' and cfg.get('inbox_id') != req['body']['inbox_id']:
        raise VerdugoError('Readback inbox differs from the uncertain creation')
    # v0.3 hashes all headers, including POST Content-Type. GET has no body.
    # Reconstruct the original write binding without changing historical fingerprints.
    _, _, headers = connection(sid, cfg)
    if digest(headers | {'Content-Type': 'application/json'}) != req.get('credential_binding'):
        raise VerdugoError('Readback credential differs from the original creation')
    return cfg, record_path


def matching(req, result, record_path, rid):
    record = extract(result, record_path)
    matches = {'id': remote_id(record, 'id') == rid}
    if req['service'] == 'twenty':
        matches.update(email=record.get('emails', {}).get('primaryEmail') == req['body']['emails']['primaryEmail'],
                       name=record.get('name') == req['body']['name'])
    else:
        matches.update(email=record.get('email') == req['body']['email'],
                       name=record.get('name') == req['body']['name'])
        inboxes = record.get('contact_inboxes')
        matches['inbox'] = isinstance(inboxes, list) and any(
            isinstance(v, dict) and isinstance(v.get('inbox'), dict) and
            type(v['inbox'].get('id')) is int and v['inbox']['id'] == req['body']['inbox_id'] for v in inboxes)
    return matches


def summary(row):
    return {'check_id': row['check_id'], 'source_key': row['source_key'], 'state': row['state'],
            'fingerprint': row['hash'], 'read_key': row['read_key'], 'observed_at': row['observed'],
            'outcome': json.loads(row['outcome']) if row['outcome'] else None,
            'source_write_retried': False, 'source_write_confirmed': False,
            'creation_proven': False, 'separate_approval_required': True}


def verify(engine, request, execute=False):
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    if execute and engine.role != 'operator': raise VerdugoError('Operator role required for readback')
    fields(request, ('key', 'fingerprint', 'remote_id', 'check_id'))
    cid, rid = identifier(request['check_id']), identifier(request['remote_id'])
    original, req = source(engine, request['key'], request['fingerprint'])
    _, path = context(engine, req)
    read_key = 'readback-'+digest(cid)[:40]
    command = {'service': req['service'], 'operation': SUPPORTED[req['service']][1],
               'params': {'remote_id': rid}, 'key': read_key}
    plan = engine.plan(command)
    for field in ('version', 'network_policy'):
        if plan['request'].get(field) != req.get(field):
            raise VerdugoError('Readback configuration/credential differs from the original plan')
    document = {'source_key': request['key'], 'source_hash': request['fingerprint'],
                'remote_id': rid, 'record_path': path, 'read_fingerprint': plan['fingerprint']}
    fingerprint = digest({'tenant': engine.tenant, 'check_id': cid, 'document': document})
    with engine.transaction():
        old = engine.db.execute('SELECT * FROM contact_readbacks WHERE tenant=? AND check_id=?',
                                (engine.tenant, cid)).fetchone()
        if old and old['hash'] != fingerprint: raise VerdugoError('Readback ID reused with changed input')
        engine.db.execute('INSERT OR IGNORE INTO contact_readbacks(tenant,check_id,source_key,source_hash,hash,document,read_key) '
                          'VALUES(?,?,?,?,?,?,?)', (engine.tenant, cid, request['key'], request['fingerprint'],
                          fingerprint, encode(document), read_key))
    if not execute:
        return {'state': 'planned', 'check_id': cid, 'fingerprint': fingerprint, 'read_plan': plan,
                'external_call_made': False, 'source_write_confirmed': False}
    if old and old['state'] != 'planned': return summary(old) | {'replayed': True}
    result = engine.execute(command, True)
    if result['state'] == 'running':
        # A concurrent reader owns this request. Do not freeze a temporary state
        # as final evidence; reusing this check later will observe its saved result.
        return {'state': 'pending', 'check_id': cid, 'fingerprint': fingerprint,
                'source_write_confirmed': False, 'source_write_retried': False}
    observed = engine.db.execute('SELECT finished FROM runs WHERE tenant=? AND key=?',
                                (engine.tenant, read_key)).fetchone()['finished']
    state, response_hash = 'unverified', None
    outcome = {'reason': 'read_not_succeeded', 'read_state': result['state']}
    if result['state'] == 'succeeded':
        response_hash = digest(result['result'])
        try:
            checks = matching(req, result['result'], path, rid)
            state = 'matched' if all(checks.values()) else 'mismatch'
            outcome = {'checks': checks, 'record_exists_and_matches': state == 'matched',
                       'creation_origin_proven': False}
        except (VerdugoError, AttributeError, TypeError):
            outcome = {'reason': 'response_schema_rejected'}
    with engine.transaction():
        source(engine, request['key'], request['fingerprint'])  # Reject concurrent resolution.
        # Never refresh the timestamp of a replayed read or overwrite a completed check.
        engine.db.execute("UPDATE contact_readbacks SET state=?,response_hash=?,observed=?,outcome=? "
            "WHERE tenant=? AND check_id=? AND state='planned'",
            (state, response_hash, observed, encode(outcome), engine.tenant, cid))
        engine.event(read_key, 'readback.observed', {'check_id': cid, 'state': state, 'response_hash': response_hash})
        row = engine.db.execute('SELECT * FROM contact_readbacks WHERE tenant=? AND check_id=?',
                                (engine.tenant, cid)).fetchone()
    return summary(row) | {'replayed': result.get('replayed', False)}


def confirmation_response(path, rid):
    """Minimal ID wrapper for existing identity binding; NOT the original POST response."""
    parts = path.split('.')
    value = rid
    for part in reversed(parts): value = {part: value}
    return value


def confirm(engine, evidence):
    if engine.role != 'approver': raise VerdugoError('Separate local approver role required')
    fields(evidence, ('check_id', 'fingerprint', 'evidence_ref'))
    cid, ref = identifier(evidence['check_id']), text(evidence['evidence_ref'], 500)
    with engine.transaction():
        check = engine.db.execute('SELECT * FROM contact_readbacks WHERE tenant=? AND check_id=?',
                                  (engine.tenant, cid)).fetchone()
        if not check or check['state'] != 'matched' or check['hash'] != evidence['fingerprint']:
            raise VerdugoError('Exact matched readback required')
        age = time.time() - check['observed']
        if not 0 <= age <= MAX_AGE: raise VerdugoError('Readback expired; perform a fresh check with a new check_id')
        document = json.loads(check['document'])
        original, req = source(engine, check['source_key'], check['source_hash'])
        cfg, path = context(engine, req)
        if path != document['record_path']: raise VerdugoError('Readback schema changed')
        command = {'service': req['service'], 'operation': SUPPORTED[req['service']][1],
                   'params': {'remote_id': document['remote_id']}, 'key': check['read_key']}
        prepared, _, fingerprint = engine.prepare(command)
        if fingerprint != document['read_fingerprint']:
            raise VerdugoError('Readback request changed after observation')
        for field in ('version', 'network_policy'):
            if prepared['public'].get(field) != req.get(field): raise VerdugoError('Original binding changed')
        read = engine.db.execute('SELECT * FROM runs WHERE tenant=? AND key=?',
                                 (engine.tenant, check['read_key'])).fetchone()
        if (not read or read['state'] != 'succeeded' or read['hash'] != fingerprint or
            read['started'] < original['finished'] or read['finished'] != check['observed'] or
            digest(json.loads(read['result'])) != check['response_hash']):
            raise VerdugoError('Persisted readback evidence no longer matches')
        if not all(matching(req, json.loads(read['result']), path, document['remote_id']).values()):
            raise VerdugoError('Persisted contact does not match the original plan')
        alias = engine.db.execute('SELECT source_key FROM identities WHERE tenant=? AND service=? AND scope=? AND remote_id=?',
            (engine.tenant, req['service'], req['identity_scope'], document['remote_id'])).fetchone()
        if alias and alias['source_key'] != check['source_key']:
            raise VerdugoError('Remote contact already bound to another creation')
        response = confirmation_response(req['result_id_path'], document['remote_id'])
        ref = sanitize(ref, prepared['secret_values'])
        engine.db.execute('INSERT INTO reconciliations VALUES(?,?,?,?,?,?,?)',
            (engine.tenant, check['source_key'], check['source_hash'], engine.actor, ref, digest(response), time.time()))
        engine.finish(check['source_key'], 'succeeded', response)
        engine.event(check['source_key'], 'action.reconciled_with_readback', {
            'actor': engine.actor, 'check_id': cid, 'read_key': check['read_key'], 'evidence_ref': ref,
            'read_response_hash': check['response_hash'], 'reconstructed_result': True,
            'basis': 'provider_readback_plus_human_review', 'creation_proven': False})
    return {'state': 'succeeded', 'key': check['source_key'], 'check_id': cid,
            'basis': 'provider_readback_plus_human_review', 'creation_proven': False,
            'source_write_retried': False, 'external_call_made': False}
