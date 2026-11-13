import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

export const PORTFOLIO = JSON.parse(readFileSync(new URL('../stack/portfolio50.json', import.meta.url), 'utf8'));
PORTFOLIO.modules=PORTFOLIO.modules.map(m=>({enabled_by_default:false,license_review:'pending',deployment_verified:false,live_integration_verified:false,source_verification:'pending_current_resolution',implemented_operations:PORTFOLIO.runtime_operations[m.id]||[],requires_external_account:PORTFOLIO.external_accounts.includes(m.id),has_external_side_effects:PORTFOLIO.external_effects.includes(m.id),source_url:'https://github.com/'+m.repository,...m}));
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const original = new Set(['posthog','growthbook','erxes','mautic','dittofeed','rudderstack','openreplay','twenty','countly','formbricks']);
const domains = ['intelligence','traffic','conversion','measurement','data','operations','privacy'];
const operations = new Set(['capabilities','email.validate','document.convert_html','text.segment_es','stripe.verify_signature','twilio.verify_signature']);
export class PortfolioError extends Error {
  constructor(code, status=400) { super(code); this.code=code; this.status=status; }
}
const fail=(code,status)=>{throw new PortfolioError(code,status);};
const own=(x,k)=>Object.hasOwn(x,k);
function shape(x,keys) {
  if (!x || Array.isArray(x) || typeof x!=='object' || keys.some(k=>!own(x,k)) || Object.keys(x).some(k=>!keys.includes(k))) fail('invalid_fields');
}
function text(x,max) {
  if(typeof x!=='string' || !x.trim() || x.length>max || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(x))fail('invalid_text');
  return x.trim();
}
const canonical=x=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(canonical).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';
const hash=x=>createHash('sha256').update(canonical(x)).digest('hex');
export function validatePortfolio(catalog=PORTFOLIO) {
  if(catalog.count!==50 || !Array.isArray(catalog.modules) || catalog.modules.length!==50)fail('portfolio_must_have_fifty');
  const ids=new Set(),repos=new Set(),roles=new Set();
  for(const m of catalog.modules){
    if(!/^[a-z][a-z0-9-]{1,50}$/.test(m.id) || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(m.repository) || !domains.includes(m.lane))fail('invalid_module');
    if(ids.has(m.id)||repos.has(m.repository.toLowerCase())||roles.has(m.role))fail('duplicate_module_or_role');
    if(m.enabled_by_default!==false || m.deployment_verified!==false || m.live_integration_verified!==false)fail('unverified_module_claim');
    ids.add(m.id);repos.add(m.repository.toLowerCase());roles.add(m.role);
  }
  const retained=[...original].filter(x=>ids.has(x)).sort(), legacy=[...original].filter(x=>!ids.has(x)).sort();
  if(JSON.stringify(retained)!==JSON.stringify(catalog.retained_originals) || JSON.stringify(legacy)!==JSON.stringify(catalog.legacy_preserved) || catalog.new_identities!==50-retained.length)fail('portfolio_count_mismatch');
  if(catalog.all_fifty_integrated!==false||catalog.production_ready!==false)fail('unverified_global_claim');
  return catalog;
}
validatePortfolio();

/** Invoke original libraries only. No shell, no arbitrary executable, no inherited cloud tokens. */
export function nativeWorker(operation,data, {python=process.env.VERDUGO_PYTHON||'python3',timeout=25000}={}) {
  if(!operations.has(operation))return Promise.reject(new PortfolioError('operation_not_implemented',422));
  const serialized=JSON.stringify({operation,data});
  if(Buffer.byteLength(serialized)>65536)return Promise.reject(new PortfolioError('body_too_large',413));
  const env={};
  for(const key of ['PATH','HOME','LANG','LC_ALL','SYSTEMROOT','TEMP','TMP','VIRTUAL_ENV','VERDUGO_STRIPE_WEBHOOK_SECRET','VERDUGO_TWILIO_AUTH_TOKEN','VERDUGO_TWILIO_WEBHOOK_URL']){
    if(process.env[key])env[key]=process.env[key];
  }
  env.PYTHONDONTWRITEBYTECODE='1';
  return new Promise((resolve,reject)=>{
    let settled=false,out='',size=0;
    const child=spawn(python,[fileURLToPath(new URL('../scripts/portfolio_worker.py',import.meta.url))],{env,stdio:['pipe','pipe','pipe'],shell:false});
    const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);error?reject(error):resolve(value);};
    const timer=setTimeout(()=>{child.kill('SIGKILL');finish(new PortfolioError('native_worker_timeout',504));},timeout);
    child.stdout.on('data',chunk=>{size+=chunk.length;if(size>262144){child.kill('SIGKILL');finish(new PortfolioError('native_output_too_large',502));}else out+=chunk;});
    child.stderr.on('data',()=>{}); // Never reflect user data, credentials or provider traces.
    child.on('error',()=>finish(new PortfolioError('native_worker_unavailable',503)));
    child.stdin.on('error',()=>{});
    child.on('close',code=>{
      if(settled)return;
      try{const receipt=JSON.parse(out);
        if(code!==0 || receipt.ok!==true){
          const safe=new Set(['dependency_not_installed','invalid_email','invalid_fields','invalid_text','operation_not_implemented','stripe_signing_secret_required','invalid_stripe_signature','twilio_signing_configuration_required','invalid_twilio_parameters','invalid_twilio_signature','network_disabled_in_local_worker']);
          return finish(new PortfolioError(safe.has(receipt.error)?receipt.error:'native_operation_failed',receipt.error==='dependency_not_installed'?503:422));
        }
        finish(null,receipt);
      }catch{finish(new PortfolioError('invalid_native_receipt',502));}
    });
    child.stdin.end(serialized);
  });
}

