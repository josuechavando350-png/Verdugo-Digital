import { DatabaseSync } from 'node:sqlite';
import { createHash } from 'node:crypto';
import { mkdirSync, lstatSync, openSync, closeSync, constants } from 'node:fs';
import { dirname, resolve } from 'node:path';

export class DomainError extends Error {
  constructor(code, status = 400) { super(code); this.code = code; this.status = status; }
}
export const PROVIDERS = Object.freeze(['posthog', 'rudderstack']);
const fail = (code, status) => { throw new DomainError(code, status); };
export function identifier(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]{1,80}$/.test(value)) fail('invalid_identifier');
  return value;
}
function fields(value, required, optional = []) {
  if (!value || Array.isArray(value) || typeof value !== 'object' ||
      required.some(k => !Object.hasOwn(value, k)) ||
      Object.keys(value).some(k => ![...required, ...optional].includes(k))) fail('invalid_fields');
}
function text(value, max) {
  if (typeof value !== 'string' || !value.trim() || value.length > max || /[\x00-\x1f\x7f]/.test(value)) fail('invalid_text');
  return value.trim();
}
function bool(value) { if (typeof value !== 'boolean') fail('invalid_consent'); return value; }
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
}
export function validateEvent(input) {
  fields(input, ['id', 'type', 'lead_id', 'data']);
  if (typeof input.id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(input.id)) fail('invalid_event_uuid');
  const data = input.data;
  let normalized;
  switch (input.type) {
    case 'lead.created':
      fields(data, ['name', 'source', 'analytics', 'marketing'], ['email']);
      normalized = { name: text(data.name, 160), source: text(data.source, 80), analytics: bool(data.analytics), marketing: bool(data.marketing), email: '' };
      if (data.email !== undefined && data.email !== '') {
        normalized.email = text(data.email, 254).toLowerCase();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized.email)) fail('invalid_email');
      }
      break;
    case 'lead.stage_changed':
      fields(data, ['stage']);
      if (!['qualified', 'lost'].includes(data.stage)) fail('invalid_stage');
      normalized = { stage: data.stage };
      break;
    case 'consent.updated':
      fields(data, ['analytics', 'marketing']);
      normalized = { analytics: bool(data.analytics), marketing: bool(data.marketing) };
      break;
    case 'sale.recorded':
      fields(data, ['order_id', 'amount_minor', 'currency']);
      if (!Number.isSafeInteger(data.amount_minor) || data.amount_minor <= 0 || data.amount_minor > 1e12) fail('invalid_amount_minor');
      if (!['MXN', 'USD', 'EUR'].includes(data.currency)) fail('invalid_currency');
      normalized = { order_id: identifier(data.order_id), amount_minor: data.amount_minor, currency: data.currency };
      break;
    default: fail('unsupported_event_type');
  }
  return { id: input.id.toLowerCase(), type: input.type, lead_id: identifier(input.lead_id), data: normalized };
}

function privateDatabase(path) {
  if (path === ':memory:') return path;
  const file = resolve(path), directory = dirname(file);
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const directoryStat = lstatSync(directory);
  if (!directoryStat.isDirectory() || directoryStat.isSymbolicLink() || (directoryStat.mode & 0o077)) fail('database_directory_must_be_private');
  try {
    const st = lstatSync(file);
    if (!st.isFile() || st.isSymbolicLink() || (st.mode & 0o077)) fail('database_file_must_be_private');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    const fd = openSync(file, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY | constants.O_NOFOLLOW, 0o600);
    closeSync(fd);
  }
  return file;
}

