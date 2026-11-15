"""Compile bounded queue-policy drafts through the original Hatchet SDK.

No Hatchet client, queue, task execution, retry or server is started. The
original SDK merges task defaults and serializes concurrency/idempotency policy.
"""
from datetime import timedelta
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, fields, integer

SPECS = {'hatchet': ('policy.compile', 'hatchet-sdk', '2.0.0a1')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-dispatch666.json'


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed dispatch-policy operation')
    fields(p, ('dataset', 'operation_kind', 'previous_state', 'max_parallel',
               'requested_retries', 'timeout_seconds', 'retention_seconds'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic policy drafts supported')
    if p['operation_kind'] not in ('read', 'write'):
        raise VerdugoError('A fixed operation kind is required')
    if p['previous_state'] not in ('failed', 'running', 'uncertain'):
        raise VerdugoError('A fixed previous synthetic state is required')
    integer(p['max_parallel'], 1, 4)
    integer(p['requested_retries'], 0, 3)
    integer(p['timeout_seconds'], 5, 120)
    integer(p['retention_seconds'], 60, 86400)


def verify_source():
    record = json.loads(CONTRACT.read_text())
    dist = metadata.distribution('hatchet-sdk')
    if dist.version != SPECS['hatchet'][2]:
        raise VerdugoError('Hatchet SDK version mismatch')
    count = 0
    for entry in record['files']:
        if entry['installed_path']:
            if hashlib.sha256(dist.locate_file(entry['installed_path']).read_bytes()).hexdigest() != entry['sha256']:
                raise VerdugoError('Installed Hatchet SDK differs from original pinned source')
            count += 1
    if count == 0:
        raise VerdugoError('Missing original Hatchet source contract')
    return {'source_commit': record['commit'], 'original_source_files_verified': count}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    from hatchet_sdk.runnables.types import TaskDefaults
    from hatchet_sdk.runnables.workflow import compute_task_parameters
    from hatchet_sdk.types.concurrency import ConcurrencyStrategy
    from hatchet_sdk.types.idempotency import StatusBasedIdempotencyConfig
    from hatchet_sdk.contracts.v1.workflows_pb2 import (
        Concurrency, ConcurrencyLimitStrategy, IdempotencyConfig, IdempotencyMethod)

    # Repository policy, not a claimed guarantee supplied by Hatchet. A draft
    # never authorizes a retry. Writes get no automatic retry even if failed.
    reconcile = p['previous_state'] in ('uncertain', 'running')
    retries = 0 if reconcile or p['operation_kind'] == 'write' else p['requested_retries']
    defaults = TaskDefaults(schedule_timeout=timedelta(seconds=120),
        execution_timeout=timedelta(seconds=p['timeout_seconds']),
        retries=p['requested_retries'], backoff_factor=2, backoff_max=timedelta(seconds=60))
    computed = compute_task_parameters(schedule_timeout=None, execution_timeout=None,
        retries=retries, backoff_factor=None, backoff_max=None, task_defaults=defaults)
    concurrency = ConcurrencyStrategy.from_int(p['max_parallel']).to_proto()
    idempotency = StatusBasedIdempotencyConfig(key_expression='input.request_key',
        fallback_ttl=timedelta(seconds=p['retention_seconds'])).to_proto()
    payloads = [concurrency.SerializeToString(deterministic=True),
                idempotency.SerializeToString(deterministic=True)]
    # Exercise the SDK-generated protobuf contract both ways; no RPC client.
    decoded_concurrency = Concurrency.FromString(payloads[0])
    decoded_idempotency = IdempotencyConfig.FromString(payloads[1])
    if decoded_concurrency != concurrency or decoded_idempotency != idempotency:
        raise VerdugoError('Original SDK protobuf round trip changed policy')
    digest = hashlib.sha256()
    for payload in payloads:
        digest.update(len(payload).to_bytes(8, 'big')); digest.update(payload)
    digest.update(computed.model_dump_json().encode())
    return evidence | {
        'compiled_max_parallel': decoded_concurrency.max_runs,
        'compiled_strategy': ConcurrencyLimitStrategy.Name(decoded_concurrency.limit_strategy),
        'compiled_idempotency_method': IdempotencyMethod.Name(decoded_idempotency.method),
        'fallback_retention_ms': decoded_idempotency.ttl_ms,
        'compiled_retries': computed.retries,
        'compiled_execution_timeout_seconds': int(computed.execution_timeout.total_seconds()),
        'compiled_schedule_timeout_seconds': int(computed.schedule_timeout.total_seconds()),
        'requested_retries': p['requested_retries'], 'reconciliation_required': reconcile,
        'recommendation': 'reconcile_before_review' if reconcile else 'request_operator_review',
        'policy_digest': digest.hexdigest(), 'protobuf_round_trip_verified': True,
        'dispatch_policy_draft_only': True, 'server_policy_enforced': False,
        'tasks_dispatched': 0, 'retries_executed': 0, 'approvals_granted': 0,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'business_outcome_proven': False}