export class Portfolio {
  constructor(store,{workspace='nexus',worker=nativeWorker,clock=()=>Date.now()}={}){
    if(!store?.db || typeof store.ingest!=='function')fail('existing_growth_store_required',503);
    if(!/^[A-Za-z0-9_-]{1,80}$/.test(workspace))fail('invalid_workspace');
    this.store=store;this.db=store.db;this.workspace=workspace;this.worker=worker;this.clock=clock;this.active=0;
    this.db.exec(`CREATE TABLE IF NOT EXISTS portfolio_runs (
      tenant TEXT NOT NULL,id TEXT NOT NULL,fingerprint TEXT NOT NULL,subject_id TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN ('running','completed','failed','interrupted')),
      step TEXT NOT NULL,error TEXT,started_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,
      PRIMARY KEY(tenant,id)
    ) STRICT;
    CREATE TABLE IF NOT EXISTS portfolio_receipts (
      tenant TEXT NOT NULL,run_id TEXT NOT NULL,step TEXT NOT NULL,provider TEXT NOT NULL,
      distribution TEXT NOT NULL,version TEXT NOT NULL,recorded_at INTEGER NOT NULL,
      PRIMARY KEY(tenant,run_id,step),FOREIGN KEY(tenant,run_id) REFERENCES portfolio_runs(tenant,id)
    ) STRICT;
    CREATE TABLE IF NOT EXISTS portfolio_provider_receipts (
      tenant TEXT NOT NULL,provider TEXT NOT NULL,event_key TEXT NOT NULL,
      fingerprint TEXT NOT NULL,result TEXT NOT NULL,distribution TEXT NOT NULL,
      version TEXT NOT NULL,received_at INTEGER NOT NULL,PRIMARY KEY(tenant,provider,event_key)
    ) STRICT;`);
  }
  transaction(fn){this.db.exec('BEGIN IMMEDIATE');try{const v=fn();this.db.exec('COMMIT');return v;}catch(e){this.db.exec('ROLLBACK');throw e;}}
  plan(objective){
    const lanes={discover:['intelligence','privacy'],attract:['traffic','measurement'],convert:['conversion','privacy'],measure:['measurement','data'],operate:['operations']};
    if(typeof objective!=='string'||!own(lanes,objective))fail('invalid_objective');
    return {objective,modules:PORTFOLIO.modules.filter(m=>lanes[objective].includes(m.lane)).map(m=>({id:m.id,role:m.role,execution:'not_started',blockers:['license_review_pending','live_adapter_or_configuration_pending']})),external_execution:false};
  }
  async status(){
    let packages={operations:[]},runtimeError=null;
    try{packages=await this.worker('capabilities',{});}catch(error){runtimeError=error instanceof PortfolioError?error.code:'native_worker_unavailable';}
    return {product:'Verdugo Digital',workspace:this.workspace,selected_count:50,
      retained_originals:PORTFOLIO.retained_originals,new_identities:44,legacy_preserved:PORTFOLIO.legacy_preserved,
      modules:PORTFOLIO.modules.map(m=>({...m,runtime:packages.operations.filter(p=>m.implemented_operations.includes(p.operation)),
        status:m.implemented_operations.length?'local_operation_implemented_not_live_certified':'adapter_pending'})),
      local_support:packages.operations.filter(p=>p.operation==='email.validate'),runtime_error:runtimeError,
      runs:this.list(),all_fifty_integrated:false,production_ready:false,paid_actions_enabled:false};
  }
  list(){return this.db.prepare('SELECT id,subject_id,state,step,error,started_at,updated_at FROM portfolio_runs WHERE tenant=? ORDER BY started_at DESC,id LIMIT 50').all(this.workspace).map(row=>({...row,receipts:this.db.prepare('SELECT step,provider,distribution,version FROM portfolio_receipts WHERE tenant=? AND run_id=? ORDER BY recorded_at,step').all(this.workspace,row.id)}));}
  receipt(run,step,provider,value){
    if(value.execution!=='original_library'||value.external_side_effects!==false||typeof value.distribution!=='string'||typeof value.version!=='string')fail('invalid_execution_proof',502);
    this.db.prepare('INSERT INTO portfolio_receipts VALUES (?,?,?,?,?,?,?)').run(this.workspace,run,step,provider,value.distribution,value.version,this.clock());
  }
  async verifyReceipt(input){
    if(!input||typeof input!=="object"||Array.isArray(input))fail('invalid_fields');
    if(!['stripe','twilio'].includes(input.provider))fail('unsupported_receipt_provider');
    const provider=input.provider;
    const expected=provider==='stripe'?['provider','raw_body','signature']:['provider','parameters','signature'];
    shape(input,expected);
    const payload=provider==='stripe'?{raw_body:input.raw_body,signature:input.signature}:{parameters:input.parameters,signature:input.signature};
    const proof=await this.worker(provider+'.verify_signature',payload);
    if(proof.execution!=='original_library'||proof.external_side_effects!==false||proof.result?.signature_valid!==true)fail('invalid_signature_proof',502);
    if(proof.distribution!==provider || typeof proof.version!=='string')fail('invalid_provider_library_proof',502);
    if(provider==='twilio' && (typeof proof.result.call_sid!=='string'||!/^CA[0-9a-fA-F]{32}$/.test(proof.result.call_sid)||!['queued','ringing','in-progress','completed','busy','failed','no-answer','canceled'].includes(proof.result.call_status)))fail('invalid_twilio_event_identity');
    const eventKey=provider==='stripe'?proof.result.provider_event_id:proof.result.call_sid+':'+proof.result.call_status;
    if(typeof eventKey!=='string'||!(/^[A-Za-z0-9_:-]{3,200}$/).test(eventKey))fail('invalid_provider_event_identity');
    const fingerprint=hash(provider==='stripe'?input.raw_body:input.parameters);
    return this.transaction(()=>{
      const old=this.db.prepare('SELECT fingerprint FROM portfolio_provider_receipts WHERE tenant=? AND provider=? AND event_key=?').get(this.workspace,provider,eventKey);
      if(old&&old.fingerprint!==fingerprint)fail('provider_event_conflict',409);
      if(!old)this.db.prepare('INSERT INTO portfolio_provider_receipts VALUES (?,?,?,?,?,?,?,?)').run(this.workspace,provider,eventKey,fingerprint,JSON.stringify(proof.result),proof.distribution,proof.version,this.clock());
      return {provider,event_key:eventKey,replayed:!!old,signature_verified:true,external_action_executed:false,payment_reconciled:false};
    });
  }
  async capture(input){
    shape(input,['id','lead_id','name','email','source','html','analytics','marketing']);
    if(typeof input.id!=='string'||typeof input.lead_id!=='string'||!uuid.test(input.id)||!uuid.test(input.lead_id)||typeof input.analytics!=='boolean'||typeof input.marketing!=='boolean')fail('invalid_identity_or_consent');
    const normalized={id:input.id.toLowerCase(),lead_id:input.lead_id.toLowerCase(),name:text(input.name,160),email:text(input.email,254),source:text(input.source,80),html:text(input.html,12000),analytics:input.analytics,marketing:input.marketing};
    const fingerprint=hash(normalized),now=this.clock();
    const previous=this.transaction(()=>{
      const old=this.db.prepare('SELECT * FROM portfolio_runs WHERE tenant=? AND id=?').get(this.workspace,normalized.id);
      if(old){
        if(old.fingerprint!==fingerprint)fail('run_id_conflict',409);
        if(old.state==='running'&&now-old.updated_at>120000){
          this.db.prepare("UPDATE portfolio_runs SET state='interrupted',error='worker_interrupted',updated_at=? WHERE tenant=? AND id=? AND state='running'").run(now,this.workspace,old.id);
          old.state='interrupted';
        }
        return old;
      }
      if(this.active>=2)fail('local_capacity_exceeded',429);
      this.db.prepare("INSERT INTO portfolio_runs VALUES (?,?,?,?,'running','email',NULL,?,?)").run(this.workspace,normalized.id,fingerprint,normalized.lead_id,now,now);
      return null;
    });
    if(previous)return {run_id:previous.id,lead_id:previous.subject_id,state:previous.state,replayed:true,external_requests:0};
    this.active++;
    try{
      const email=await this.worker('email.validate',{email:normalized.email});
      this.receipt(normalized.id,'email','email-validator-support',email);
      if(email.result?.syntax_valid!==true || typeof email.result.email!=='string')fail('invalid_email_receipt',502);
      this.db.prepare("UPDATE portfolio_runs SET step='document',updated_at=? WHERE tenant=? AND id=?").run(this.clock(),this.workspace,normalized.id);
      const document=await this.worker('document.convert_html',{html:normalized.html});
      this.receipt(normalized.id,'document','markitdown',document);
      if(typeof document.result?.markdown!=='string'||document.result.markdown.length>20000)fail('invalid_document_receipt',502);
      this.db.prepare("UPDATE portfolio_runs SET step='text',updated_at=? WHERE tenant=? AND id=?").run(this.clock(),this.workspace,normalized.id);
      const segmented=await this.worker('text.segment_es',{text:document.result.markdown});
      this.receipt(normalized.id,'text','spacy',segmented);
      if(!Array.isArray(segmented.result?.sentences))fail('invalid_text_receipt',502);
      // Existing authoritative lead ledger, same UUID/workspace/consent. No remote send.
      const receipt=this.store.ingest(this.workspace,{id:normalized.id,type:'lead.created',lead_id:normalized.lead_id,
        data:{name:normalized.name,email:email.result.email,source:normalized.source,analytics:normalized.analytics,marketing:normalized.marketing}},[]);
      this.db.prepare("UPDATE portfolio_runs SET state='completed',step='lead_registered',updated_at=? WHERE tenant=? AND id=?").run(this.clock(),this.workspace,normalized.id);
      return {run_id:normalized.id,lead_id:normalized.lead_id,state:'completed',replayed:receipt.replayed,
        sentence_count:segmented.result.sentences.length,external_requests:0,
        buying_intent_verified:false,mailbox_verified:false,consent_inferred:false,all_fifty_integrated:false};
    }catch(error){
      const code=error instanceof PortfolioError?error.code:'existing_core_or_native_operation_failed';
      this.db.prepare("UPDATE portfolio_runs SET state='failed',error=?,updated_at=? WHERE tenant=? AND id=?").run(code,this.clock(),this.workspace,normalized.id);
      if(error instanceof PortfolioError)throw error;
      throw new PortfolioError(code,422);
    }finally{this.active--;}
  }
}

