import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { getStatus } from '../lib/control-plane.mjs';
const catalog=JSON.parse(readFileSync(new URL('../stack/catalog.json', import.meta.url),'utf8'));
let endpoints={};
try {
  endpoints=JSON.parse(readFileSync(join(homedir(),'.config','verdugo','endpoints.json'),'utf8'));
  if (!endpoints || Array.isArray(endpoints) || typeof endpoints!=='object') throw Error('invalid');
} catch (e) {
  if (e.code!=='ENOENT') { console.error('endpoints.json inválido'); process.exit(3); }
}
const status=await getStatus(catalog,endpoints);
if (process.argv.includes('--json')) console.log(JSON.stringify(status,null,2));
else {
  for (const s of status.systems) console.log(s.id.padEnd(13)+' '+s.state.padEnd(16)+' HTTP '+(s.status_code??'-'));
  console.log('Integración E2E real: NO verificada');
}
if (process.argv.includes('--require-ten-live') && (!status.e2e_verified || status.systems.some(s=>s.state!=='reachable'))) process.exitCode=2;
