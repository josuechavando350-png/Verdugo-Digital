"""Single control plane: persistent runs, tenant scoping, exact-action approvals."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import re
import sqlite3
import stat
import time
from .adapters import SPECS, build, service_config, connection, remote_id
from . import read_contracts
from .catalog import catalog
from .source_evidence import read_sources
from . import license_policy
from . import local_runtime
from .common import VerdugoError, digest, encode, fields, identifier, integer, sanitize, text
from .transport import send
from . import identity, jobs, reconciliation, readback, commercial, pilot, office
from .guards import StateGuards, GuardBusy, SCHEMA as GUARD_SCHEMA

CORE = {'lead.capture', 'lead.qualify', 'payment.record', 'metrics.summary'} | identity.ACTIONS
SCHEMA = '''
CREATE TABLE IF NOT EXISTS plans (
 tenant TEXT, key TEXT, hash TEXT NOT NULL, document TEXT NOT NULL,
 approved_by TEXT, expires REAL, used INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(tenant,key));
CREATE TABLE IF NOT EXISTS runs (
 tenant TEXT, key TEXT, hash TEXT NOT NULL, state TEXT NOT NULL,
 result TEXT, started REAL NOT NULL, finished REAL, PRIMARY KEY(tenant,key));
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL,
 key TEXT NOT NULL, kind TEXT NOT NULL, details TEXT NOT NULL, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS records (
 tenant TEXT, kind TEXT, id TEXT, dataset TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(tenant,kind,id));
CREATE INDEX IF NOT EXISTS events_tenant_id ON events(tenant,id);
'''


class Engine:
    def __init__(self, state, config=None, tenant='nexus', actor='local-operator',
                 role='operator', transport=send):
        self.tenant, self.actor = identifier(tenant), identifier(actor)
        if role not in ('viewer', 'operator', 'approver'):
            raise VerdugoError('Invalid role')
        self.role = role
        self.config = config if config is not None else {'tenants': {'nexus': {'services': {}}}}
        if not isinstance(self.config, dict) or not isinstance(self.config.get('tenants'), dict):
            raise VerdugoError('Configuration must contain a tenants object')
        if tenant not in self.config.get('tenants', {}):
            raise VerdugoError('Tenant is not provisioned in the operator configuration')
        tenant_cfg = self.config['tenants'][tenant]
        if not isinstance(tenant_cfg, dict) or not isinstance(tenant_cfg.get('services', {}), dict):
            raise VerdugoError('Tenant configuration requires a services object')
        if any(not isinstance(v, dict) for v in tenant_cfg.get('services', {}).values()):
            raise VerdugoError('Each service configuration must be an object')
        self.transport = transport
        self.state_path = ':memory:' if str(state) == ':memory:' else str(Path(state).resolve())
        if self.state_path != ':memory:':
            p = Path(self.state_path)
            p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            parent = p.parent.stat()
            if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
                raise VerdugoError('State requires an owner-only local directory (mode 0700)')
            if p.exists():
                info = p.stat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise VerdugoError('State must be a regular single-link local file')
        # Let SQLite manage its own file descriptors. A separate open()/close()
        # of an already-open database can cancel POSIX locks of other connections.
        self.db = sqlite3.connect(self.state_path, isolation_level=None, timeout=10)
        try:
            if self.state_path != ':memory:': os.chmod(self.state_path, 0o600)
            self.guards = StateGuards(self.state_path)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA foreign_keys=ON')
            self.db.executescript(SCHEMA + identity.SCHEMA + jobs.SCHEMA + reconciliation.SCHEMA + GUARD_SCHEMA + readback.SCHEMA + commercial.SCHEMA + pilot.SCHEMA + office.SCHEMA)
        except BaseException:
            # sqlite3.connect() succeeded, but schema/PRAGMA/bootstrap failed.
            # Context managers alone do not close sqlite3.Connection objects.
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def event(self, key, kind, details):
        self.db.execute('INSERT INTO events(tenant,key,kind,details,at) VALUES(?,?,?,?,?)',
                        (self.tenant, key, kind, encode(sanitize(details)), time.time()))

    def events(self, after=0):
        integer(after)
        return [dict(r) | {'details': json.loads(r['details'])} for r in self.db.execute(
            'SELECT * FROM events WHERE tenant=? AND id>? ORDER BY id LIMIT 200',
            (self.tenant, after))]

    def status(self):
        pins = {r['id']: r['commit_sha'] for r in read_sources()}
        policy = license_policy.read_policy()
        rows = []
        for item in catalog():
            cfg = service_config(self.config, self.tenant, item['id'])
            rows.append(item | {'artifact_pin': pins[item['id']],
                'license_detected': policy[item['id']]['spdx'],
                'license_policy': policy[item['id']]['policy'],
                'source_status': 'pinned',
                'adapter_implemented': item['id'] in SPECS,
                'local_adapter_implemented': item['id'] in local_runtime.SPECS,
                'any_adapter_implemented': item['id'] in SPECS or item['id'] in local_runtime.SPECS,
                'local_actions': [local_runtime.SPECS[item['id']][0]] if item['id'] in local_runtime.SPECS else [],
                'actions': list(SPECS.get(item['id'], {})),
                'enabled_by_operator': cfg.get('enabled') is True,
                'configured_version': cfg.get('version'),
                'live_verified': False})
        return {'name': 'Verdugo Digital', 'phase': 'integration-foundation',
                'tenant': self.tenant, 'registered': len(rows),
                'source_pinned': len(pins), 'license_review_pending': len(pins),
                'api_adapters_implemented': sum(r['adapter_implemented'] for r in rows),
                'api_actions_implemented': sum(len(v) for v in SPECS.values()),
                'local_adapters_implemented': len(local_runtime.SPECS),
                'total_adapters_implemented': len(set(SPECS) | set(local_runtime.SPECS)),
                'projects_without_any_adapter': sum(not r['any_adapter_implemented'] for r in rows),
                'license_policy_allowed': sum(r['license_policy'] != 'excluido' for r in rows),
                'license_policy_excluded': sum(r['license_policy'] == 'excluido' for r in rows),
                'adapters_usable_under_policy': sum(r['any_adapter_implemented'] and r['license_policy'] != 'excluido' for r in rows),
                'live_verified': 0, 'note': 'API success is not acceptance certification.',
                'integrations': rows}

    def preflight(self, service, operation):
        if service == 'core':
            if operation not in CORE: raise VerdugoError('Unknown core action')
            return {}
        is_local = local_runtime.supports(service, operation)
        if operation not in SPECS.get(service, {}) and not is_local:
            raise VerdugoError('Adapter/action not implemented: %s.%s' % (service, operation))
        cfg = service_config(self.config, self.tenant, service)
        if cfg.get('enabled') is not True:
            raise VerdugoError('Integration disabled: ' + service)
        license_policy.check(service, cfg)
        if cfg.get('license_reviewed') is not True:
            raise VerdugoError('License/use review required: ' + service)
        version = cfg.get('version')
        if not isinstance(version, str) or not version.strip() or version.strip().lower() in ('latest', 'main', 'master'):
            raise VerdugoError('Explicit deployed version/commit required: ' + service)
        if is_local:
            local_runtime.preflight(service, operation, cfg)
        else:
            connection(service, cfg)
        return cfg

    def prepare(self, command):
        fields(command, ('service', 'operation', 'params', 'key'))
        service, op, key = command['service'], command['operation'], identifier(command['key'])
        if not isinstance(service, str) or not isinstance(op, str):
            raise VerdugoError('Service and operation must be strings')
        cfg = self.preflight(service, op)
        if service == 'core':
            self.validate_core(op, command['params'])
            request = {'public': command, 'mutates': False, 'secret_values': []}
        elif local_runtime.supports(service, op):
            request = local_runtime.build(service, op, command['params'], cfg)
        else:
            request = build(service, op, command['params'], cfg)
        fingerprint = digest({'tenant': self.tenant, 'key': key, 'request': request['public']})
        return request, cfg, fingerprint

    def plan(self, command):
        request, _, fingerprint = self.prepare(command)
        public = sanitize(request['public'])
        with self.transaction():
            old = self.db.execute('SELECT hash FROM plans WHERE tenant=? AND key=?',
                                  (self.tenant, command['key'])).fetchone()
            if old and old['hash'] != fingerprint:
                raise VerdugoError('Idempotency key reused with different input/configuration')
            self.db.execute('INSERT OR IGNORE INTO plans(tenant,key,hash,document) VALUES(?,?,?,?)',
                            (self.tenant, command['key'], fingerprint, encode(public)))
        return {'state': 'planned', 'key': command['key'], 'fingerprint': fingerprint,
                'requires_approval': request['mutates'], 'request': public,
                'external_call_made': False}

    def approve(self, key, fingerprint, ttl=600):
        self.approve_many([{'key': key, 'fingerprint': fingerprint}], ttl)
        return {'state': 'approved', 'key': key, 'expires_in_seconds': ttl}

    def approve_many(self, plans, ttl=600):
        if self.role != 'approver': raise VerdugoError('Separate local approver role required')
        integer(ttl, 1, 3600)
        if not isinstance(plans, list) or not 1 <= len(plans) <= 50:
            raise VerdugoError('Approval batch must contain 1..50 exact plans')
        with self.transaction():
            seen = set()
            for plan in plans:
                fields(plan, ('key', 'fingerprint'))
                key = identifier(plan['key'])
                if key in seen: raise VerdugoError('Duplicate approval key')
                seen.add(key)
                p = self.db.execute('SELECT * FROM plans WHERE tenant=? AND key=?',
                                    (self.tenant, key)).fetchone()
                if not p or p['hash'] != plan['fingerprint'] or p['used']:
                    raise VerdugoError('Unknown, changed, or consumed plan')
            for plan in plans:
                self.db.execute('UPDATE plans SET approved_by=?,expires=? WHERE tenant=? AND key=?',
                                (self.actor, time.time()+ttl, self.tenant, plan['key']))
                self.event(plan['key'], 'approval.granted',
                           {'fingerprint': plan['fingerprint'], 'actor': self.actor})
        return {'state': 'approved', 'count': len(plans), 'expires_in_seconds': ttl}

    def execute(self, command, execute=False):
        if type(execute) is not bool: raise VerdugoError('execute must be a boolean')
        if execute and self.role != 'operator':
            raise VerdugoError('Operator role required to execute')
        plan = self.plan(command)
        if not execute: return plan
        try:
            with self.guards.hold(self.tenant, command['key']):
                return self._execute_guarded(command, plan)
        except GuardBusy:
            return {'state': 'running', 'key': command['key'], 'external_call_made': False,
                    'note': 'Another cooperating process owns this action; no request sent.'}

    def _execute_guarded(self, command, plan):
        request, cfg, fingerprint = self.prepare(command)
        if fingerprint != plan['fingerprint']:
            raise VerdugoError('Configuration changed during preparation')
        key = command['key']
        with self.transaction():
            existing = self.db.execute('SELECT * FROM runs WHERE tenant=? AND key=?',
                                       (self.tenant, key)).fetchone()
            if existing:
                if existing['hash'] != fingerprint: raise VerdugoError('Run fingerprint conflict')
                return {'state': existing['state'], 'key': key, 'replayed': True,
                        'result': json.loads(existing['result']) if existing['result'] else None,
                        'note': 'Running/uncertain actions require reconciliation; never auto-replayed.'}
            if request['mutates']:
                p = self.db.execute('SELECT * FROM plans WHERE tenant=? AND key=?',
                                    (self.tenant, key)).fetchone()
                if not p['approved_by'] or p['used'] or p['expires'] < time.time():
                    return plan | {'state': 'awaiting_approval'}
                self.db.execute('UPDATE plans SET used=1 WHERE tenant=? AND key=?', (self.tenant, key))
            self.db.execute('INSERT INTO runs(tenant,key,hash,state,started) VALUES(?,?,?,?,?)',
                            (self.tenant, key, fingerprint, 'running', time.time()))
            self.guards.record(self, key)
            self.event(key, 'action.started', {'service': command['service'],
                'operation': command['operation'], 'actor': self.actor, 'fingerprint': fingerprint})
        try:
            if command['service'] == 'core':
                with self.transaction():
                    result = self.core(command['operation'], command['params'])
                    self.finish(key, 'succeeded', result)
            elif local_runtime.supports(command['service'], command['operation']):
                result = sanitize(local_runtime.execute(request, cfg), request['secret_values'])
                with self.transaction(): self.finish(key, 'succeeded', result)
            else:
                result = sanitize(self.transport(request, cfg), request['secret_values'])
                result = read_contracts.check(command['service'], command['operation'], result, request['public'])
                if request['mutates']:
                    remote_id(result, request['public']['result_id_path'])
                with self.transaction(): self.finish(key, 'succeeded', result)
            return {'state': 'succeeded', 'key': key, 'replayed': False, 'result': result}
        except Exception as exc:
            # A timeout after a write may mean the upstream applied it. Never blindly retry.
            state = 'uncertain' if request['mutates'] else 'failed'
            result = {'error': str(exc) if isinstance(exc, VerdugoError) else type(exc).__name__,
                      'reconciliation_required': request['mutates']}
            result = sanitize(result, request['secret_values'])
            with self.transaction(): self.finish(key, state, result)
            return {'state': state, 'key': key, 'result': result}

    def finish(self, key, state, result):
        self.db.execute('UPDATE runs SET state=?,result=?,finished=? WHERE tenant=? AND key=?',
                        (state, encode(result), time.time(), self.tenant, key))
        self.event(key, 'action.' + state, {'result_digest': digest(result)})

    def validate_core(self, op, p):
        if op in identity.ACTIONS:
            return identity.validate(op, p)
        specs = {
            'lead.capture': (('lead_id', 'name', 'email', 'dataset'), ()),
            'lead.qualify': (('lead_id', 'need_confirmed', 'budget_confirmed',
                             'authority_confirmed', 'decision_days'), ()),
            'payment.record': (('payment_id', 'lead_id', 'amount_minor', 'cost_minor',
                                'currency', 'evidence_ref', 'dataset'), ()),
            'metrics.summary': (('dataset', 'currency'), ())}
        fields(p, *specs[op])
        if 'dataset' in p and p['dataset'] not in ('demo', 'real'):
            raise VerdugoError('Explicit demo or real dataset required')
        for k in ('lead_id', 'payment_id'):
            if k in p: identifier(p[k])
        if 'name' in p: text(p['name'], 200)
        if 'email' in p:
            email = text(p['email'], 254)
            if email.count('@') != 1 or ' ' in email: raise VerdugoError('Invalid email')
        if 'currency' in p and not re.fullmatch(r'[A-Z]{3}', str(p['currency'])):
            raise VerdugoError('Currency must be an explicit three-letter code')
        for k in ('amount_minor', 'cost_minor'):
            if k in p: integer(p[k], 1 if k == 'amount_minor' else 0)
        if 'evidence_ref' in p: text(p['evidence_ref'], 500)
        if op == 'lead.qualify':
            for k in ('need_confirmed', 'budget_confirmed', 'authority_confirmed'):
                if type(p[k]) is not bool: raise VerdugoError('Qualification flags must be booleans')
            integer(p['decision_days'], 0, 3650)

    def record(self, kind, rid):
        row = self.db.execute('SELECT payload FROM records WHERE tenant=? AND kind=? AND id=?',
                              (self.tenant, kind, rid)).fetchone()
        return json.loads(row['payload']) if row else None

    def insert_record(self, kind, rid, p):
        old = self.record(kind, rid)
        if old:
            if old != p: raise VerdugoError('Record ID already exists with different values')
            return old
        self.db.execute('INSERT INTO records VALUES(?,?,?,?,?)',
                        (self.tenant, kind, rid, p['dataset'], encode(p)))
        return p

    def core(self, op, p):
        if op in identity.ACTIONS:
            return identity.apply(self, op, p)
        if op == 'lead.capture':
            self.insert_record('lead', p['lead_id'], p)
            return {'lead_id': p['lead_id'], 'dataset': p['dataset']}
        if op == 'lead.qualify':
            lead = self.record('lead', p['lead_id'])
            if not lead: raise VerdugoError('Lead not found in this tenant')
            qualified = all(p[k] for k in ('need_confirmed', 'budget_confirmed', 'authority_confirmed')) and p['decision_days'] <= 30
            data = p | {'dataset': lead['dataset'], 'qualified': qualified}
            self.insert_record('qualification', p['lead_id'], data)
            return {'lead_id': p['lead_id'], 'qualified': qualified,
                    'basis': 'operator-declared rules, not a predictive probability'}
        if op == 'payment.record':
            lead = self.record('lead', p['lead_id'])
            if not lead or lead['dataset'] != p['dataset']:
                raise VerdugoError('Lead/dataset not found in this tenant')
            self.insert_record('payment', p['payment_id'], p)
            return {'payment_id': p['payment_id'], 'reconciled': False,
                    'dataset': p['dataset']}
        payments = [json.loads(r['payload']) for r in self.db.execute(
            "SELECT payload FROM records WHERE tenant=? AND kind='payment' AND dataset=?",
            (self.tenant, p['dataset']))]
        payments = [r for r in payments if r['currency'] == p['currency']]
        receipts = sum(r['amount_minor'] for r in payments)
        costs = sum(r['cost_minor'] for r in payments)
        return {'dataset': p['dataset'], 'currency': p['currency'],
                'reported_paying_customers': len({r['lead_id'] for r in payments}),
                'reported_receipts_minor': receipts, 'reported_cost_minor': costs,
                'reported_contribution_minor': receipts - costs,
                'reconciled_receipts_minor': None, 'commercial_success_probability': None,
                'basis': 'operator-declared; bank reconciliation/tax/refunds not implemented'}
