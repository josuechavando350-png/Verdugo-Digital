"""Tenant-scoped durable inbox/jobs. At-least-once delivery, never exactly-once claims."""
import json
import secrets
import time
from .common import VerdugoError, digest, encode, fields, identifier, integer
from .bridge import contact_bridge

SCHEMA = '''
CREATE TABLE IF NOT EXISTS inbox (
 tenant TEXT NOT NULL, source TEXT NOT NULL, event_id TEXT NOT NULL,
 body_hash TEXT NOT NULL, job_id TEXT NOT NULL, received REAL NOT NULL,
 PRIMARY KEY(tenant,source,event_id));
CREATE TABLE IF NOT EXISTS jobs (
 tenant TEXT NOT NULL, id TEXT NOT NULL, source TEXT NOT NULL,
 route_hash TEXT NOT NULL, handler TEXT NOT NULL, payload TEXT NOT NULL,
 state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
 available REAL NOT NULL, lease TEXT, lease_until REAL, outcome TEXT,
 created REAL NOT NULL, updated REAL NOT NULL, PRIMARY KEY(tenant,id));
CREATE INDEX IF NOT EXISTS jobs_due ON jobs(tenant,state,available);
'''
HANDLERS = ('lead.capture', 'contact.bridge')



def route(engine, source):
    identifier(source)
    sources = engine.config['tenants'][engine.tenant].get('ingress', {})
    if not isinstance(sources, dict): raise VerdugoError('Invalid ingress configuration')
    cfg = sources.get(source)
    if not isinstance(cfg, dict): raise VerdugoError('Unknown event source')
    fields(cfg, ('enabled', 'secret_env', 'handler', 'dataset'), ('max_pending', 'max_attempts'))
    if cfg['enabled'] is not True: raise VerdugoError('Event source disabled')
    if cfg['handler'] not in HANDLERS or cfg['dataset'] not in ('demo', 'real'):
        raise VerdugoError('Invalid event route')
    integer(cfg.get('max_pending', 100), 1, 10000)
    integer(cfg.get('max_attempts', 3), 1, 10)
    return cfg


def route_hash(cfg):
    # Secret rotation is allowed. Changing the business route requires operator review.
    return digest({k: cfg[k] for k in ('handler', 'dataset')})


def require_operator(engine):
    if engine.role != 'operator': raise VerdugoError('Operator role required')


def view(row):
    if not row: raise VerdugoError('Job not found in this tenant')
    return {k: row[k] for k in ('id', 'source', 'handler', 'state', 'attempts',
            'max_attempts', 'available', 'lease_until', 'created', 'updated')} | {
            'outcome': json.loads(row['outcome']) if row['outcome'] else None}


def get(engine, job_id):
    identifier(job_id)
    return view(engine.db.execute('SELECT * FROM jobs WHERE tenant=? AND id=?',
                                (engine.tenant, job_id)).fetchone())


def overview(engine, limit=50):
    integer(limit, 1, 200)
    counts = {r['state']: r['n'] for r in engine.db.execute(
        'SELECT state,COUNT(*) n FROM jobs WHERE tenant=? GROUP BY state', (engine.tenant,))}
    rows = engine.db.execute('SELECT * FROM jobs WHERE tenant=? ORDER BY created,id LIMIT ?',
                             (engine.tenant, limit)).fetchall()
    return {'tenant': engine.tenant, 'counts': counts, 'jobs': [view(r) for r in rows],
            'truncated': sum(counts.values()) > len(rows), 'external_calls_made': False}


def dispatch(engine, job, execute):
    cfg = route(engine, job['source'])
    if route_hash(cfg) != job['route_hash']: raise VerdugoError('Queued route changed')
    payload = json.loads(job['payload'])
    if job['handler'] == 'contact.bridge': return contact_bridge(engine, payload, execute)
    if job['handler'] != 'lead.capture': raise VerdugoError('Unsupported queued handler')
    params = {'lead_id': payload['lead_id'], 'name': (payload['first_name']+' '+payload.get('last_name', '')).strip(),
              'email': payload['email'], 'dataset': payload['dataset']}
    # Resource key, not delivery ID: different events for one profile cannot duplicate it.
    key = 'ingest-' + digest([engine.tenant, params['lead_id'], params['dataset']])[:40]
    return engine.execute({'service': 'core', 'operation': 'lead.capture',
                           'params': params, 'key': key}, execute)


def plan(engine, job_id):
    identifier(job_id)
    row = engine.db.execute('SELECT * FROM jobs WHERE tenant=? AND id=?',
                            (engine.tenant, job_id)).fetchone()
    if not row: raise VerdugoError('Job not found in this tenant')
    return {'job_id': job_id, 'plan': dispatch(engine, row, False)}


