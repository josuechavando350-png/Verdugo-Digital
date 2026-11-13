import { createHash } from 'node:crypto';
import { DomainError, PROVIDERS } from './growth-store.mjs';

/** Only operator-controlled configuration is accepted, never endpoint URLs from event bodies. */
export function validateConnections(config = {}, env = process.env) {
  if (!config || Array.isArray(config) || typeof config !== 'object' || Object.keys(config).some(k => !PROVIDERS.includes(k))) throw new DomainError('invalid_connections');
  const result = {};
  for (const [provider, item] of Object.entries(config)) {
    if (!item || typeof item !== 'object' || Array.isArray(item) || Object.keys(item).some(k => !['enabled','base_url','key_env'].includes(k))) throw new DomainError('invalid_connection_fields');
    if (item.enabled === false) continue;
    if (item.enabled !== true || typeof item.base_url !== 'string' || typeof item.key_env !== 'string' || !/^VERDUGO_[A-Z0-9_]+$/.test(item.key_env)) throw new DomainError('invalid_connection_fields');
    let url;
    try { url = new URL(item.base_url); } catch { throw new DomainError('invalid_connection_url'); }
    if (url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
        (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost','127.0.0.1','[::1]'].includes(url.hostname)))) throw new DomainError('invalid_connection_url');
    const secret = env[item.key_env];
    if (typeof secret !== 'string' || secret.length < 8 || secret.length > 1024 || /[\r\n:]/.test(secret)) throw new DomainError('missing_or_invalid_provider_key');
    result[provider] = Object.freeze({ base: url.origin, secret, route_id: createHash('sha256').update(provider + '\0' + url.origin + '\0' + secret).digest('hex') });
  }
  return Object.freeze(result);
}

export function buildRequest(provider, connection, event) {
  const headers = { 'Content-Type': 'application/json' };
  if (provider === 'posthog') return {
    url: connection.base + '/i/v0/e/', headers,
    body: { api_key: connection.secret, event: event.type, uuid: event.id, timestamp: event.timestamp,
      properties: { ...event.properties, distinct_id: event.subject, $process_person_profile: false } },
  };
  if (provider === 'rudderstack') return {
    url: connection.base + '/v1/track',
    headers: { ...headers, Authorization: 'Basic ' + Buffer.from(connection.secret + ':').toString('base64') },
    body: { userId: event.subject, event: event.type, messageId: event.id, timestamp: event.timestamp,
      properties: event.properties, context: { library: { name: 'verdugo-digital', version: '0.1.0' } } },
  };
  throw new DomainError('unsupported_provider');
}

/** A 2xx means HTTP acceptance only. No remote readback or end-to-end certification is inferred. */
export async function dispatch(store, tenant, connections, { confirm = false, limit = 10, fetchImpl = fetch } = {}) {
  if (confirm !== true) throw new DomainError('explicit_dispatch_confirmation_required', 403);
  if (!Number.isInteger(limit) || limit < 1 || limit > 50) throw new DomainError('invalid_dispatch_limit');
  if (!connections || Object.keys(connections).some(p => !PROVIDERS.includes(p))) throw new DomainError('invalid_connections');
  const results = [];
  for (const [provider, connection] of Object.entries(connections)) {
    while (results.length < limit) {
      const event = store.claim(tenant, provider, connection.route_id);
      if (!event) break;
      if (!store.lead(tenant, event.lead_id)?.analytics) {
        store.finish(tenant, event.id, provider, 'cancelled');
        results.push({ event_id: event.id, provider, state: 'cancelled', http_status: null });
        continue;
      }
      let state = 'uncertain', status = null;
      try {
        const request = buildRequest(provider, connection, event);
        const response = await fetchImpl(request.url, { method: 'POST', headers: request.headers,
          body: JSON.stringify(request.body), redirect: 'manual', signal: AbortSignal.timeout(5000) });
        status = response.status;
        state = response.ok ? 'accepted' : (status >= 300 && status < 500 ? 'rejected' : 'uncertain');
        // Do not retain vendor bodies: they can contain credentials or customer data.
        try { await response.body?.cancel(); } catch { /* Acceptance status already observed. */ }
      } catch { /* Network failure may have happened after the remote write: no automatic replay. */ }
      store.finish(tenant, event.id, provider, state, status);
      results.push({ event_id: event.id, provider, state, http_status: status });
    }
  }
  return { deliveries: results, upstream_e2e_verified: false };
}
