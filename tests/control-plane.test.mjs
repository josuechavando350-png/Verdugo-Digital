import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import http from 'node:http';
import { checkProvider, createServer, EXPECTED, getStatus, validateCatalog } from '../lib/control-plane.mjs';

const catalog = { projects: EXPECTED.map(id => ({ id, purpose: `Project ${id}`, domain: 'test', upstream_url: `https://github.com/${id}` })) };
let provider, app, mockPort, appPort;
const token = 'an-example-very-long-control-plane-secret';

before(async () => {
  provider = http.createServer((req, res) => { res.writeHead(req.url === '/down' ? 503 : 200); res.end('OK'); });
  await new Promise(resolve => provider.listen(0, '127.0.0.1', resolve));
  mockPort = provider.address().port;
  const endpoints = Object.fromEntries(EXPECTED.map(id => [id, `http://127.0.0.1:${mockPort}/${id}`]));
  app = createServer({ catalog, endpoints, token });
  await new Promise(resolve => app.listen(0, '127.0.0.1', resolve));
  appPort = app.address().port;
});
after(async () => {
  await Promise.all([new Promise(resolve => app.close(resolve)), new Promise(resolve => provider.close(resolve))]);
});

test('exactly ten required providers', () => { assert.equal(validateCatalog(catalog).length, 10); assert.throws(() => validateCatalog({ projects: [] })); });
test('control plane rejects unauthenticated access', async () => {
  const response = await fetch(`http://127.0.0.1:${appPort}/v1/systems`);
  assert.equal(response.status, 401);
});
test('one authenticated API health-checks all ten configured endpoints', async () => {
  const response = await fetch(`http://127.0.0.1:${appPort}/v1/systems`, { headers: { Authorization: `Bearer ${token}` } });
  assert.equal(response.status, 200);
  const result = await response.json();
  assert.deepEqual(result.systems.map(p => p.id), EXPECTED);
  assert.equal(result.systems.filter(p => p.state === 'reachable').length, 10);
  assert.equal(result.e2e_verified, false);
  assert.equal(result.systems.filter(p => p.integration_verified).length, 0);
});
test('no configured provider is mislabelled as installed', async () => {
  const result = await getStatus(catalog, {});
  assert.equal(result.systems.filter(p => p.state === 'not_configured').length, 10);
});
test('protects against URL userinfo and arbitrary plaintext hosts', async () => {
  for (const url of ['http://example.com', 'http://user:pass@localhost:3000', 'https://host.invalid?token=x']) {
    assert.equal((await checkProvider(url)).state, 'unreachable');
  }
});

test('serves dashboard on loopback without exposing token', async () => {
  const response=await fetch('http://127.0.0.1:'+appPort+'/');
  assert.equal(response.status,200);
  assert.match(response.headers.get('content-security-policy'),/frame-ancestors/);
  const content=await response.text();
  assert.match(content,/Verdugo Digital/);
  assert.doesNotMatch(content,/an-example-very-long-control-plane-secret/);
});
