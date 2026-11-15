"""Original Invariant local policy parser/evaluator over fixed synthetic traces.

The temporal private-read/send rule detects an ordered pattern, not data leakage,
causation, prompt injection, or actual permission to execute an operation.
"""
from collections import Counter
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, fields

SPECS = {'invariant': ('trace.check', 'invariant-ai', '0.3.5')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-trace666.json'
RULES = ('review_missing', 'reconcile_first', 'private_before_send')
POLICY = '''
raise PolicyViolation("review_missing") if:
    (call: ToolCall)
    call.function.name == "send"
    call.function.arguments.hypothetical_review == False

raise PolicyViolation("reconcile_first") if:
    (call: ToolCall)
    call.function.name == "send"
    call.function.arguments.previous_state != "failed"

raise PolicyViolation("private_before_send") if:
    (a: ToolCall) -> (b: ToolCall)
    a.function.name == "read_private"
    b.function.name == "send"
'''


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed trace-check operation')
    fields(p, ('dataset', 'events'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic traces supported')
    if not isinstance(p['events'], list) or not 1 <= len(p['events']) <= 12:
        raise VerdugoError('One to twelve synthetic events required')
    for event in p['events']:
        fields(event, ('kind', 'previous_state', 'hypothetical_review'))
        if event['kind'] not in ('read_public', 'read_private', 'draft', 'send'):
            raise VerdugoError('Unknown fixed event kind')
        if event['previous_state'] not in ('failed', 'running', 'uncertain'):
            raise VerdugoError('Unknown fixed synthetic state')
        if type(event['hypothetical_review']) is not bool:
            raise VerdugoError('Hypothetical review must be a boolean')


def verify_source():
    record = json.loads(CONTRACT.read_text())
    counts = {}
    for source in record['sources']:
        dist = metadata.distribution(source['distribution'])
        if dist.version != source['version']:
            raise VerdugoError('Invariant dependency version mismatch')
        count = 0
        for entry in source['files']:
            if entry['installed_path']:
                if hashlib.sha256(dist.locate_file(entry['installed_path']).read_bytes()).hexdigest() != entry['sha256']:
                    raise VerdugoError('Invariant installed source differs from pinned commit')
                count += 1
        if count == 0:
            raise VerdugoError('Missing original Invariant source evidence')
        counts[source['distribution']] = count
    return {'source_commit': record['sources'][0]['commit'],
            'original_source_files_verified': sum(counts.values()),
            'source_files_by_distribution': counts}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    # Policy can choose a remote engine. LocalPolicy explicitly selects the
    # original local parser, type checker and RuleSet interpreter.
    from invariant.analyzer import LocalPolicy
    messages = [{'role': 'assistant', 'content': None, 'tool_calls': [{
        'id': 'fixed_trace_' + str(index), 'type': 'function',
        'function': {'name': event['kind'], 'arguments': {
            'previous_state': event['previous_state'],
            'hypothetical_review': event['hypothetical_review']}}}]}
        for index, event in enumerate(p['events'])]
    result = LocalPolicy.from_string(POLICY).analyze(messages)
    counts = Counter()
    for error in result.errors:
        if len(error.args) != 1 or error.args[0] not in RULES or error.kwargs:
            raise VerdugoError('Unexpected original policy result shape')
        counts[error.args[0]] += 1
    return evidence | {
        'synthetic_event_count': len(messages), 'rule_match_count': sum(counts.values()),
        'rule_match_counts': {rule: counts[rule] for rule in RULES},
        'fixed_policy_sha256': hashlib.sha256(POLICY.encode()).hexdigest(),
        'matches_require_review': bool(counts), 'rules_evaluated': len(RULES),
        'ordered_pattern_only': True, 'data_leak_proven': False,
        'tool_calls_executed': 0, 'approvals_granted': 0,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'business_outcome_proven': False}
