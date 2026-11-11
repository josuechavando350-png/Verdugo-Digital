"""Local commercial ledger for a 30-day sales objective.

Operator assertions are NOT verified customer outcomes. No messaging, ad spend,
external calls, or bank verification. CLI/MCP use the same tenant-scoped Engine.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import json
import re
import time
from .common import VerdugoError, fields, identifier, integer

SCHEMA = '''
CREATE TABLE IF NOT EXISTS commercial_events (
 tenant TEXT NOT NULL, event_id TEXT NOT NULL, lead_id TEXT NOT NULL,
 dataset TEXT NOT NULL, kind TEXT NOT NULL, channel TEXT NOT NULL,
 evidence_ref TEXT NOT NULL, payment_id TEXT, followup_due TEXT,
 created REAL NOT NULL, PRIMARY KEY(tenant,event_id));
CREATE INDEX IF NOT EXISTS commercial_lead ON commercial_events(tenant,lead_id,created);
CREATE INDEX IF NOT EXISTS commercial_window ON commercial_events(tenant,dataset,created);
'''
KINDS = frozenset(('contacted', 'meeting_booked', 'meeting_held',
                   'proposal_sent', 'followup_due', 'won', 'lost'))
CHANNELS = frozenset(('referral', 'partner', 'outbound', 'organic', 'paid', 'other'))
EVIDENCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{2,119}\Z')
DUE = re.compile(r'\d{4}-\d{2}-\d{2}\Z')


def validate(engine, item):
    fields(item, ('event_id', 'lead_id', 'kind', 'channel', 'evidence_ref'),
           ('payment_id', 'followup_due'))
    identifier(item['event_id'])
    identifier(item['lead_id'])
    if not isinstance(item['kind'], str) or item['kind'] not in KINDS:
        raise VerdugoError('Unknown commercial event kind')
    if not isinstance(item['channel'], str) or item['channel'] not in CHANNELS:
        raise VerdugoError('Unknown commercial channel')
    if not isinstance(item['evidence_ref'], str) or not EVIDENCE.fullmatch(item['evidence_ref']):
        raise VerdugoError('Provide a bounded, private evidence identifier; no URLs, email, or secrets')
    lead = engine.record('lead', item['lead_id'])
    if not lead or lead.get('dataset') not in ('demo', 'real'):
        raise VerdugoError('Existing tenant lead with an explicit dataset required')
    due = item.get('followup_due')
    if item['kind'] == 'followup_due':
        if not isinstance(due, str) or not DUE.fullmatch(due):
            raise VerdugoError('followup_due needs an exact UTC YYYY-MM-DD date')
        try: date.fromisoformat(due)
        except ValueError as exc: raise VerdugoError('Invalid calendar date') from exc
    elif due is not None:
        raise VerdugoError('Only followup_due events may contain a due date')
    pid = item.get('payment_id')
    if item['kind'] == 'won':
        if not isinstance(pid, str): raise VerdugoError('Won requires payment_id')
        identifier(pid)
        payment = engine.record('payment', pid)
        if not payment or payment['lead_id'] != item['lead_id'] or payment['dataset'] != lead['dataset']:
            raise VerdugoError('Matching tenant/dataset payment declaration required to report a win')
    elif pid is not None:
        raise VerdugoError('Payment references are only accepted for won')
    # Store a stable canonical representation, not event time provided by clients.
    return {'event_id': item['event_id'], 'lead_id': item['lead_id'],
            'dataset': lead['dataset'], 'kind': item['kind'],
            'channel': item['channel'], 'evidence_ref': item['evidence_ref'],
            'payment_id': pid, 'followup_due': due}


def record(engine, item, execute=False):
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    normalized = validate(engine, item)
    if not execute:
        return {'state': 'planned', 'event_id': normalized['event_id'],
                'dataset': normalized['dataset'], 'requires_operator': True,
                'external_call_made': False, 'bank_reconciled': False}
    if engine.role != 'operator': raise VerdugoError('Operator role required')
    with engine.transaction():
        old = engine.db.execute('SELECT * FROM commercial_events WHERE tenant=? AND event_id=?',
                                (engine.tenant, normalized['event_id'])).fetchone()
        if old:
            if any(old[k] != v for k, v in normalized.items()):
                raise VerdugoError('Commercial event ID reused with different facts')
            return {'state': 'recorded', 'event_id': normalized['event_id'],
                    'replayed': True, 'dataset': normalized['dataset'],
                    'bank_reconciled': False, 'external_call_made': False}
        previous = engine.db.execute('SELECT kind,channel FROM commercial_events WHERE tenant=? AND lead_id=?',
                                     (engine.tenant, normalized['lead_id'])).fetchall()
        if previous and any(p['channel'] != normalized['channel'] for p in previous):
            raise VerdugoError('Channel is immutable for this lead; do not relabel attribution')
        if any(p['kind'] in ('won', 'lost') for p in previous):
            raise VerdugoError('A closed lead cannot receive more commercial events')
        if normalized['kind'] == 'won':
            prior = engine.db.execute("SELECT lead_id FROM commercial_events WHERE tenant=? AND payment_id=?",
                                      (engine.tenant, normalized['payment_id'])).fetchone()
            if prior: raise VerdugoError('Payment declaration already attributed to another event')
        engine.db.execute('INSERT INTO commercial_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                          (engine.tenant, *(normalized[k] for k in ('event_id', 'lead_id', 'dataset',
                            'kind', 'channel', 'evidence_ref', 'payment_id', 'followup_due')),
                           time.time()))
        engine.event(normalized['event_id'], 'commercial.recorded', {
            'lead_id': normalized['lead_id'], 'dataset': normalized['dataset'],
            'kind': normalized['kind'], 'channel': normalized['channel'],
            'bank_reconciled': False})
    return {'state': 'recorded', 'event_id': normalized['event_id'], 'replayed': False,
            'dataset': normalized['dataset'], 'bank_reconciled': False,
            'external_call_made': False}


def _events(engine, dataset):
    if dataset not in ('demo', 'real'): raise VerdugoError('dataset must be demo or real')
    return engine.db.execute('SELECT * FROM commercial_events WHERE tenant=? AND dataset=? '
                             'ORDER BY created,event_id', (engine.tenant, dataset)).fetchall()


def _stats(engine, dataset, window_days):
    integer(window_days, 1, 365)
    now = time.time()
    cutoff = now - window_days * 86400
    rows = _events(engine, dataset)
    current = [r for r in rows if cutoff <= r['created'] <= now]
    events_by_kind = {kind: len({r['lead_id'] for r in current if r['kind'] == kind})
                      for kind in sorted(KINDS)}
    won_rows = [r for r in current if r['kind'] == 'won']
    by_channel = Counter(r['channel'] for r in won_rows)
    money = defaultdict(int)
    for row in won_rows:
        payment = engine.record('payment', row['payment_id'])
        if payment and payment['lead_id'] == row['lead_id'] and payment['dataset'] == dataset:
            money[payment['currency']] += payment['amount_minor']
        else:
            raise VerdugoError('Commercial ledger lost linked payment evidence')
    return {'now': now, 'cutoff': cutoff, 'rows': rows, 'current': current,
            'stage_leads': events_by_kind, 'won_rows': won_rows,
            'by_channel': dict(sorted(by_channel.items())),
            'reported_receipts_by_currency_minor': dict(sorted(money.items()))}


def report(engine, params=None):
    params = {'dataset': 'real', 'window_days': 30, 'goal_min': 6, 'goal_target': 10} if params is None else params
    fields(params, ('dataset',), ('window_days', 'goal_min', 'goal_target'))
    goal_min = integer(params.get('goal_min', 6), 1, 10000)
    goal_target = integer(params.get('goal_target', 10), goal_min, 10000)
    window_days = integer(params.get('window_days', 30), 1, 365)
    stats = _stats(engine, params['dataset'], window_days)
    wins = len({r['lead_id'] for r in stats['won_rows']})
    def utc(seconds):
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    return {'state': 'observed_local', 'tenant': engine.tenant, 'dataset': params['dataset'],
            'window_start_utc': utc(stats['cutoff']), 'window_end_utc': utc(stats['now']),
            'window_days': window_days, 'tracked_leads_in_window': len({r['lead_id'] for r in stats['current']}),
            'stage_leads': stats['stage_leads'], 'reported_paid_clients': wins,
            'reported_paid_by_channel': stats['by_channel'],
            'reported_receipts_by_currency_minor': stats['reported_receipts_by_currency_minor'],
            'goal_min': goal_min, 'goal_target': goal_target,
            'gap_to_min': max(0, goal_min-wins), 'gap_to_target': max(0, goal_target-wins),
            'bank_reconciled': False, 'commercial_success_probability': None,
            'measurement_basis': 'operator-declared events plus local payment declarations; not audited bank receipts',
            'external_call_made': False}


def next_actions(engine, params=None):
    params = {'dataset': 'real', 'limit': 50} if params is None else params
    fields(params, ('dataset',), ('limit',))
    dataset, limit = params['dataset'], integer(params.get('limit', 50), 1, 200)
    rows = _events(engine, dataset)
    by_lead = defaultdict(list)
    for r in rows: by_lead[r['lead_id']].append(r)
    lead_ids = {r['id'] for r in engine.db.execute("SELECT id FROM records WHERE tenant=? AND kind='lead' AND dataset=?",
                                                   (engine.tenant, dataset))}
    today = datetime.now(timezone.utc).date().isoformat()
    items = []
    for lid in lead_ids:
        history = by_lead.get(lid, [])
        if any(r['kind'] in ('won', 'lost') for r in history): continue
        last = history[-1] if history else None
        due = next((r['followup_due'] for r in reversed(history) if r['kind'] == 'followup_due'), None)
        stage = next((r['kind'] for r in reversed(history) if r['kind'] != 'followup_due'), 'untracked')
        items.append({'lead_id': lid, 'channel': last['channel'] if last else None,
                      'last_stage': stage, 'followup_due_utc_date': due,
                      'overdue': due is not None and due < today,
                      'has_scheduled_followup': due is not None,
                      'last_recorded_at': last['created'] if last else None})
    # Highest priority: overdue, then untracked, scheduled and unscheduled.
    items.sort(key=lambda x: (0 if x['overdue'] else 1 if x['last_stage'] == 'untracked' else 2 if x['has_scheduled_followup'] else 3,
                              x['followup_due_utc_date'] or '9999-12-31',
                              x['last_recorded_at'] or 0, x['lead_id']))
    return {'state': 'observed_local', 'tenant': engine.tenant, 'dataset': dataset,
            'active_leads': len(items), 'overdue_followups': sum(x['overdue'] for x in items),
            'untracked_leads': sum(x['last_stage'] == 'untracked' for x in items),
            'items': items[:limit], 'truncated': len(items) > limit,
            'contacts_sent': 0, 'external_call_made': False,
            'note': 'No emails, calls or calendar events are sent; this is a local review queue.'}