def claim(engine, lease_seconds=300):
    require_operator(engine)
    integer(lease_seconds, 30, 3600)
    now = time.time()
    with engine.transaction():
        expired = engine.db.execute("SELECT id,attempts,max_attempts FROM jobs WHERE tenant=? "
                  "AND state='leased' AND lease_until<=?", (engine.tenant, now)).fetchall()
        for row in expired:
            state = 'dead' if row['attempts'] >= row['max_attempts'] else 'pending'
            engine.db.execute('UPDATE jobs SET state=?,lease=NULL,lease_until=NULL,available=?,updated=? '
                              'WHERE tenant=? AND id=?', (state, now, now, engine.tenant, row['id']))
            engine.event(row['id'], 'job.lease_expired', {'state': state})
        row = engine.db.execute("SELECT * FROM jobs WHERE tenant=? AND state='pending' AND available<=? "
                                 'ORDER BY available,created,id LIMIT 1', (engine.tenant, now)).fetchone()
        if not row: return None
        token = secrets.token_hex(24)
        engine.db.execute("UPDATE jobs SET state='leased',attempts=attempts+1,lease=?,lease_until=?,updated=? "
                          'WHERE tenant=? AND id=?', (token, now+lease_seconds, now, engine.tenant, row['id']))
        engine.event(row['id'], 'job.claimed', {'attempt': row['attempts']+1, 'actor': engine.actor})
        return dict(row) | {'lease': token, 'attempts': row['attempts']+1}


def settle(engine, job, state, outcome, delay=0):
    require_operator(engine)
    if state not in ('pending', 'succeeded', 'blocked', 'dead'): raise VerdugoError('Invalid job transition')
    integer(delay, 0, 3600)
    now = time.time()
    with engine.transaction():
        cur = engine.db.execute('UPDATE jobs SET state=?,outcome=?,available=?,lease=NULL,lease_until=NULL,updated=? '
            "WHERE tenant=? AND id=? AND state='leased' AND lease=? AND lease_until>?",
            (state, encode(outcome), now+delay, now, engine.tenant, job['id'], job['lease'], now))
        if cur.rowcount != 1: raise VerdugoError('Worker lease lost; stale completion rejected')
        engine.event(job['id'], 'job.'+state, {'outcome': outcome})
    return get(engine, job['id'])


def work(engine, execute=False):
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    if not execute: return {'state': 'planned', 'queue': overview(engine), 'external_calls_made': False}
    require_operator(engine)
    job = claim(engine)
    if not job: return {'state': 'idle', 'external_calls_made': False}
    delay = 0
    try:
        result = dispatch(engine, job, True)
        status = result.get('state')
        if status == 'succeeded':
            state, outcome = 'succeeded', {'state': status, 'result_digest': digest(result)}
        else:
            state = 'blocked'
            outcome = {'state': status, 'reason': result.get('outcome', {}).get('state', status),
                       'step': result.get('step'), 'operator_review_required': True}
    except VerdugoError:
        state, outcome = 'blocked', {'reason': 'configuration_or_contract', 'operator_review_required': True}
    except Exception as exc:
        # Retry the SAME workflow keys, never reset runs or approvals. Messages may contain secrets.
        state = 'dead' if job['attempts'] >= job['max_attempts'] else 'pending'
        delay = min(300, 5 * 2 ** (job['attempts']-1)) if state == 'pending' else 0
        outcome = {'reason': 'worker_error', 'error_type': type(exc).__name__}
    # A failed acknowledgement must not be interpreted as another dispatch failure.
    return settle(engine, job, state, outcome, delay)


def resume(engine, job_id):
    require_operator(engine)
    identifier(job_id)
    with engine.transaction():
        row = engine.db.execute('SELECT * FROM jobs WHERE tenant=? AND id=?',
                                (engine.tenant, job_id)).fetchone()
        if not row or row['state'] not in ('blocked', 'dead'):
            raise VerdugoError('Only blocked/dead jobs can be manually resumed')
        if row['attempts'] >= row['max_attempts']:
            raise VerdugoError('Attempt budget exhausted; no automatic reset or new action keys')
        cfg = route(engine, row['source'])
        if route_hash(cfg) != row['route_hash']: raise VerdugoError('Queued route changed')
        engine.db.execute("UPDATE jobs SET state='pending',available=?,updated=? WHERE tenant=? AND id=?",
                          (time.time(), time.time(), engine.tenant, job_id))
        engine.event(job_id, 'job.resumed', {'actor': engine.actor, 'approvals_unchanged': True})
    return get(engine, job_id)
