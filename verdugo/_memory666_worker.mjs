// Fixed development MCP session; no caller-selected tools, files or endpoints.
import { mkdtemp, rm } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

if (process.versions.node !== '24.22.1') throw new Error('Unexpected Node version');
const home = process.env.VERDUGO_MEMORY666_ROOT;
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const p = JSON.parse(Buffer.concat(chunks).toString('utf8'));
const { Client, InMemoryTransport } = await import(pathToFileURL(path.join(home, 'node_modules/@modelcontextprotocol/client/dist/index.mjs')));
const { createServer } = await import(pathToFileURL(path.join(home, 'upstream/src/memory/dist/index.js')));
const dir = await mkdtemp(path.join(process.cwd(), 'memory666-'));
const names = p.statuses.map((_, i) => `stage_${i}`);
const entities = names.map((name, i) => ({ name, entityType: 'synthetic_stage', observations: [p.statuses[i]] }));
const relations = p.edges.map(([from, to]) => ({ from: names[from], to: names[to], relationType: 'depends_on' }));
let client, server, calls = 0;
async function connect() {
  server = createServer(path.join(dir, 'graph.jsonl'));
  client = new Client({ name: 'verdugo-synthetic-client', version: '1.0.0' });
  const [c, s] = InMemoryTransport.createLinkedPair();
  await server.connect(s); await client.connect(c);
  const tools = (await client.listTools()).tools.map(t => t.name);
  for (const name of ['create_entities', 'create_relations', 'search_nodes', 'read_graph', 'delete_entities']) {
    if (!tools.includes(name)) throw new Error('Missing original MCP tool');
  }
}
async function call(name, args) {
  ++calls;
  const r = await client.callTool({ name, arguments: args });
  if (r.isError || !r.structuredContent) throw new Error('Original MCP tool failed');
  return r.structuredContent;
}
try {
  await connect();
  const created = await call('create_entities', { entities: [...entities, entities[0]] });
  const linked = await call('create_relations', { relations });
  const found = await call('search_nodes', { query: p.query, limit: 16, observationLimit: 1 });
  if (created.entities.length !== entities.length) throw new Error('Original entity deduplication failed');
  await client.close(); await server.close();
  await connect();
  const restored = await call('read_graph', {});
  if (restored.entities.length !== created.entities.length || restored.relations.length !== linked.relations.length) {
    throw new Error('Temporary original graph did not survive server restart');
  }
  await call('delete_entities', { entityNames: names });
  const empty = await call('read_graph', {});
  if (empty.entities.length || empty.relations.length) throw new Error('Original graph cleanup failed');
  process.stdout.write(JSON.stringify({
    original_sdk: 'servers', sdk_version: '2.1.1', original_tools_called: calls,
    entity_count: created.entities.length, unique_relation_count: linked.relations.length,
    duplicate_entities_skipped: 1, duplicate_relations_skipped: relations.length - linked.relations.length,
    matching_entity_count: found.entities.length, matching_incident_relation_count: found.relations.length,
    temporary_server_restart_verified: true, sdk_graph_deleted: true,
    transport: 'original_in_memory_development', durable_agent_memory: false,
    raw_graph_persisted_by_engine: false, dataset: 'demo', dry_run: true, llm_calls: 0,
    autonomous_agent: false, external_calls_made: false, external_execution_authorized: false,
    operator_approval_required: true, approvals_granted: 0
  }));
} finally {
  await client?.close(); await server?.close(); await rm(dir, { recursive: true, force: true });
}
