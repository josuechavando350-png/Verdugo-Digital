import assert from 'node:assert/strict';
import { test } from 'node:test';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync, chmodSync, statSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { GrowthStore } from '../lib/growth-store.mjs';

const lead = (id='l1', analytics=false) => ({ id: randomUUID(), type:'lead.created', lead_id:id, data:{name:'Persona de prueba',email:'test@example.invalid',source:'organic',analytics,marketing:false} });
const event = (type,data,id='l1') => ({id:randomUUID(),type,lead_id:id,data});
const withStore = fn => {const s=new GrowthStore();try{fn(s);}finally{s.close();}};

test('lead -> qualification -> declared sale is persisted atomically',()=>withStore(s=>{
  s.ingest('nexus',lead());
  s.ingest('nexus',event('lead.stage_changed',{stage:'qualified'}));
  s.ingest('nexus',event('sale.recorded',{order_id:'ord1',amount_minor:125000,currency:'MXN'}));
  assert.equal(s.lead('nexus','l1').stage,'won');
  assert.deepEqual(s.report('nexus').declared_sales,[{currency:'MXN',orders:1,amount_minor:125000}]);
  assert.equal(s.report('nexus').revenue_reconciled,false);
}));
test('same event replay has one lead and one event',()=>withStore(s=>{
  const e=lead();assert.equal(s.ingest('nexus',e).replayed,false);assert.equal(s.ingest('nexus',e).replayed,true);
  assert.equal(s.leads('nexus').length,1);assert.equal(s.report('nexus').events,1);
}));
test('event fingerprint ignores JSON key order, not content',()=>withStore(s=>{
  const e=lead();s.ingest('nexus',e);
  const reordered={data:Object.fromEntries(Object.entries(e.data).reverse()),lead_id:e.lead_id,type:e.type,id:e.id};
  assert.equal(s.ingest('nexus',reordered).replayed,true);
  assert.throws(()=>s.ingest('nexus',{...e,data:{...e.data,name:'Alterado'}}),{code:'event_id_conflict'});
}));
test('workspace isolation covers leads, orders, events, and outbox',()=>withStore(s=>{
  const e=lead('l1',true);s.ingest('a',e,['posthog']);s.ingest('b',e);
  s.ingest('a',event('sale.recorded',{order_id:'same',amount_minor:100,currency:'USD'}));
  assert.equal(s.lead('b','l1').stage,'new');assert.equal(s.report('b').declared_sales.length,0);
  assert.equal(s.deliveries('b').length,0);assert.equal(s.report('b').events,1);
}));
test('invalid payloads fail without partial writes',()=>withStore(s=>{
  const e=lead();
  for(const invalid of [{...e,tenant:'other'},{...e,data:{...e.data,analytics:'yes'}},{...e,data:{...e.data,secret:'oops'}},{...e,type:'arbitrary'},{...e,id:'not-uuid'}]) assert.throws(()=>s.ingest('nexus',invalid));
  assert.equal(s.leads('nexus').length,0);
}));
test('duplicate lead and duplicate order are rejected without counting revenue twice',()=>withStore(s=>{
  s.ingest('nexus',lead());assert.throws(()=>s.ingest('nexus',lead()),{code:'lead_already_exists'});
  s.ingest('nexus',event('sale.recorded',{order_id:'o1',amount_minor:500,currency:'MXN'}));
  assert.throws(()=>s.ingest('nexus',event('sale.recorded',{order_id:'o1',amount_minor:500,currency:'MXN'})),{code:'order_id_conflict'});
  assert.equal(s.report('nexus').events,2);
}));
test('money is positive integer minor units, currencies are not mixed',()=>withStore(s=>{
  s.ingest('nexus',lead());
  for(const amount of [0,-1,1.5,Number.MAX_SAFE_INTEGER]) assert.throws(()=>s.ingest('nexus',event('sale.recorded',{order_id:'bad',amount_minor:amount,currency:'MXN'})),{code:'invalid_amount_minor'});
  for(const currency of ['MXN','USD']) s.ingest('nexus',event('sale.recorded',{order_id:currency,amount_minor:100,currency}));
  assert.equal(s.report('nexus').declared_sales.length,2);
}));
test('lost leads must be requalified; won leads cannot be downgraded',()=>withStore(s=>{
  s.ingest('nexus',lead());s.ingest('nexus',event('lead.stage_changed',{stage:'lost'}));
  assert.throws(()=>s.ingest('nexus',event('sale.recorded',{order_id:'o1',amount_minor:100,currency:'MXN'})),{code:'requalify_lost_lead_first'});
  s.ingest('nexus',event('lead.stage_changed',{stage:'qualified'}));
  s.ingest('nexus',event('sale.recorded',{order_id:'o1',amount_minor:100,currency:'MXN'}));
  assert.throws(()=>s.ingest('nexus',event('lead.stage_changed',{stage:'lost'})),{code:'invalid_stage_transition'});
}));
test('no consent or no configured destinations means no outbound jobs',()=>withStore(s=>{
  s.ingest('nexus',lead('l1'),['posthog']);s.ingest('nexus',lead('l2',true));
  assert.equal(s.deliveries('nexus').length,0);
}));
test('revocation cancels queued jobs and granting does not revive them',()=>withStore(s=>{
  s.ingest('nexus',lead('l1',true),['posthog','rudderstack']);
  s.ingest('nexus',event('consent.updated',{analytics:false,marketing:false}));
  assert.ok(s.deliveries('nexus').every(r=>r.state==='cancelled'));
  s.ingest('nexus',event('consent.updated',{analytics:true,marketing:false}),['posthog']);
  assert.equal(s.claim('nexus','posthog'),null);
}));
test('outbound envelope contains no name, email, or plain lead id as subject',()=>withStore(s=>{
  s.ingest('nexus',lead('l1',true),['posthog']);const job=s.claim('nexus','posthog');
  assert.equal(job.subject.length,64);assert.notEqual(job.subject,'l1');
  assert.doesNotMatch(JSON.stringify(job.properties),/Persona|example|email|name/);
  assert.equal(s.claim('nexus','posthog'),null);
}));
test('SQL payload is data, pagination and tenant identifiers are validated',()=>withStore(s=>{
  const e=lead();e.data.name="Robert'); DROP TABLE leads;--";s.ingest('nexus',e);
  assert.equal(s.leads('nexus')[0].name,e.data.name);
  assert.throws(()=>s.leads('nexus',999));assert.throws(()=>s.report('../other'));
}));
test('database survives reopen; second connection cannot claim the same job',()=>{
  const dir=mkdtempSync(join(tmpdir(),'vd-store-')),file=join(dir,'state.sqlite');let a,b;
  try{a=new GrowthStore(file);a.ingest('nexus',lead('l1',true),['posthog']);a.close();a=new GrowthStore(file);b=new GrowthStore(file);
    assert.equal(b.leads('nexus').length,1);assert.ok(a.claim('nexus','posthog'));assert.equal(b.claim('nexus','posthog'),null);
    assert.equal(statSync(file).mode&0o077,0);
  }finally{a?.close();b?.close();rmSync(dir,{recursive:true,force:true});}
});
test('abandoned in-flight write becomes uncertain, never pending',()=>withStore(s=>{
  s.ingest('nexus',lead('l1',true),['posthog']);s.claim('nexus','posthog');
  s.db.prepare('UPDATE outbox SET updated_at=?').run('2000-01-01T00:00:00.000Z');
  assert.equal(s.claim('nexus','posthog'),null);assert.equal(s.deliveries('nexus')[0].state,'uncertain');
}));
test('insecure directories and symlink databases are rejected',()=>{
  const dir=mkdtempSync(join(tmpdir(),'vd-insecure-')),file=join(dir,'state.sqlite');
  try{chmodSync(dir,0o755);assert.throws(()=>new GrowthStore(file),{code:'database_directory_must_be_private'});
    chmodSync(dir,0o700);writeFileSync(join(dir,'target'),'');symlinkSync(join(dir,'target'),file);
    assert.throws(()=>new GrowthStore(file),{code:'database_file_must_be_private'});
  }finally{rmSync(dir,{recursive:true,force:true});}
});