/** Local operator ledger, not a bank ledger or a substitute for the ten upstream servers. */
export class GrowthStore {
  constructor(path = ':memory:') {
    this.db = new DatabaseSync(privateDatabase(path));
    try {
      this.db.exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000; PRAGMA trusted_schema=OFF; PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;');
      const version = this.db.prepare('PRAGMA user_version').get().user_version;
      if (version > 1) fail('unsupported_database_version');
      this.db.exec(`BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS leads (
          tenant TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL,
          source TEXT NOT NULL, stage TEXT NOT NULL CHECK(stage IN ('new','qualified','won','lost')),
          analytics INTEGER NOT NULL CHECK(analytics IN (0,1)), marketing INTEGER NOT NULL CHECK(marketing IN (0,1)),
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(tenant,id)
        ) STRICT;
        CREATE TABLE IF NOT EXISTS events (
          tenant TEXT NOT NULL, id TEXT NOT NULL, fingerprint TEXT NOT NULL, type TEXT NOT NULL,
          lead_id TEXT NOT NULL, received_at TEXT NOT NULL, data TEXT NOT NULL,
          PRIMARY KEY(tenant,id), FOREIGN KEY(tenant,lead_id) REFERENCES leads(tenant,id)
        ) STRICT;
        CREATE TABLE IF NOT EXISTS sales (
          tenant TEXT NOT NULL, order_id TEXT NOT NULL, lead_id TEXT NOT NULL, event_id TEXT NOT NULL,
          amount_minor INTEGER NOT NULL CHECK(amount_minor>0), currency TEXT NOT NULL,
          PRIMARY KEY(tenant,order_id), FOREIGN KEY(tenant,event_id) REFERENCES events(tenant,id)
        ) STRICT;
        CREATE TABLE IF NOT EXISTS outbox (
          tenant TEXT NOT NULL, event_id TEXT NOT NULL, provider TEXT NOT NULL, route_id TEXT NOT NULL,
          state TEXT NOT NULL CHECK(state IN ('pending','inflight','accepted','rejected','uncertain','cancelled')),
          attempts INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, http_status INTEGER,
          PRIMARY KEY(tenant,event_id,provider), FOREIGN KEY(tenant,event_id) REFERENCES events(tenant,id)
        ) STRICT;
        CREATE INDEX IF NOT EXISTS events_lead ON events(tenant,lead_id,received_at);
        CREATE INDEX IF NOT EXISTS outbox_pending ON outbox(tenant,state,updated_at);
        PRAGMA user_version=1; COMMIT;`);
    } catch (error) { this.db.close(); throw error; }
  }
  close() { if (this.db.isOpen) this.db.close(); }
  transaction(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const value = fn(); this.db.exec('COMMIT'); return value; }
    catch (error) { this.db.exec('ROLLBACK'); throw error; }
  }
  lead(tenant, id) {
    const result = this.db.prepare('SELECT * FROM leads WHERE tenant=? AND id=?').get(identifier(tenant), identifier(id));
    return result ? { ...result, analytics: !!result.analytics, marketing: !!result.marketing } : null;
  }
  ingest(tenant, input, destinations = [], routes = {}) {
    identifier(tenant);
    if (!Array.isArray(destinations) || destinations.some(p => !PROVIDERS.includes(p)) || new Set(destinations).size !== destinations.length) fail('invalid_destinations');
    if (!routes || typeof routes !== 'object' || Array.isArray(routes) || Object.entries(routes).some(([p,v]) => !destinations.includes(p) || typeof v !== 'string' || !/^[0-9a-f]{64}$/.test(v))) fail('invalid_destination_routes');
    const event = validateEvent(input), fingerprint = createHash('sha256').update(canonical(event)).digest('hex');
    return this.transaction(() => {
      const existing = this.db.prepare('SELECT * FROM events WHERE tenant=? AND id=?').get(tenant, event.id);
      if (existing) {
        if (existing.fingerprint !== fingerprint) fail('event_id_conflict', 409);
        return { id: existing.id, lead_id: existing.lead_id, type: existing.type, received_at: existing.received_at, replayed: true };
      }
      const now = new Date().toISOString(), data = event.data;
      let lead = this.lead(tenant, event.lead_id);
      if (event.type === 'lead.created') {
        if (lead) fail('lead_already_exists', 409);
        this.db.prepare('INSERT INTO leads VALUES (?,?,?,?,?,?,?,?,?,?)').run(tenant, event.lead_id, data.name, data.email, data.source, 'new', Number(data.analytics), Number(data.marketing), now, now);
      } else {
        if (!lead) fail('lead_not_found', 404);
        if (event.type === 'lead.stage_changed') {
          if (lead.stage === 'won' || lead.stage === data.stage) fail('invalid_stage_transition', 409);
          this.db.prepare('UPDATE leads SET stage=?,updated_at=? WHERE tenant=? AND id=?').run(data.stage, now, tenant, lead.id);
        } else if (event.type === 'consent.updated') {
          this.db.prepare('UPDATE leads SET analytics=?,marketing=?,updated_at=? WHERE tenant=? AND id=?').run(Number(data.analytics), Number(data.marketing), now, tenant, lead.id);
          if (!data.analytics) this.db.prepare("UPDATE outbox SET state='cancelled',updated_at=? WHERE tenant=? AND state='pending' AND event_id IN (SELECT id FROM events WHERE tenant=? AND lead_id=?)").run(now, tenant, tenant, lead.id);
        } else if (event.type === 'sale.recorded') {
          if (lead.stage === 'lost') fail('requalify_lost_lead_first', 409);
          if (this.db.prepare('SELECT 1 FROM sales WHERE tenant=? AND order_id=?').get(tenant, data.order_id)) fail('order_id_conflict', 409);
          this.db.prepare("UPDATE leads SET stage='won',updated_at=? WHERE tenant=? AND id=?").run(now, tenant, lead.id);
        }
      }
      this.db.prepare('INSERT INTO events VALUES (?,?,?,?,?,?,?)').run(tenant, event.id, fingerprint, event.type, event.lead_id, now, JSON.stringify(data));
      if (event.type === 'sale.recorded') this.db.prepare('INSERT INTO sales VALUES (?,?,?,?,?,?)').run(tenant, data.order_id, event.lead_id, event.id, data.amount_minor, data.currency);
      lead = this.lead(tenant, event.lead_id);
      if (lead.analytics && event.type !== 'consent.updated') {
        for (const provider of destinations) this.db.prepare("INSERT INTO outbox (tenant,event_id,provider,route_id,state,updated_at) VALUES (?,?,?,?,'pending',?)").run(tenant, event.id, provider, routes[provider] || 'unbound', now);
      }
      return { id: event.id, lead_id: lead.id, type: event.type, received_at: now, replayed: false };
    });
  }
  leads(tenant, limit = 50, offset = 0) {
    identifier(tenant);
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 200 || !Number.isSafeInteger(offset) || offset < 0) fail('invalid_pagination');
    return this.db.prepare('SELECT id,name,email,source,stage,analytics,marketing,created_at,updated_at FROM leads WHERE tenant=? ORDER BY created_at DESC,id LIMIT ? OFFSET ?').all(tenant, limit, offset).map(row => ({ ...row, analytics: !!row.analytics, marketing: !!row.marketing }));
  }
  report(tenant) {
    identifier(tenant);
    const q = sql => this.db.prepare(sql).all(tenant).map(row => ({ ...row }));
    return {
      workspace: tenant, stages: q('SELECT stage,COUNT(*) AS count FROM leads WHERE tenant=? GROUP BY stage ORDER BY stage'),
      sources: q('SELECT source,COUNT(*) AS leads FROM leads WHERE tenant=? GROUP BY source ORDER BY source'),
      declared_sales: q('SELECT currency,COUNT(*) AS orders,SUM(amount_minor) AS amount_minor FROM sales WHERE tenant=? GROUP BY currency ORDER BY currency'),
      outbox: q('SELECT state,COUNT(*) AS count FROM outbox WHERE tenant=? GROUP BY state ORDER BY state'),
      events: this.db.prepare('SELECT COUNT(*) AS n FROM events WHERE tenant=?').get(tenant).n,
      revenue_reconciled: false, attribution: 'operator_declared_first_touch', upstream_e2e_verified: false,
    };
  }
  deliveries(tenant) {
    return this.db.prepare('SELECT event_id,provider,state,attempts,updated_at,http_status FROM outbox WHERE tenant=? ORDER BY updated_at DESC,event_id LIMIT 200').all(identifier(tenant));
  }
  claim(tenant, provider, routeId = 'unbound') {
    identifier(tenant);
    if (!PROVIDERS.includes(provider)) fail('unsupported_provider');
    return this.transaction(() => {
      const now = new Date().toISOString();
      const cutoff = new Date(Date.now() - 60_000).toISOString();
      // A process may have died AFTER a POST succeeded: never retry such writes automatically.
      this.db.prepare("UPDATE outbox SET state='uncertain',updated_at=? WHERE tenant=? AND state='inflight' AND updated_at<?").run(now, tenant, cutoff);
      this.db.prepare("UPDATE outbox SET state='cancelled',updated_at=? WHERE tenant=? AND state='pending' AND event_id IN (SELECT e.id FROM events e JOIN leads l ON l.tenant=e.tenant AND l.id=e.lead_id WHERE e.tenant=? AND l.analytics=0)").run(now, tenant, tenant);
      const row = this.db.prepare("SELECT e.* FROM outbox o JOIN events e ON e.tenant=o.tenant AND e.id=o.event_id WHERE o.tenant=? AND o.provider=? AND o.route_id=? AND o.state='pending' ORDER BY o.updated_at,o.event_id LIMIT 1").get(tenant, provider, routeId);
      if (!row) return null;
      this.db.prepare("UPDATE outbox SET state='inflight',attempts=attempts+1,updated_at=? WHERE tenant=? AND event_id=? AND provider=? AND state='pending'").run(now, tenant, row.id, provider);
      const lead = this.lead(tenant, row.lead_id), data = JSON.parse(row.data);
      const properties = { source: lead.source };
      if (row.type === 'lead.stage_changed') properties.stage = data.stage;
      if (row.type === 'sale.recorded') { properties.amount_minor = data.amount_minor; properties.currency = data.currency; }
      return { id: row.id, type: row.type, timestamp: row.received_at, lead_id: row.lead_id,
        subject: createHash('sha256').update(tenant + '\0' + row.lead_id).digest('hex'), properties };
    });
  }
  finish(tenant, eventId, provider, state, status = null) {
    if (!['accepted', 'rejected', 'uncertain', 'cancelled'].includes(state)) fail('invalid_delivery_state');
    const result = this.db.prepare("UPDATE outbox SET state=?,http_status=?,updated_at=? WHERE tenant=? AND event_id=? AND provider=? AND state='inflight'").run(state, status, new Date().toISOString(), tenant, eventId, provider);
    if (result.changes !== 1) fail('delivery_not_inflight', 409);
  }
}
