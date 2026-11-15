const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),child=require('node:child_process');
const raw=fs.readFileSync(0);if(raw.length>65536)throw Error('Input budget');const {service,params:p}=JSON.parse(raw);
const root=process.env.VERDUGO_OWNED_HTTP_ROOT;const token=crypto.randomBytes(24).toString('hex');
const auth=service==='siteone-crawler'?'Basic '+Buffer.from('verdugo:'+token).toString('base64'):'Bearer '+token;
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const pages=new Map();let port;let calls=0;
if(service==='siteone-crawler'){
 const ids=new Map(p.pages.map((r,i)=>[r.id,i]));
 p.pages.forEach((r,i)=>{const content='<!doctype html><title>'+esc(r.title)+'</title><h1>'+esc(r.title)+'</h1>'+r.links.map((id,j)=>'<a href="'+(ids.has(id)?'/p/'+ids.get(id):'/missing/'+id)+'">'+esc(id)+'</a>').join('');pages.set('/p/'+i,{status:200,body:content});});
 pages.set('/robots.txt',{status:200,body:'User-agent: *\nAllow: /\n',type:'text/plain'});
}else if(service==='sherlock'){
 p.responses.forEach((r,i)=>pages.set('/case/'+i+'/supplied-brand',{status:r.status,body:r.text,type:'text/plain'}));
}else throw Error('Unsupported owned HTTP operation');
const server=http.createServer((req,res)=>{
 if(req.headers.host!=='127.0.0.1:'+port||req.headers.authorization!==auth||!['GET','HEAD'].includes(req.method)){res.writeHead(401);res.end();return;}
 if(++calls>100){res.writeHead(429);res.end();return;}
 const item=pages.get(req.url)||{status:404,body:'Missing'};res.writeHead(item.status,{'Content-Type':item.type||'text/html; charset=utf-8','Cache-Control':'no-store','Connection':'close'});res.end(req.method==='HEAD'?'':item.body);
});
const exec=(exe,args,input)=>new Promise((resolve,reject)=>{const process=child.execFile(exe,args,{cwd:global.process.cwd(),env:{PATH:global.process.env.PATH,HOME:global.process.cwd(),TMPDIR:global.process.cwd(),LANG:'C.UTF-8'},timeout:35000,maxBuffer:2*1024*1024,killSignal:'SIGKILL'},(err,stdout)=>err?reject(Error('Original owned HTTP subprocess failed')):resolve(stdout));if(input!==undefined)process.stdin.end(input);else process.stdin.end();});
(async()=>{
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve)});port=server.address().port;let result;
 try {
  const base='http://127.0.0.1:'+port;
  if(service==='siteone-crawler'){
   const args=['--url='+base+'/p/0','--http-auth=verdugo:'+token,'--workers=1','--max-visited-urls=30','--max-queue-length=60','--max-skipped-urls=60','--max-reqs-per-sec=20','--timeout=3','--disable-all-assets','--analyzer-filter-regex=^$','--output=json','--output-json-file=report.json','--output-html-report=','--output-text-file=','--no-cache','--hide-progress-bar','--no-color'];
   await exec(path.join(root,'bin/siteone-crawler'),args);
   const raw=fs.readFileSync('report.json');if(raw.length>2*1024*1024)throw Error('Report budget');const report=JSON.parse(raw);
   if(!Array.isArray(report.results)||report.results.length>30)throw Error('Original crawl report changed');const counts={};
   for(const row of report.results){const u=new URL(row.url);if(u.origin!==base||!['200','404'].includes(row.status))throw Error('Unexpected crawl destination/status');counts[row.status]=(counts[row.status]??0)+1;}
   if(report.stats.totalUrls!==report.results.length||JSON.stringify(report.stats.countByStatus)!==JSON.stringify(counts))throw Error('Original crawl counts disagree');
   result={pages_in_input:p.pages.length,visited:report.results.length,status_counts:counts,missing_pages:counts['404']??0,remote_site_fetched:false,quality_scores_reported:false,scope:'Original crawler visits generated private HTTP pages and discovers their links; no production website, SEO score or rendering'};
  }else{
   const input={base,token,responses:p.responses.map((r,i)=>({id:r.id,index:i,mode:r.mode,marker:r.marker}))};
   const output=await exec(global.process.env.VERDUGO_SHERLOCK_EXECUTABLE,['-I',path.join(__dirname,'_sherlock_original_worker.py')],JSON.stringify(input));result=JSON.parse(output);
  }
 } finally {server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
 result.owned_http_requests=calls;result.local_server_closed=!server.listening;process.stdout.write(JSON.stringify(result));
})().catch(e=>{server.closeAllConnections();server.close();process.stderr.write(String(e)+'\n');process.exitCode=1;});
