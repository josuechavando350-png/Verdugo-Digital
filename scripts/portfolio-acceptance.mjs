/** Actual original-library subprocesses -> existing API -> existing SQLite ledger. */
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readFileSync,mkdtempSync,rmSync,mkdirSync,writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createServer } from '../lib/control-plane.mjs';
import { GrowthStore } from '../lib/growth-store.mjs';
import { nativeWorker } from '../lib/portfolio.mjs';
const catalog=JSON.parse(readFileSync(new URL('../stack/catalog.json',import.meta.url)));
const directory=mkdtempSync(join(tmpdir(),'verdugo-portfolio-native-'));
const dbpath=join(directory,'core.sqlite');
const token='synthetic-'+randomUUID();
const event={id:randomUUID(),lead_id:randomUUID(),name:'Empresa de prueba',email:'contacto@EXAMPLE.com',source:'synthetic-acceptance',html:'<h1>Empresa sintética</h1><p>Abre una sucursal. Requiere revisión comercial.</p>',analytics:false,marketing:false};
let store,server;
const report={scope:'original_library_to_existing_core',synthetic:true,mock_libraries:false,commit:process.env.GITHUB_SHA||null,run_id:process.env.GITHUB_RUN_ID||null,checks:{},all_fifty_integrated:false,external_customer_or_payment_activity:false,status:'not_run'};
async function start(){store=new GrowthStore(dbpath);server=createServer({catalog,token,store,workspace:'portfolio-demo'});await new Promise(r=>server.listen(0,'127.0.0.1',r));return 'http://127.0.0.1:'+server.address().port;}
async function stop(){if(server){await new Promise(r=>server.close(r));server=null;}store?.close();store=null;}
try{
 const capabilities=await nativeWorker('capabilities',{});assert.ok(capabilities.operations.every(p=>p.package_present));report.packages=capabilities.operations;
 let base=await start();
 const call=async(path,body)=>{const r=await fetch(base+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});assert.ok(r.ok,'HTTP '+r.status+' for '+path);return r.json();};
 const capture=await call('/v1/portfolio/opportunities',event);assert.equal(capture.state,'completed');
 const leads=(await call('/v1/leads')).leads;assert.equal(leads.length,1);assert.equal(leads[0].id,event.lead_id);assert.equal(leads[0].email,'contacto@example.com');
 report.checks.native_pipeline_to_authoritative_lead=true;
 let state=await call('/v1/portfolio');assert.equal(state.selected_count,50);assert.equal(state.runs[0].receipts.length,3);assert.deepEqual(state.runs[0].receipts.map(r=>r.distribution).sort(),['email-validator','markitdown','spacy']);
 report.checks.original_library_receipts=true;assert.equal(state.all_fifty_integrated,false);assert.equal(state.paid_actions_enabled,false);
 assert.equal((await call('/v1/portfolio/opportunities',event)).replayed,true);assert.equal((await call('/v1/leads')).leads.length,1);report.checks.idempotent_capture=true;
 const denied=await fetch(base+'/v1/portfolio');assert.equal(denied.status,401);report.checks.authentication_required=true;
 await stop();base=await start();state=await call('/v1/portfolio');assert.equal(state.runs[0].state,'completed');assert.equal((await call('/v1/leads')).leads[0].id,event.lead_id);assert.equal((await call('/v1/portfolio/opportunities',event)).replayed,true);report.checks.restart_persistence=true;
 const coreReport=await call('/v1/report');assert.equal(coreReport.revenue_reconciled,false);assert.equal(coreReport.events,1);report.checks.no_revenue_fabricated=true;
 report.status='passed';
}catch(error){report.status='failed';report.error=String(error?.message||'native_acceptance_failed').slice(0,200);process.exitCode=1;}
finally{await stop();rmSync(directory,{recursive:true,force:true});mkdirSync('evidence',{recursive:true});writeFileSync('evidence/portfolio-runtime.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