export function createPortfolioRouter({store,workspace,send,readJson,worker=nativeWorker}){
  const portfolio=store?new Portfolio(store,{workspace,worker}):null;
  const page=readFileSync(new URL('../public/portfolio.html',import.meta.url));
  const script=readFileSync(new URL('../public/portfolio.mjs',import.meta.url));
  return async function(req,res,url){
    if(req.method==='GET' && req.url==='/portfolio'){send(res,200,page,'text/html; charset=utf-8');return true;}
    if(req.method==='GET' && req.url==='/portfolio.mjs'){send(res,200,script,'text/javascript; charset=utf-8');return true;}
    if(!url.pathname.startsWith('/v1/portfolio'))return false;
    try{
      if(!portfolio)fail('local_store_not_enabled',503);
      if(url.search)fail('invalid_portfolio_query');
      if(req.method==='GET'&&url.pathname==='/v1/portfolio')send(res,200,await portfolio.status());
      else if(req.method==='POST'&&url.pathname==='/v1/portfolio/plan'){
        const input=await readJson(req);shape(input,['objective']);send(res,200,portfolio.plan(input.objective));
      }else if(req.method==='POST'&&url.pathname==='/v1/portfolio/receipts'){
        send(res,200,await portfolio.verifyReceipt(await readJson(req)));
      }else if(req.method==='POST'&&url.pathname==='/v1/portfolio/opportunities'){
        const result=await portfolio.capture(await readJson(req));send(res,result.replayed?200:201,result);
      }else send(res,404,{error:'unsupported_portfolio_route'});
    }catch(error){const parseError=['json_content_type_required','body_too_large','invalid_json','invalid_request_body','aborted_request'].includes(error?.code);send(res,error instanceof PortfolioError||parseError?error.status:500,{error:error instanceof PortfolioError||parseError?error.code:'portfolio_internal_error'});}
    return true;
  };
}
