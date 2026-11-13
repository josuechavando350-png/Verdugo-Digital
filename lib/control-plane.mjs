import http from 'node:http';
import { readFileSync } from 'node:fs';

export const EXPECTED = Object.freeze(['posthog', 'growthbook', 'erxes', 'mautic', 'dittofeed', 'rudderstack', 'openreplay', 'twenty', 'countly', 'formbricks']);

export function validateCatalog(catalog) {
  if (!catalog || !Array.isArray(catalog.projects) || catalog.projects.length !== 10) throw new Error('Catalog must contain ten projects');
  const ids = catalog.projects.map(p => p.id);
  if (new Set(ids).size !== 10 || EXPECTED.some(id => !ids.includes(id))) throw new Error('Catalog does not match required ten providers');
  return catalog.projects;
}

function legalEndpoint(raw) {
  if (typeof raw !== 'string') throw new Error('Endpoint must be a URL string');
  const url = new URL(raw);
  if (url.username || url.password || url.search || url.hash) throw new Error('Credential/query components forbidden in endpoint URL');
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['127.0.0.1', 'localhost', '::1'].includes(url.hostname))) throw new Error('Use HTTPS or loopback HTTP only');
  return url;
}

export async function checkProvider(endpoint, fetchImpl = fetch) {
  try {
    const url = legalEndpoint(endpoint);
    const res = await fetchImpl(url, { method: 'GET', redirect: 'error', signal: AbortSignal.timeout(2500) });
    return { state: res.ok ? 'reachable' : 'http_error', status_code: res.status };
  } catch (err) {
    return { state: 'unreachable', status_code: null };
  }
}

export async function getStatus(catalog, endpoints, fetchImpl = fetch) {
  const projects = validateCatalog(catalog);
  const results = await Promise.all(projects.map(async project => ({
    id: project.id,
    purpose: project.purpose,
    ...(!endpoints?.[project.id] ? { state: 'not_configured', status_code: null } : await checkProvider(endpoints[project.id], fetchImpl)),
    integration_verified: false,
    production_certified: false,
  })));
  return { product: 'Verdugo Digital', stage: 'integration', systems: results, e2e_verified: false };
}

function send(res, code, obj) {
  const body = Buffer.from(JSON.stringify(obj));
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': body.length, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
  res.end(body);
}

export function createServer({ catalog, endpoints = {}, token, fetchImpl = fetch }) {
  validateCatalog(catalog);
  if (!token || token.length < 20) throw new Error('VERDUGO_CONTROL_TOKEN must have >= 20 characters');
  return http.createServer(async (req, res) => {
    if (req.url === '/healthz' && req.method === 'GET') return send(res, 200, { status: 'ready', note: 'Control plane only; not provider certification' });
    if (req.headers.authorization !== `Bearer ${token}`) return send(res, 401, { error: 'unauthorized' });
    if (req.method !== 'GET') return send(res, 405, { error: 'method_not_allowed' });
    if (req.url === '/v1/catalog') return send(res, 200, { systems: catalog.projects.map(({ id, purpose, domain, upstream_url }) => ({ id, purpose, domain, upstream_url })) });
    if (req.url === '/v1/systems') return send(res, 200, await getStatus(catalog, endpoints, fetchImpl));
    return send(res, 404, { error: 'not_found' });
  });
}

export function startFromEnvironment() {
  const catalog = JSON.parse(readFileSync(new URL('../stack/catalog.json', import.meta.url), 'utf8'));
  const path = process.env.VERDUGO_ENDPOINTS_JSON;
  const endpoints = path ? JSON.parse(readFileSync(path, 'utf8')) : {};
  const port = Number(process.env.PORT || 8177);
  const bind = process.env.BIND_ADDRESS || '127.0.0.1';
  return createServer({ catalog, endpoints, token: process.env.VERDUGO_CONTROL_TOKEN }).listen(port, bind, () => {
    process.stdout.write(`Verdugo control plane ready at http://${bind}:${port} (providers not certified)\n`);
  });
}

if (process.argv[1]?.endsWith('/control-plane.mjs')) startFromEnvironment();
