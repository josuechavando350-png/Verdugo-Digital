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
if (service === 'lighthouse') {
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
