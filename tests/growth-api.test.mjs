import assert from 'node:assert/strict';
import { test } from 'node:test';
import { randomUUID } from 'node:crypto';
import http from 'node:http';
import { mkdtempSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer,EXPECTED } from '../lib/control-plane.mjs';
import { GrowthStore } from '../lib/growth-store.mjs';
const token='synthetic-control-token-at-least-32-chars';
const catalog={projects:EXPECTED.map(id=>({id,purpose:id}))};
const event=(type='lead.created',data={name:'Test',source:'direct',analytics:false,marketing:false})=>({id:randomUUID(),type,lead_id:'l1',data});
async function app(fn,store=new GrowthStore()){
  const server=createServer({catalog,token,store,workspace:'client-a'});await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+server.address().port;
  const request=(path,body,headers={})=>fetch(base+path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(body!==undefined?{'Content-Type':'application/json'}:{}),...headers},...(body!==undefined?{body:typeof body==='string'?body:JSON.stringify(body)}:{})});
  try{await fn({base,request,store});}finally{await new Promise(r=>server.close(r));store.close();}
}

test('HTTP flow captures, qualifies, records sale, and reports it in one product',()=>app(async({request})=>{
  const lead=event();assert.equal((await request('/v1/events',lead)).status,201);assert.equal((await request('/v1/events',lead)).status,200);
  assert.equal((await request('/v1/events',event('lead.stage_changed',{stage:'qualified'}))).status,201);
  assert.equal((await request('/v1/events',event('sale.recorded',{order_id:'order1',amount_minor:125000,currency:'MXN'}))).status,201);
  const report=await (await request('/v1/report')).json();assert.deepEqual(report.declared_sales,[{currency:'MXN',orders:1,amount_minor:125000}]);assert.equal(report.events,3);assert.equal(report.revenue_reconciled,false);
  const leads=await (await request('/v1/leads')).json();assert.equal(leads.leads[0].stage,'won');
}));
test('API rejects cross-tenant payloads and query overrides',()=>app(async({request,store})=>{
  assert.equal((await request('/v1/events',{...event(),tenant:'other'})).status,400);
  assert.equal((await request('/v1/leads?tenant=other')).status,400);
  assert.equal(store.leads('other').length,0);
}));
test('unauthorized request never mutates state',()=>app(async({base,store})=>{
  const response=await fetch(base+'/v1/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(event())});assert.equal(response.status,401);assert.equal(store.leads('client-a').length,0);
}));
test('malformed JSON, wrong content type, and oversized bodies fail closed',()=>app(async({request,store})=>{
  assert.equal((await request('/v1/events','{')).status,400);
  assert.equal((await request('/v1/events',event(),{'Content-Type':'text/plain'})).status,415);
  assert.equal((await request('/v1/events','"'+'x'.repeat(20000)+'"')).status,413);
  assert.equal(store.report('client-a').events,0);
}));
test('host rebinding and cross-origin requests are rejected',()=>app(async({request,base})=>{
  const hostileStatus=await new Promise((resolve,reject)=>{const q=http.get(base+'/v1/report',{headers:{Host:'evil.invalid',Authorization:'Bearer '+token}},r=>{r.resume();resolve(r.statusCode);});q.on('error',reject);});
  assert.equal(hostileStatus,403);
  assert.equal((await request('/v1/events',event(),{Origin:'https://evil.invalid'})).status,403);
  assert.equal((await request('/v1/report',undefined,{'Sec-Fetch-Site':'cross-site'})).status,403);
}));
test('capabilities distinguish adapters from configured live integrations',()=>app(async({request})=>{
  const value=await (await request('/v1/capabilities')).json();assert.deepEqual(value.enabled_destinations,[]);assert.deepEqual(value.event_adapters,['posthog','rudderstack']);assert.equal(value.upstream_e2e_verified,false);
}));
test('dispatch route rejects unknown fields and requires boolean confirmation',()=>app(async({request})=>{
  assert.equal((await request('/v1/outbox/dispatch',{confirm:'true'})).status,403);
  assert.equal((await request('/v1/outbox/dispatch',{confirm:true,endpoint:'http://evil'})).status,400);
  const result=await request('/v1/outbox/dispatch',{confirm:true});assert.equal(result.status,200);assert.deepEqual((await result.json()).deliveries,[]);
}));
test('dashboard scripts are local, no token is embedded, and CSP blocks inline scripts',()=>app(async({base})=>{
  const html=await fetch(base+'/');assert.equal(html.status,200);assert.match(html.headers.get('content-security-policy'),/script-src 'self'/);
  const text=await html.text();assert.match(text,/Prospectos/);assert.doesNotMatch(text,new RegExp(token));assert.doesNotMatch(text,/<script(?![^>]*src=)[^>]*>/);
  const js=await fetch(base+'/dashboard.mjs');assert.equal(js.status,200);
}));
test('HTTP capture survives server restart with same SQLite database',async()=>{
  const dir=mkdtempSync(join(tmpdir(),'vd-api-')),path=join(dir,'state.sqlite');
  try{await app(async({request})=>{assert.equal((await request('/v1/events',event())).status,201);},new GrowthStore(path));
    await app(async({request})=>{const value=await (await request('/v1/leads')).json();assert.equal(value.leads.length,1);},new GrowthStore(path));
  }finally{rmSync(dir,{recursive:true,force:true});}
});
