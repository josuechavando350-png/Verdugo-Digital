"""Original TransformerLens cache/intervention on a fixed untrained toy model.

This diagnoses hook behavior, not the reasoning or quality of a pretrained LLM.
No pretrained weights, model paths, user callbacks or raw activations are accepted.
"""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path

from .common import VerdugoError, fields, integer

SPECS = {'transformerlens': ('activations.check', 'transformer-lens', '0.0.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-lens666.json'
CONFIG = dict(d_model=8, d_head=4, n_layers=1, n_ctx=8, n_heads=2,
              d_mlp=16, d_vocab=16, device='cpu', seed=666, init_weights=True,
              normalization_type='LN', act_fn='relu')
NAMES = ('blocks.0.hook_resid_pre', 'blocks.0.hook_resid_post',
         'blocks.0.attn.hook_pattern')


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed activation diagnostic')
    fields(p, ('dataset', 'symbol_ids', 'intervention'))
    if p['dataset'] != 'demo' or p['intervention'] not in ('observe', 'zero_residual'):
        raise VerdugoError('Only synthetic data and fixed interventions supported')
    if not isinstance(p['symbol_ids'], list) or not 2 <= len(p['symbol_ids']) <= 6:
        raise VerdugoError('Two to six synthetic symbols required')
    for value in p['symbol_ids']:
        integer(value, 0, 15)


def verify_source():
    record = json.loads(CONTRACT.read_text())
    dist = metadata.distribution('transformer-lens')
    if dist.version != SPECS['transformerlens'][2]:
        raise VerdugoError('TransformerLens version mismatch')
    for name, version in record['runtime_versions'].items():
        if metadata.version(name) != version:
            raise VerdugoError('TransformerLens dependency version mismatch')
    count = 0
    for entry in record['files']:
        if entry['installed_path']:
            data = dist.locate_file(entry['installed_path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise VerdugoError('Installed TransformerLens differs from original source')
            count += 1
    if count != 375:
        raise VerdugoError('Incomplete TransformerLens source evidence')
    return {'source_commit': record['commit'], 'original_source_files_verified': count}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      WANDB_MODE='disabled', TRANSFORMERLENS_HF_RETRY='0')
    import torch
    from transformer_lens import TransformerBridge, TransformerBridgeConfig
    from transformer_lens.hook_points import HookPoint

    torch.set_num_threads(1)
    model = TransformerBridge.boot_native(TransformerBridgeConfig(**CONFIG),
                                         device='cpu', dtype=torch.float32)
    model.eval()
    inputs = torch.tensor([p['symbol_ids']], dtype=torch.long)
    # This callback is fixed repository code; callers cannot supply any function.
    hooks = [(NAMES[0], lambda value, hook: torch.zeros_like(value))] if p['intervention'] == 'zero_residual' else []
    with torch.no_grad():
        baseline, cache = model.run_with_cache(inputs, return_cache_object=False,
                                               names_filter=list(NAMES))
        changed = model.run_with_hooks(inputs, fwd_hooks=hooks, reset_hooks_end=True)
        restored = model(inputs)
    length = len(p['symbol_ids'])
    if (tuple(baseline.shape) != (1, length, 16) or
            tuple(cache[NAMES[0]].shape) != (1, length, 8) or
            tuple(cache[NAMES[1]].shape) != (1, length, 8) or
            tuple(cache[NAMES[2]].shape) != (1, 2, length, length)):
        raise VerdugoError('Unexpected original activation shape')
    if any(not bool(torch.isfinite(t).all()) for t in (baseline, changed, restored, *cache.values())):
        raise VerdugoError('Nonfinite original activation result')
    pattern = cache[NAMES[2]]
    row_error = float((pattern.sum(dim=-1) - 1).abs().max())
    future_mass = float(torch.triu(pattern, diagonal=1).abs().max())
    restored_error = float((restored - baseline).abs().max())
    remaining = sum(len(m.fwd_hooks) + len(m.bwd_hooks)
                    for m in model.modules() if isinstance(m, HookPoint))
    if remaining or restored_error != 0 or row_error > 1e-6 or future_mass != 0:
        raise VerdugoError('Original causal attention or hook cleanup failed')
    return evidence | {
        'symbol_count': length, 'vocabulary_size': 16, 'requested_activation_count': 3,
        'cache_entry_count_with_aliases': len(cache), 'attention_head_count': 2,
        'toy_model_parameter_count': sum(x.numel() for x in model.parameters()),
        'toy_forward_passes': 3, 'intervention': p['intervention'],
        'max_output_change': float((changed - baseline).abs().max()),
        'max_restored_output_error': restored_error, 'hooks_remaining': remaining,
        'max_attention_row_sum_error': row_error, 'max_future_attention': future_mass,
        'hooks_removed_and_output_restored': True, 'untrained_toy_model': True,
        'pretrained_weights_downloaded': False, 'model_persisted': False,
        'real_llm_reasoning_explained': False, 'quality_calibrated': False,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}
