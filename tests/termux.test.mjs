import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
const root=fileURLToPath(new URL('../',import.meta.url));
test('shell scripts parse in Bash',()=>{
  for(const name of ['termux-install.sh','termux-run.sh','termux-doctor.sh']){
    const p=spawnSync('bash',['-n',join(root,'scripts',name)]);
    assert.equal(p.status,0,String(p.stderr));
  }
});
test('unconfigured providers remain unverified',()=>{
  const home=mkdtempSync(join(tmpdir(),'vd-termux-'));
  try {
    const p=spawnSync(process.execPath,[join(root,'scripts/termux-status.mjs'),'--json'],{env:{...process.env,HOME:home},encoding:'utf8'});
    assert.equal(p.status,0,p.stderr);
    const result=JSON.parse(p.stdout);
    assert.equal(result.systems.length,10);
    assert.ok(result.systems.every(x=>x.state==='not_configured'));
    assert.equal(result.e2e_verified,false);
  } finally {rmSync(home,{recursive:true,force:true});}
});
test('strict verification fails closed without real integration',()=>{
  const home=mkdtempSync(join(tmpdir(),'vd-termux-'));
  try {
    const p=spawnSync(process.execPath,[join(root,'scripts/termux-status.mjs'),'--require-ten-live'],{env:{...process.env,HOME:home},encoding:'utf8'});
    assert.equal(p.status,2,p.stderr);
    assert.match(p.stdout,/E2E real: NO/);
  } finally {rmSync(home,{recursive:true,force:true});}
});
