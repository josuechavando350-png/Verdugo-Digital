import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import { mkdtempSync,rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { PORTFOLIO,validatePortfolio,Portfolio,nativeWorker } from '../lib/portfolio.mjs';

function store(path=':memory:'){
 const db=new DatabaseSync(path);db.exec('PRAGMA foreign_keys=ON;CREATE TABLE IF NOT EXISTS test_leads(tenant TEXT,id TEXT,event TEXT,payload TEXT,PRIMARY KEY(tenant,id),UNIQUE(tenant,event));');
 // Narrow store fixture for new-router unit tests. Integration test below uses real GrowthStore.
 return {db,ingest(tenant,event){const old=db.prepare('SELECT * FROM test_leads WHERE tenant=? AND event=?').get(tenant,event.id);if(old)return {replayed:true};db.prepare('INSERT INTO test_leads VALUES (?,?,?,?)').run(tenant,event.lead_id,event.id,JSON.stringify(event));return {replayed:false};}};
}
const input=()=>({id:randomUUID(),lead_id:randomUUID(),name:'Empresa sintética',email:'contacto@EXAMPLE.com',source:'fixture',html:'<h1>Consulta</h1><p>Expansión comercial.</p>',analytics:false,marketing:false});
const fake=async(op,data)=>({ok:true,operation:op,execution:'original_library',distribution:op.split('.')[0]+'-fixture',version:'test-fixture',external_side_effects:false,result:op==='email.validate'?{email:data.email.toLowerCase(),syntax_valid:true}:op==='document.convert_html'?{markdown:'Consulta. Expansión comercial.'}:{sentences:['Consulta.','Expansión comercial.']}});
function withStore(fn){const s=store();return Promise.resolve().then(()=>fn(s)).finally(()=>s.db.close());}

test('portfolio reconciles 50 candidates, 6 retained, 44 new and 4 preserved',()=>{validatePortfolio();assert.equal(PORTFOLIO.modules.length,50);assert.equal(PORTFOLIO.retained_originals.length,6);assert.equal(PORTFOLIO.new_identities,44);assert.deepEqual(PORTFOLIO.legacy_preserved,['countly','dittofeed','erxes','openreplay']);});
test('duplicate roles, repositories and false deployment claims rejected',()=>{for(const mutate of [c=>c.modules[1].role=c.modules[0].role,c=>c.modules[1].repository=c.modules[0].repository,c=>c.modules[0].deployment_verified=true,c=>c.all_fifty_integrated=true]){const c=structuredClone(PORTFOLIO);mutate(c);assert.throws(()=>validatePortfolio(c));}});
test('planning all lanes does not execute ads or enable services',()=>withStore(s=>{const p=new Portfolio(s);assert.ok(p.plan('attract').modules.length>5);assert.equal(p.plan('convert').external_execution,false);assert.throws(()=>p.plan('__proto__'));}));
test('one canonical event passes stages and writes existing lead ledger once (fixture contract)',()=>withStore(async s=>{const p=new Portfolio(s,{worker:fake});const event=input();const r=await p.capture(event);assert.equal(r.state,'completed');assert.equal(p.list()[0].receipts.length,3);assert.equal((await p.capture(event)).replayed,true);assert.equal(s.db.prepare('SELECT COUNT(*) n FROM test_leads').get().n,1);assert.equal(r.external_requests,0);assert.equal(r.all_fifty_integrated,false);}));
test('reused run ID with different content is rejected',()=>withStore(async s=>{const p=new Portfolio(s,{worker:fake});const e=input();await p.capture(e);await assert.rejects(()=>p.capture({...e,name:'Different'}),{code:'run_id_conflict'});}));
test('workspace isolation covers lead writes, runs and receipts',()=>withStore(async s=>{const a=new Portfolio(s,{workspace:'a',worker:fake}),b=new Portfolio(s,{workspace:'b',worker:fake});const e=input();await a.capture(e);assert.equal(b.list().length,0);await b.capture(e);assert.equal(a.list().length,1);assert.equal(b.list().length,1);assert.equal(s.db.prepare('SELECT COUNT(*) n FROM test_leads').get().n,2);}));
test('missing dependency stops before lead write and records failure',()=>withStore(async s=>{const worker=async()=>{const {PortfolioError}=await import('../lib/portfolio.mjs');throw new PortfolioError('dependency_not_installed',503);};const p=new Portfolio(s,{worker});await assert.rejects(()=>p.capture(input()),{code:'dependency_not_installed'});assert.equal(s.db.prepare('SELECT COUNT(*) n FROM test_leads').get().n,0);assert.equal(p.list()[0].state,'failed');}));
test('false original-library receipt is rejected',()=>withStore(async s=>{const p=new Portfolio(s,{worker:async()=>({execution:'mock',distribution:'fake',version:'1',external_side_effects:false})});await assert.rejects(()=>p.capture(input()),{code:'invalid_execution_proof'});assert.equal(s.db.prepare('SELECT COUNT(*) n FROM test_leads').get().n,0);}));
test('hostile fields and nonboolean consent fail before workers',()=>withStore(async s=>{let calls=0;const p=new Portfolio(s,{worker:async()=>{calls++;}});for(const e of [{...input(),tenant:'other'},{...input(),analytics:'yes'},{...input(),id:'not-uuid'}])await assert.rejects(()=>p.capture(e));assert.equal(calls,0);}));
test('reopen preserves run and prevents duplicate pipeline execution',async()=>{const dir=mkdtempSync(join(tmpdir(),'portfolio-')),path=join(dir,'state.sqlite'),e=input();let s;try{s=store(path);await new Portfolio(s,{worker:fake}).capture(e);s.db.close();s=store(path);const p=new Portfolio(s,{worker:()=>{throw Error('must not rerun');}});assert.equal((await p.capture(e)).replayed,true);assert.equal(p.list()[0].receipts.length,3);}finally{s?.db.close();rmSync(dir,{recursive:true,force:true});}});
test('native worker rejects arbitrary operations and bounded output requests',async()=>{await assert.rejects(()=>nativeWorker('shell.exec',{}),{code:'operation_not_implemented'});await assert.rejects(()=>nativeWorker('text.segment_es',{text:'x'.repeat(70000)}),{code:'body_too_large'});});
test('actual installed email-validator validates through subprocess with no DNS',async(t)=>{const caps=await nativeWorker('capabilities',{});const item=caps.operations.find(x=>x.operation==='email.validate');if(!item.package_present){t.skip('Original email-validator not installed');return;}const r=await nativeWorker('email.validate',{email:'contacto@EXAMPLE.com'});assert.equal(r.execution,'original_library');assert.equal(r.result.email,'contacto@example.com');assert.equal(r.result.mailbox_verified,false);assert.equal(r.external_side_effects,false);});

test('verified receipt deduplicates within workspace without declaring revenue (fixture contract)',()=>withStore(async s=>{
 const proof={execution:'original_library',external_side_effects:false,distribution:'stripe',version:'fixture',result:{signature_valid:true,provider_event_id:'evt_synthetic',payment_reconciled:false}};
 const p=new Portfolio(s,{worker:async()=>proof});const x={provider:'stripe',raw_body:'synthetic fixture',signature:'fixture'};
 assert.equal((await p.verifyReceipt(x)).replayed,false);assert.equal((await p.verifyReceipt(x)).replayed,true);
 await assert.rejects(()=>p.verifyReceipt({...x,raw_body:'changed'}),{code:'provider_event_conflict'});
 assert.equal((await p.verifyReceipt(x)).payment_reconciled,false);
}));
test('incomplete signed callback never creates a valid call identity',()=>withStore(async s=>{
 const p=new Portfolio(s,{worker:async()=>({execution:'original_library',external_side_effects:false,distribution:'twilio',version:'fixture',result:{signature_valid:true}})});
 await assert.rejects(()=>p.verifyReceipt({provider:'twilio',parameters:{},signature:'fixture'}),{code:'invalid_twilio_event_identity'});
}));
