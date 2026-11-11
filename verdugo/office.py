"""Termux-friendly first-party sales intake and a compact read-only workday.

No provider calls, messages, ad purchases or bank reconciliation. The operator
explicitly declares data; none of this demonstrates commercial success.
"""
from datetime import date
from . import commercial, jobs, reconciliation
from .common import VerdugoError, digest, fields, identifier, text, encode

SCHEMA = '''
CREATE TABLE IF NOT EXISTS sales_intakes (
 tenant TEXT NOT NULL, lead_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
 PRIMARY KEY(tenant, lead_id));
'''


def _prepare(engine, data):
    fields(data, ('lead_id', 'name', 'email', 'dataset', 'channel', 'evidence_ref'),
           ('followup_due',))
    lid = identifier(data['lead_id'])
    lead = {k: data[k] for k in ('lead_id', 'name', 'email', 'dataset')}
    engine.validate_core('lead.capture', lead)
    channel = data['channel']
    if not isinstance(channel, str) or channel not in commercial.CHANNELS:
        raise VerdugoError('Unsupported acquisition channel')
    ref = data['evidence_ref']
    if not isinstance(ref, str) or not commercial.EVIDENCE.fullmatch(ref):
        raise VerdugoError('Private evidence ID required; never include email or URL')
    due = data.get('followup_due')
    if due is not None:
        if not isinstance(due, str) or not commercial.DUE.fullmatch(due):
            raise VerdugoError('Followup date must be YYYY-MM-DD in UTC')
        try: date.fromisoformat(due)
        except ValueError as exc: raise VerdugoError('Invalid followup date') from exc
    identified = {'event_id': 'identified-'+digest([engine.tenant,lid])[:35],
                  'lead_id': lid, 'channel': channel,
                  'kind': 'identified', 'evidence_ref': ref}
    planned = [identified]
    if due is not None:
        planned.append({'event_id': 'due-'+digest([engine.tenant,lid])[:35],
                        'lead_id': lid, 'channel': channel,
                        'kind': 'followup_due', 'followup_due': due,
                        'evidence_ref': ref})
    fingerprint = digest({'tenant': engine.tenant, 'lead': lead, 'events': planned})
    return lead, planned, fingerprint


def intake(engine, data, execute=False):
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    lead, entries, fingerprint = _prepare(engine, data)
    if not execute:
        return {'state':'planned', 'tenant':engine.tenant,
                'lead_id':lead['lead_id'], 'dataset':lead['dataset'],
                'events': [e['kind'] for e in entries],
                'requires_operator':True, 'external_calls_made':False}
    if engine.role != 'operator': raise VerdugoError('Operator role required for local intake')
    with engine.transaction():
        row = engine.db.execute('SELECT fingerprint FROM sales_intakes WHERE tenant=? AND lead_id=?',
                                (engine.tenant, lead['lead_id'])).fetchone()
        if row and row['fingerprint'] != fingerprint:
            raise VerdugoError('Intake already exists with different data; use a distinct followup event')
        if row:
            return {'state':'recorded', 'tenant':engine.tenant,
                    'lead_id':lead['lead_id'], 'dataset':lead['dataset'],
                    'events': [e['kind'] for e in entries], 'replayed':True,
                    'external_calls_made':False, 'bank_reconciled':False}
        # All local operations are in one SQLite transaction. An invalid stage,
        # duplicate ID, audit failure or channel conflict rolls back capture too.
        engine.core('lead.capture', lead)
        for entry in entries:
            validated = commercial.validate(engine, entry)
            commercial.persist_in_transaction(engine, validated)
        engine.db.execute('INSERT INTO sales_intakes VALUES(?,?,?)',
                          (engine.tenant, lead['lead_id'], fingerprint))
        engine.event(lead['lead_id'], 'sales.intake_completed', {
            'lead_id':lead['lead_id'], 'dataset':lead['dataset'],
            'commercial_stages': [e['kind'] for e in entries]})
    return {'state':'recorded', 'tenant':engine.tenant,
            'lead_id':lead['lead_id'], 'dataset':lead['dataset'],
            'events': [e['kind'] for e in entries], 'replayed':False,
            'external_calls_made':False, 'bank_reconciled':False}


def desk(engine, params=None):
    if params is None: params = {'dataset':'real'}
    fields(params, ('dataset',), ('goal_min','goal_target','limit'))
    dataset = params['dataset']
    report = commercial.report(engine, {'dataset':dataset,
        'goal_min':params.get('goal_min',6),
        'goal_target':params.get('goal_target',10), 'window_days':30})
    followups = commercial.next_actions(engine, {'dataset': dataset,
                                                 'limit': params.get('limit',20)})
    queued = jobs.overview(engine,1)
    unresolved = reconciliation.pending(engine)
    status = engine.status()
    return {'state':'observed_local', 'tenant':engine.tenant, 'dataset':dataset,
            'sales': report, 'followups': followups,
            'jobs_by_state':queued['counts'],
            'reconciliation_required': len(unresolved['items']),
            'reconciliation_list_truncated': len(unresolved['items'])==unresolved['limit'],
            'adapters_implemented':status['api_adapters_implemented'],
            'live_verified':status['live_verified'],
            'outbound_actions_sent':0, 'external_calls_made':False,
            'payment_reconciliation_available':False,
            'note':'Operator-declared local data only. No provider, bank or commercial-success certification.'}
