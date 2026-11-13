import http from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import { readFileSync, lstatSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { GrowthStore, DomainError, identifier, PROVIDERS } from './growth-store.mjs';
import { validateConnections, dispatch } from './event-adapters.mjs';
import { createPortfolioRouter } from './portfolio.mjs';

export const EXPECTED = Object.freeze(['posthog','growthbook','erxes','mautic','dittofeed','rudderstack','openreplay','twenty','countly','formbricks']);
export function validateCatalog(catalog) {
  if (!catalog || !Array.isArray(catalog.projects) || catalog.projects.length !== 10) throw new Error('Catalog must contain ten projects');
  const ids = catalog.projects.map(p => p.id);
  if (new Set(ids).size !== 10 || EXPECTED.some(id => !ids.includes(id))) throw new Error('Catalog does not match required ten providers');
  return catalog.projects;
}
function legalEndpoint(raw) {
  if (typeof raw !== 'string') throw new Error('Endpoint must be a URL string');
  const url = new URL(raw);
  if (url.username || url.password || url.search || url.hash) throw new Error('Credential/query components forbidden');
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['127.0.0.1','localhost','[::1]'].includes(url.hostname))) throw new Error('Use HTTPS or loopback HTTP only');
  return url;
}
export async function checkProvider(endpoint, fetchImpl = fetch) {
  try {
    const response = await fetchImpl(legalEndpoint(endpoint), { method:'GET', redirect:'error', signal:AbortSignal.timeout(2500) });
    try { await response.body?.cancel(); } catch { /* Do not retain provider responses. */ }
    return { state:response.ok ? 'reachable' : 'http_error', status_code:response.status };
  } catch { return { state:'unreachable', status_code:null }; }
}
export async function getStatus(catalog, endpoints, fetchImpl = fetch) {
  const systems = await Promise.all(validateCatalog(catalog).map(async p => ({ id:p.id, purpose:p.purpose,
    ...(!endpoints?.[p.id] ? {state:'not_configured',status_code:null} : await checkProvider(endpoints[p.id], fetchImpl)),
    integration_verified:false, production_certified:false,
  })));
  return { product:'Verdugo Digital', stage:'integration', systems, e2e_verified:false };
}
const dashboard = readFileSync(new URL('../public/index.html', import.meta.url));
const dashboardScript = readFileSync(new URL('../public/dashboard.mjs', import.meta.url));
function send(res, code, value, type='application/json; charset=utf-8') {
  const body = Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(value));
  res.writeHead(code, { 'Content-Type':type, 'Content-Length':body.length, 'Cache-Control':'no-store',
    'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer',
    'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'" });
  res.end(body);
}
function localRequest(req) {
  try {
    const host = req.headers.host;
    if (typeof host !== 'string' || /[\s,/@\\]/.test(host)) return false;
    const url = new URL('http://' + host);
    return ['localhost','127.0.0.1','[::1]'].includes(url.hostname) && Number(url.port || 80) === req.socket.localPort &&
      (!req.headers.origin || req.headers.origin === 'http://' + host) && req.headers['sec-fetch-site'] !== 'cross-site';
  } catch { return false; }
}
function authenticated(value, token) {
  if (typeof value !== 'string') return false;
  const actual = Buffer.from(value), expected = Buffer.from('Bearer ' + token);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}
function readJson(req) {
  if ((req.headers['content-type'] || '').split(';')[0].trim().toLowerCase() !== 'application/json') { req.resume(); throw new DomainError('json_content_type_required',415); }
  return new Promise((resolve, reject) => {
    let size=0, chunks=[], settled=false;
    const bad = (code,status) => { if (!settled) { settled=true; chunks=[]; reject(new DomainError(code,status)); } };
    req.on('data', chunk => {
      if (settled) return;
      size += chunk.length;
      if (size > 16384) return bad('body_too_large',413);
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (settled) return;
      try { const value=JSON.parse(Buffer.concat(chunks).toString('utf8'));settled=true;resolve(value); }
      catch { bad('invalid_json',400); }
    });
    req.on('error', () => bad('invalid_request_body',400));
    req.on('aborted', () => bad('aborted_request',400));
  });
}
export function createServer({catalog, endpoints={}, token, fetchImpl=fetch, store=null, workspace='nexus', connections={}}) {
  validateCatalog(catalog); identifier(workspace);
  if (typeof token !== 'string' || token.length < 20) throw new Error('VERDUGO_CONTROL_TOKEN must have >= 20 characters');
  const portfolioRouter=createPortfolioRouter({store,workspace,send,readJson});
  const server = http.createServer(async (req,res) => {
    try {
      if (!localRequest(req)) return send(res,403,{error:'loopback_origin_required'});
      if (req.url === '/' && req.method === 'GET') return send(res,200,dashboard,'text/html; charset=utf-8');
      if (req.url === '/dashboard.mjs' && req.method === 'GET') return send(res,200,dashboardScript,'text/javascript; charset=utf-8');
      if (req.method === 'GET' && ['/portfolio','/portfolio.mjs'].includes(req.url)) {
        await portfolioRouter(req,res,new URL(req.url,'http://localhost')); return;
      }
      if (req.url === '/healthz' && req.method === 'GET') return send(res,200,{status:'ready',note:'Local core only; upstream providers not certified'});
      if (!authenticated(req.headers.authorization,token)) return send(res,401,{error:'unauthorized'});
      const url = new URL(req.url,'http://localhost');
      if (await portfolioRouter(req,res,url)) return;
      if (req.method === 'GET' && url.pathname === '/v1/catalog') return send(res,200,{systems:catalog.projects.map(({id,purpose,domain,upstream_url}) => ({id,purpose,domain,upstream_url,event_adapter_implemented:PROVIDERS.includes(id)}))});
      if (req.method === 'GET' && url.pathname === '/v1/systems') return send(res,200,await getStatus(catalog,endpoints,fetchImpl));
      if (req.method === 'GET' && url.pathname === '/v1/capabilities') return send(res,200,{workspace,local_store_enabled:!!store,event_adapters:PROVIDERS,enabled_destinations:Object.keys(connections),upstream_e2e_verified:false});
      if (!store) return send(res,503,{error:'local_store_not_enabled'});
      if (req.method === 'GET' && url.pathname === '/v1/leads') {
        if ([...url.searchParams.keys()].some(k => !['limit','offset'].includes(k))) throw new DomainError('invalid_query');
        return send(res,200,{leads:store.leads(workspace,Number(url.searchParams.get('limit')??50),Number(url.searchParams.get('offset')??0))});
      }
      if (req.method === 'GET' && url.pathname === '/v1/report') return send(res,200,store.report(workspace));
      if (req.method === 'GET' && url.pathname === '/v1/outbox') return send(res,200,{deliveries:store.deliveries(workspace)});
      if (req.method === 'POST' && req.url === '/v1/events') {
        const receipt=store.ingest(workspace,await readJson(req),Object.keys(connections),Object.fromEntries(Object.entries(connections).map(([p,c])=>[p,c.route_id])));
        return send(res,receipt.replayed?200:201,receipt);
      }
      if (req.method === 'POST' && req.url === '/v1/outbox/dispatch') {
        const options=await readJson(req);
        if (!options || Array.isArray(options) || typeof options !== 'object' || Object.keys(options).some(k => !['confirm','limit'].includes(k))) throw new DomainError('invalid_dispatch_fields');
        return send(res,200,await dispatch(store,workspace,connections,{...options,fetchImpl}));
      }
      return send(res,['GET','POST'].includes(req.method)?404:405,{error:'unsupported_route_or_method'});
    } catch (error) {
      if (!res.headersSent && !res.destroyed) send(res,error instanceof DomainError?error.status:500,{error:error instanceof DomainError?error.code:'internal_error'});
    }
  });
  server.requestTimeout=10000;server.headersTimeout=10000;
  return server;
}
export function startFromEnvironment() {
  process.umask(0o077);
  const catalog=JSON.parse(readFileSync(new URL('../stack/catalog.json',import.meta.url),'utf8'));
  const endpointPath=process.env.VERDUGO_ENDPOINTS_JSON;
  const endpoints=endpointPath?JSON.parse(readFileSync(endpointPath,'utf8')):{};
  let connectionConfig={};
  if (process.env.VERDUGO_CONNECTIONS_JSON) {
    const st=lstatSync(process.env.VERDUGO_CONNECTIONS_JSON);
    if (!st.isFile() || st.isSymbolicLink() || (st.mode&0o077)) throw new DomainError('connections_file_must_be_private');
    connectionConfig=JSON.parse(readFileSync(process.env.VERDUGO_CONNECTIONS_JSON,'utf8'));
  }
  const connections=validateConnections(connectionConfig);
  const bind=process.env.BIND_ADDRESS||'127.0.0.1',port=Number(process.env.PORT||8177);
  if (!['127.0.0.1','::1','localhost'].includes(bind) || !Number.isInteger(port) || port<1 || port>65535) throw new DomainError('loopback_bind_required');
  const store=new GrowthStore(process.env.VERDUGO_STATE_DB||join(homedir(),'.local','share','verdugo','growth.sqlite'));
  let server;
  try { server=createServer({catalog,endpoints,token:process.env.VERDUGO_CONTROL_TOKEN,store,connections,workspace:process.env.VERDUGO_WORKSPACE||'nexus'}); }
  catch(error){store.close();throw error;}
  server.on('close',()=>store.close());
  server.on('error',()=>{store.close();console.error('No se pudo iniciar el servidor local.');process.exitCode=1;});
  for (const signal of ['SIGINT','SIGTERM']) process.once(signal,()=>server.close());
  return server.listen(port,bind,()=>console.log(`Verdugo local: http://${bind}:${port}. Proveedores externos no certificados.`));
}
if (process.argv[1]===fileURLToPath(import.meta.url)) {
  try {startFromEnvironment();} catch(error) {console.error(error instanceof DomainError?error.code:'No se pudo iniciar Verdugo; revise configuración y Node.js.');process.exitCode=1;}
}
