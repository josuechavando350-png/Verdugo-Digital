// Fixed offline recipes. No caller-selected code, import, command or destination.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire, syncBuiltinESMExports} from 'node:module';
import {pathToFileURL} from 'node:url';
import net from 'node:net';
import tls from 'node:tls';
import dns from 'node:dns';
import http from 'node:http';
import https from 'node:https';
import child from 'node:child_process';

const deny = () => { throw new Error('Offline recipe'); };
net.connect = net.createConnection = net.Socket.prototype.connect = net.Server.prototype.listen = deny;
tls.connect = deny;
for (const key of Object.keys(dns)) if (/^(lookup|resolve|reverse)/.test(key) && typeof dns[key] === 'function') dns[key] = deny;
for (const key of Object.keys(dns.promises)) if (typeof dns.promises[key] === 'function') dns.promises[key] = deny;
http.request = http.get = https.request = https.get = deny;
for (const key of ['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork']) child[key] = deny;
globalThis.fetch = deny; globalThis.WebSocket = deny;
syncBuiltinESMExports();
const require = createRequire(path.join(process.env.VERDUGO_NATIVE_ROOT, 'package.json'));
const load = async name => import(pathToFileURL(name === '@jdevalk/seo-graph-core'
  ? path.join(process.env.VERDUGO_NATIVE_ROOT, 'node_modules', name, 'dist/index.js') : require.resolve(name)).href);
const data = fs.readFileSync(0);
if (data.length > 65536) throw new Error('Input budget');
const {service, params:p} = JSON.parse(data);
let result;
if (service === 'promptfoo') {
  process.env.PROMPTFOO_DISABLE_TELEMETRY='1';process.env.PROMPTFOO_DISABLE_UPDATE='1';
  process.env.PROMPTFOO_CONFIG_DIR=path.join(process.cwd(),'promptfoo');
  const m=await load('promptfoo');
  // This provider supplies caller-provided text. It never pretends to be a model.
  const provider={id:()=> 'verdugo-supplied-response',callApi:async()=>({output:p.text,cost:0,tokenUsage:{total:0,prompt:0,completion:0}})};
  const write=process.stdout.write;
  process.stdout.write=()=>true;
  try {
    const evaluation=await m.evaluate({prompts:['Fixed offline supplied-response assertion'],providers:[provider],
      tests:[{assert:[{type:'contains-all',value:p.required_terms}]}]}, {writeResults:false,cache:false});
    const summary=await evaluation.toEvaluateSummary();
    if(summary.stats.errors || summary.results.length!==1)throw new Error('Native evaluation failed');
    const grade=summary.results[0].gradingResult;
    if(typeof grade?.pass!=='boolean')throw new Error('Unexpected native grade');
    result={passed:grade.pass, score:grade.score, required_terms:p.required_terms.length,
      llm_calls:0,provider:'supplied_text',semantic_correctness_verified:false,scope:'original contains-all assertion; case-sensitive literal phrases'};
  } finally {process.stdout.write=write;}
} else if (service === 'log4brains') {
  fs.mkdirSync('adrs');
  fs.writeFileSync('.log4brains.yml','project:\n  name: Verdugo\n  tz: UTC\n  adrFolder: adrs\n  repository:\n    url: https://example.invalid/verdugo/repo\n    provider: generic\n    viewFileUriPattern: /blob/main/%path\n');
  p.decisions.forEach((row,i)=>fs.writeFileSync(`adrs/20260101-decision-${i}.md`,
    `# ${row.title}\n\n* Status: ${row.status}\n* Date: 2026-01-01\n\n## Context\n\nSupplied decision metadata only.\n`));
  const m=await load('@log4brains/core');
  const rows=await m.Log4brains.create(process.cwd()).searchAdrs();
  if(rows.length!==p.decisions.length)throw new Error('Decision count mismatch');
  const counts={};for(const row of rows){if(!['proposed','accepted'].includes(row.status))throw new Error('Unexpected status');counts[row.status]=(counts[row.status]??0)+1;}
  result={decisions_in_input:rows.length,status_counts:counts,published:false,repository_modified:false,
    scope:'original ADR parser over temporary supplied records; no actual decision approval'};
} else if (service === 'lighthouse') {
  const {default:Description} = await load('lighthouse/core/audits/seo/meta-description.js');
  const audit = Description.audit({MetaElements:p.descriptions.map(content=>({name:'description',content}))});
  result = {audit_id:'meta-description', score:audit.score, descriptions_in_input:p.descriptions.length,
    scope:'Lighthouse original meta-description audit over supplied artifacts; first description only',
    browser_launched:false, page_fetched:false, performance_audited:false, search_ranking_verified:false};
} else if (service === 'slidev') {
  const m = await load('@slidev/parser');
  const parsed = await m.parse(p.text, 'supplied.md', [], {noParseYAML:true});
  if (parsed.slides.length > 100) throw new Error('Slide budget exceeded');
  result = {slides:parsed.slides.map(s=>({title:s.title??null, content:s.content, notes:s.note??null})),
    count:parsed.slides.length, rendered:false, published:false, external_resources_loaded:false};
} else if (service === 'site-md') {
  const m = await load('site-md');
  result = {...m.convertHtmlToMarkdown(p.html, {url:'https://example.invalid/'}), fetched:false};
} else if (service === 'geo-lint') {
  const m = await load('@ijonis/geo-lint');
  const item = {title:p.title, description:p.description, slug:'document', permalink:'/document/',
    contentType:'blog', locale:'en', filePath:'document.md', body:p.text, rawContent:p.text};
  const rows = await m.lintQuiet({projectRoot:process.cwd(), config:{siteUrl:'https://example.invalid',
    contentPaths:[], imageDirectories:[], staticRoutes:['/document/'], i18n:{locales:['en'],defaultLocale:'en'}},
    adapter:m.createAdapter(() => [item])});
  result = {issues:rows.length, errors:rows.filter(r=>r.severity==='error').length,
    warnings:rows.filter(r=>r.severity==='warning').length,
    rules:[...new Set(rows.map(r=>r.rule))].sort(), language:'en', search_ranking_verified:false};
} else if (service === 'seo-graph') {
  const m = await load('@jdevalk/seo-graph-core');
  const site='https://'+p.host, ids=m.makeIds({siteUrl:site});
  const items=p.entries.map(e=>({name:e.name,url:site+'/'+e.slug+'/'}));
  const crumb=m.buildBreadcrumbList({url:items.at(-1).url,items},ids);
  result={graph:m.assembleGraph([crumb]), entries:items.length, published:false};
} else if (service === 'structured-data-validator') {
  const {default:Validator}=await load('@adobe/structured-data-validator');
  const rows=await new Validator().validate({jsonld:{BreadcrumbList:p.graph['@graph']},errors:[]});
  result={issues:rows.length, errors:rows.filter(r=>r.severity==='ERROR').length,
    warnings:rows.filter(r=>r.severity==='WARNING').length,
    fields:[...new Set(rows.flatMap(r=>r.fieldNames??[]))].sort(),
    scope:'BreadcrumbList and its ListItems; JSON-LD', search_eligibility_verified:false};
} else throw new Error('Unknown fixed recipe');
const encoded=JSON.stringify(result);
if (Buffer.byteLength(encoded)>1024*1024) throw new Error('Output budget');
process.stdout.write(encoded);
