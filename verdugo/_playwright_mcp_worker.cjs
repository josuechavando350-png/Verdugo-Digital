// Fixed first-party bridge to an actual MCP server and client, no arbitrary tools.
const fs=require('node:fs'),path=require('node:path');
const home=process.env.VERDUGO_LASTNODE_ROOT;
const req=require('node:module').createRequire(path.join(home,'package.json'));
const {chromium}=req('playwright');const {createConnection}=req('@playwright/mcp');
const {Client}=req('@modelcontextprotocol/sdk/client/index.js');
const {InMemoryTransport}=req('@modelcontextprotocol/sdk/inMemory.js');
const raw=fs.readFileSync(0);if(raw.length>32768)throw Error('Input budget');const p=JSON.parse(raw);
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:path.join(home,'chromium/chrome-linux64/chrome'),args:['--disable-dev-shm-usage']});
 try {
  const context=await browser.newContext({javaScriptEnabled:false,serviceWorkers:'block',offline:true});
  await context.route('**/*',r=>r.abort());const page=await context.newPage();
  await page.setContent('<!doctype html><html><head><title>'+esc(p.title)+'</title></head><body><main>'+p.headings.map(h=>`<h${h.level}>${esc(h.text)}</h${h.level}>`).join('')+p.buttons.map(b=>'<button>'+esc(b)+'</button>').join('')+'</main></body></html>');
  const server=await createConnection({capabilities:['core'],browser:{browserName:'chromium',isolated:false,contextOptions:{javaScriptEnabled:false}},outputMode:'stdout'},async()=>context);
  const client=new Client({name:'verdugo-fixed-client',version:'0.21.0'},{capabilities:{}});
  const [ct,st]=InMemoryTransport.createLinkedPair();await server.connect(st);await client.connect(ct);
  try {
   const result=await client.callTool({name:'browser_snapshot',arguments:{}});
   if(result.isError||!Array.isArray(result.content)){
    if(process.env.VERDUGO_MCP_PROBE==='1')process.stderr.write(JSON.stringify(result).slice(0,6000)+'\n');
    throw Error('Original MCP tool failed');
   }
   const text=result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n');
   if(text.length>24000)throw Error('MCP output budget');
   const snapshot=text.match(/### Snapshot\s*\n```yaml\n([\s\S]*?)```/);
   if(!snapshot)throw Error('Original snapshot format changed');
   const headings=[...snapshot[1].matchAll(/^-?\s*- heading .*\[level=(\d)\]/gm)].map(x=>Number(x[1]));
   const buttons=[...snapshot[1].matchAll(/^\s*- button\b/gm)].length;
   if(!snapshot[1].includes('main'))throw Error('Original document snapshot absent');
   process.stdout.write(JSON.stringify({headings:headings.length,heading_levels:headings,buttons,mcp_tool:'browser_snapshot',browser_started:true,javascript_enabled:false,remote_page_fetched:false,scope:'Original MCP accessibility snapshot of supplied structured content; not a live website audit'}));
  } finally {await client.close();await server.close();}
 } finally {await browser.close();}
})().catch(e=>{process.stderr.write(String(e)+'\n');process.exitCode=1});
