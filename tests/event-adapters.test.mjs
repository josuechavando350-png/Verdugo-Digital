import assert from 'node:assert/strict';
import { test } from 'node:test';
import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { GrowthStore } from '../lib/growth-store.mjs';
import { validateConnections,buildRequest,dispatch } from '../lib/event-adapters.mjs';
const key='synthetic-key-only';
function setup(store,connections=config('https://example.invalid')){store.ingest('nexus',{id:randomUUID(),type:'lead.created',lead_id:'l1',data:{name:'Private Name',email:'private@example.invalid',source:'organic',analytics:true,marketing:false}},['posthog','rudderstack'],Object.fromEntries(Object.entries(connections).map(([p,c])=>[p,c.route_id])));}
function config(base){return validateConnections(Object.fromEntries(['posthog','rudderstack'].map(p=>[p,{enabled:true,base_url:base,key_env:'VERDUGO_TEST_KEY'}])),{VERDUGO_TEST_KEY:key});}
async function fixture(handler,fn){const server=http.createServer(handler);await new Promise(r=>server.listen(0,'127.0.0.1',r));try{await fn('http://127.0.0.1:'+server.address().port);}finally{await new Promise(r=>server.close(r));}}

test('default configuration disables every outbound integration',()=>{assert.deepEqual(validateConnections(),{});assert.deepEqual(validateConnections({posthog:{enabled:false}}),{});});
test('configuration rejects missing credentials, URL credentials, arbitrary HTTP and unsupported providers',()=>{
  for(const url of ['http://example.com','https://user:pass@example.com','https://example.com?key=x','https://example.com/path'])assert.throws(()=>config(url));
  assert.throws(()=>validateConnections({mautic:{enabled:true}}));assert.throws(()=>validateConnections({posthog:{enabled:true,base_url:'https://example.com',key_env:'VERDUGO_MISSING'}},{}));
});
test('two concrete API contracts reach real local HTTP fixtures without contact PII',async()=>{
  const calls=[];
  await fixture(async(req,res)=>{let body='';for await(const part of req)body+=part;calls.push({path:req.url,auth:req.headers.authorization,body:JSON.parse(body)});res.writeHead(200);res.end('OK');},async base=>{
    const s=new GrowthStore();try{setup(s,config(base));const result=await dispatch(s,'nexus',config(base),{confirm:true});
      assert.equal(result.deliveries.length,2);assert.ok(result.deliveries.every(d=>d.state==='accepted'));
      assert.equal(result.upstream_e2e_verified,false);
      assert.equal(calls[0].path,'/i/v0/e/');assert.equal(calls[0].body.api_key,key);assert.equal(calls[0].body.properties.distinct_id.length,64);
      assert.equal(calls[1].path,'/v1/track');assert.equal(calls[1].auth,'Basic '+Buffer.from(key+':').toString('base64'));
      assert.equal(calls[1].body.messageId,calls[0].body.uuid);
      assert.doesNotMatch(JSON.stringify(calls),/Private Name|private@example|"lead_id"/);
      assert.doesNotMatch(JSON.stringify(s.deliveries('nexus')),/synthetic-key/);
      assert.equal((await dispatch(s,'nexus',config(base),{confirm:true})).deliveries.length,0);
    }finally{s.close();}
  });
});
test('dispatch requires explicit confirmation, not a truthy string',async()=>{
  const s=new GrowthStore();try{setup(s);for(const confirm of [false,'true',1])await assert.rejects(()=>dispatch(s,'nexus',config('https://example.invalid'),{confirm}),{code:'explicit_dispatch_confirmation_required'});assert.ok(s.deliveries('nexus').every(d=>d.state==='pending'));}finally{s.close();}
});
test('network failure is uncertain and never silently retried',async()=>{
  const s=new GrowthStore();let calls=0;try{setup(s);const connections=config('https://example.invalid');const fetchImpl=async()=>{calls++;throw Error('private-secret-do-not-log');};
    const result=await dispatch(s,'nexus',connections,{confirm:true,fetchImpl});assert.ok(result.deliveries.every(d=>d.state==='uncertain'));
    await dispatch(s,'nexus',connections,{confirm:true,fetchImpl});assert.equal(calls,2);assert.doesNotMatch(JSON.stringify(result),/private-secret/);
  }finally{s.close();}
});
test('redirects are rejected without leaking the secret to a second host',async()=>{
  const s=new GrowthStore();try{setup(s);const result=await dispatch(s,'nexus',config('https://example.invalid'),{confirm:true,fetchImpl:async(_url,options)=>{
    assert.equal(options.redirect,'manual');return new Response('',{status:302,headers:{Location:'https://other.invalid'}});
  }});assert.ok(result.deliveries.every(d=>d.state==='rejected'));}finally{s.close();}
});
test('consent withdrawal prevents POST even with configured providers',async()=>{
  const s=new GrowthStore();let calls=0;try{setup(s);s.ingest('nexus',{id:randomUUID(),type:'consent.updated',lead_id:'l1',data:{analytics:false,marketing:false}});
    const result=await dispatch(s,'nexus',config('https://example.invalid'),{confirm:true,fetchImpl:async()=>{calls++;return new Response();}});assert.equal(calls,0);assert.equal(result.deliveries.length,0);
  }finally{s.close();}
});
test('concurrent dispatches claim each row only once',async()=>{
  const s=new GrowthStore();let calls=0;try{setup(s);const options={confirm:true,fetchImpl:async()=>{calls++;await new Promise(r=>setTimeout(r,10));return new Response('',{status:200});}};
    await Promise.all([dispatch(s,'nexus',config('https://example.invalid'),options),dispatch(s,'nexus',config('https://example.invalid'),options)]);assert.equal(calls,2);
  }finally{s.close();}
});
test('adapters maintain original event timestamp and stable ID',()=>{
  const envelope={id:randomUUID(),timestamp:'2026-01-01T00:00:00.000Z',type:'sale.recorded',subject:'hash',properties:{amount_minor:123,currency:'MXN'}};
  for(const provider of ['posthog','rudderstack']){const request=buildRequest(provider,{base:'https://example.invalid',secret:key},envelope);assert.equal(request.body.timestamp,envelope.timestamp);assert.equal(request.body.uuid||request.body.messageId,envelope.id);}
});

test('changing destination credentials never reroutes previously queued customer events',async()=>{
  const s=new GrowthStore();let calls=0;try{setup(s);const changed=validateConnections({posthog:{enabled:true,base_url:'https://other.invalid',key_env:'VERDUGO_TEST_KEY'}},{VERDUGO_TEST_KEY:key});
    const result=await dispatch(s,'nexus',changed,{confirm:true,fetchImpl:async()=>{calls++;return new Response();}});assert.equal(calls,0);assert.equal(result.deliveries.length,0);assert.ok(s.deliveries('nexus').every(r=>r.state==='pending'));
  }finally{s.close();}
});
