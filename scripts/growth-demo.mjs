import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { GrowthStore } from '../lib/growth-store.mjs';
const directory=mkdtempSync(join(tmpdir(),'verdugo-synthetic-'));
let store;
try{
  const path=join(directory,'state.sqlite');store=new GrowthStore(path);
  const lead={id:randomUUID(),type:'lead.created',lead_id:'synthetic-lead',data:{name:'DEMO SINTÉTICA',source:'demo',analytics:false,marketing:false}};
  store.ingest('demo',lead);assert.equal(store.ingest('demo',lead).replayed,true);
  store.ingest('demo',{id:randomUUID(),type:'lead.stage_changed',lead_id:lead.lead_id,data:{stage:'qualified'}});
  store.ingest('demo',{id:randomUUID(),type:'sale.recorded',lead_id:lead.lead_id,data:{order_id:'demo-order',amount_minor:125000,currency:'MXN'}});
  store.close();store=new GrowthStore(path);
  assert.equal(store.lead('demo',lead.lead_id).stage,'won');
  assert.equal(store.report('demo').events,3);
  console.log(JSON.stringify({synthetic:true,persistence_reopen_verified:true,external_requests:0,report:store.report('demo')},null,2));
}finally{store?.close();rmSync(directory,{recursive:true,force:true});}
