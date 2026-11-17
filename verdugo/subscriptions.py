"""Per-client service switch.

A client tenant keeps service only while its paid period is current. Each client
is a tenant of the operator configuration. Tenants without a subscription record
are the operator's own and are never switched off.

Payments are declared by the operator. Verdugo does not verify bank receipts and
does not use any payment provider. Changes are previewed by default, require the
operator role and are written to the audit trail.
"""
from datetime import date, datetime, timedelta, timezone
import calendar
import re
import time

from .common import VerdugoError, integer, text

SCHEMA = '''
CREATE TABLE IF NOT EXISTS subscriptions (
 tenant TEXT PRIMARY KEY, label TEXT NOT NULL, paid_until TEXT,
 grace_days INTEGER NOT NULL DEFAULT 0, paused INTEGER NOT NULL DEFAULT 0,
 pause_reason TEXT, updated_at REAL NOT NULL, updated_by TEXT NOT NULL);
'''

MAX_GRACE_DAYS = 31
MAX_MONTHS = 24
BILLING_TZ = 'America/Mexico_City'


def today():
    """Current calendar day in Mexico City (UTC-6, no daylight saving since 2022)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(BILLING_TZ)).date()
    except Exception:
        return datetime.now(timezone(timedelta(hours=-6))).date()


def _parse_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise VerdugoError('Date must be YYYY-MM-DD')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise VerdugoError('Date must be YYYY-MM-DD') from None


def add_months(day, months):
    integer(months, 1, MAX_MONTHS)
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _row(engine):
    return engine.db.execute('SELECT * FROM subscriptions WHERE tenant=?', (engine.tenant,)).fetchone()


def _describe(tenant, row, now):
    if row is None:
        return {'tenant': tenant, 'managed': False, 'active': True, 'state': 'unmanaged',
                'reason': 'Tenant propio del operador: no tiene interruptor de pago.'}
    paid_until = row['paid_until']
    out = {'tenant': tenant, 'managed': True, 'label': row['label'], 'paid_until': paid_until,
           'grace_days': row['grace_days'], 'paused': bool(row['paused']),
           'verification': 'operator_declared', 'checked_on': now.isoformat()}
    if row['paused']:
        return out | {'active': False, 'state': 'suspended', 'reason': 'pausado',
                      'pause_reason': row['pause_reason']}
    if paid_until is None:
        return out | {'active': False, 'state': 'suspended', 'reason': 'sin_pago'}
    service_until = date.fromisoformat(paid_until) + timedelta(days=row['grace_days'])
    days_left = (service_until - now).days
    if days_left < 0:
        return out | {'active': False, 'state': 'suspended', 'reason': 'pago_vencido',
                      'service_until': service_until.isoformat(), 'days_left': days_left}
    return out | {'active': True, 'state': 'active', 'service_until': service_until.isoformat(),
                  'days_left': days_left}


def state(engine, now=None):
    row = _row(engine)
    required = engine.config.get('tenants', {}).get(engine.tenant, {}).get('subscription_required', False)
    if row is None and required:
        return {'tenant': engine.tenant, 'managed': False, 'active': False,
                'state': 'suspended', 'reason': 'registro_pendiente'}
    return _describe(engine.tenant, row, now or today())


def check(engine, now=None):
    current = state(engine, now)
    if not current['active']:
        raise VerdugoError('Servicio apagado para este cliente (%s): registra su pago para reactivarlo'
                           % current['reason'])
    return current


def _require_operator(engine):
    if engine.role != 'operator':
        raise VerdugoError('Operator role required to change a client switch')


def _apply(engine, change, execute, write):
    if type(execute) is not bool:
        raise VerdugoError('execute must be a boolean')
    if not execute:
        return {'state': 'planned', 'tenant': engine.tenant, 'change': change,
                'note': 'Vista previa: agrega --execute para aplicarlo.'}
    _require_operator(engine)
    with engine.transaction():
        write()
        engine.event('subscription', 'subscription.' + change['action'],
                     {k: v for k, v in change.items() if k != 'action'} | {'actor': engine.actor})
    return {'state': 'applied', 'change': change, 'subscription': state(engine)}


def register(engine, label, grace_days=0, execute=False):
    label = text(label, 120)
    integer(grace_days, 0, MAX_GRACE_DAYS)
    if _row(engine) is not None:
        raise VerdugoError('Client switch already exists for this tenant')

    def write():
        engine.db.execute('INSERT INTO subscriptions(tenant,label,paid_until,grace_days,paused,updated_at,updated_by) '
                          'VALUES(?,?,NULL,?,0,?,?)', (engine.tenant, label, grace_days, time.time(), engine.actor))
    return _apply(engine, {'action': 'registered', 'label': label, 'grace_days': grace_days,
                           'starts': 'suspended_until_first_payment'}, execute, write)


def pay(engine, until=None, months=None, execute=False, now=None):
    row = _row(engine)
    if row is None:
        raise VerdugoError('Register the client switch first')
    if (until is None) == (months is None):
        raise VerdugoError('Give exactly one of until (YYYY-MM-DD) or months')
    now = now or today()
    if until is not None:
        new = _parse_day(until)
    else:
        current = date.fromisoformat(row['paid_until']) if row['paid_until'] else None
        base = current if current and current >= now else now
        new = add_months(base, months)
    if new < now:
        raise VerdugoError('Paid-until date cannot be in the past')
    if (new - now).days > MAX_MONTHS * 31:
        raise VerdugoError('Paid-until date is too far in the future')

    def write():
        engine.db.execute('UPDATE subscriptions SET paid_until=?,updated_at=?,updated_by=? WHERE tenant=?',
                          (new.isoformat(), time.time(), engine.actor, engine.tenant))
    return _apply(engine, {'action': 'paid', 'previous_paid_until': row['paid_until'],
                           'paid_until': new.isoformat(), 'verification': 'operator_declared'}, execute, write)


def pause(engine, reason, execute=False):
    reason = text(reason, 200)
    if _row(engine) is None:
        raise VerdugoError('Register the client switch first')

    def write():
        engine.db.execute('UPDATE subscriptions SET paused=1,pause_reason=?,updated_at=?,updated_by=? WHERE tenant=?',
                          (reason, time.time(), engine.actor, engine.tenant))
    return _apply(engine, {'action': 'paused', 'reason': reason}, execute, write)


def resume(engine, execute=False):
    if _row(engine) is None:
        raise VerdugoError('Register the client switch first')

    def write():
        engine.db.execute('UPDATE subscriptions SET paused=0,pause_reason=NULL,updated_at=?,updated_by=? WHERE tenant=?',
                          (time.time(), engine.actor, engine.tenant))
    return _apply(engine, {'action': 'resumed'}, execute, write)


def listing(engine, now=None):
    if engine.role not in ('operator', 'viewer'):
        raise VerdugoError('Operator or viewer role required')
    now = now or today()
    rows = engine.db.execute('SELECT * FROM subscriptions ORDER BY tenant').fetchall()
    clients = [_describe(r['tenant'], r, now) for r in rows]
    return {'state': 'observed_local', 'checked_on': now.isoformat(), 'clients': clients,
            'active': sum(c['active'] for c in clients), 'suspended': sum(not c['active'] for c in clients),
            'verification': 'operator_declared',
            'note': 'Pagos declarados por el operador; Verdugo no verifica depósitos bancarios.'}
