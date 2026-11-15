// Fixed original SDK workflow over synthetic counts; no caller-provided code.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

if (process.versions.node !== '24.22.1') throw new Error('Unreviewed Node version');
// Upstream starts a model-registry fetch at import outside production mode.
if (process.env.NODE_ENV !== 'production') throw new Error('Automatic refresh must be disabled');
const home = process.env.VERDUGO_VOLT666_ROOT;
const require = createRequire(path.join(home, 'package.json'));
const m = await import(pathToFileURL(path.join(home, 'node_modules/@voltagent/core/dist/index.mjs')).href);
const {z} = require('zod');
const raw = fs.readFileSync(0);
if (raw.length > 8192) throw new Error('Input budget exceeded');
const p = JSON.parse(raw);
const input = z.object({dataset:z.literal('demo'), target_clients:z.number().int().min(1).max(10000),
  simulated_median:z.number().int().min(0).max(20000), observed_clients:z.number().int().min(0).max(20000),
  observed_contacts:z.number().int().min(0).max(20000)}).strict();
input.parse(p);
if (p.observed_clients > p.observed_contacts) throw new Error('Inconsistent counts');
const schema = z.object({difference_from_median:z.number().int(), target_reached:z.boolean(),
  review_recommendation:z.enum(['review_shortfall','review_before_execution'])}).strict();
const observability = new m.VoltAgentObservability({serviceName:'verdugo-synthetic-review',
  storage:new m.InMemoryObservabilityAdapter({maxSpans:30}),
  voltOpsSync:{sampling:{strategy:'never'}}, flushOnFinishStrategy:'never'});
const memory = new m.Memory({storage:new m.InMemoryStorageAdapter()});
const seen = [];
try {
  const flow = m.createWorkflowChain({id:'verdugo-fixed-review', name:'Synthetic measurement review',
    input, result:schema, memory, observability, disableCheckpointing:true})
    .andThen({id:'compare', retries:0, execute:async ({data}) => {
      seen.push('compare');
      return {difference_from_median:data.observed_clients-data.simulated_median,
        target_reached:data.observed_clients>=data.target_clients};
    }})
    .andThen({id:'review', retries:0, execute:async ({data}) => {
      seen.push('review');
      return {...data, review_recommendation:(!data.target_reached || data.difference_from_median<0)
        ? 'review_shortfall' : 'review_before_execution'};
    }});
  const output = await flow.run(p);
  if (output.status !== 'completed' || seen.join(',') !== 'compare,review') throw new Error('Original workflow failed');
  const result = schema.parse(output.result);
  process.stdout.write(JSON.stringify({...result, fixed_sdk_steps:2, original_sdk:'voltagent',
    sdk_version:'2.11.1', dataset:'demo', dry_run:true, llm_calls:0, autonomous_agent:false,
    external_calls_made:false, external_execution_authorized:false, operator_approval_required:true,
    real_observations_verified:false, storage:'ephemeral_memory', remote_telemetry_enabled:false}));
} finally {
  await observability.shutdown();
}
