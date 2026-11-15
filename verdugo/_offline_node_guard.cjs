const deny=()=>{throw new Error('Offline original validation');};
const net=require('node:net'),tls=require('node:tls'),dns=require('node:dns'),http=require('node:http'),https=require('node:https'),child=require('node:child_process');
net.connect=net.createConnection=net.Socket.prototype.connect=net.Server.prototype.listen=deny;tls.connect=deny;
for(const key of Object.keys(dns))if(/^(lookup|resolve|reverse)/.test(key)&&typeof dns[key]==='function')dns[key]=deny;
for(const key of Object.keys(dns.promises))if(typeof dns.promises[key]==='function')dns.promises[key]=deny;
http.request=http.get=https.request=https.get=deny;
for(const key of ['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork'])child[key]=deny;
globalThis.fetch=deny;globalThis.WebSocket=deny;require('node:module').syncBuiltinESMExports();
