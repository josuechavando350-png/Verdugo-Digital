"""Original PyRIT message-link validation and invocation matching, locally.

Every message is synthetic and ephemeral. Matching recorded invocation evidence
does not execute a tool, prove completion, or authorize another operation.
"""
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, fields

SPECS = {'pyrit': ('tools.audit', 'pyrit', '1.3.0.dev0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-toolaudit666.json'
TOOLS = ('plan', 'draft', 'send')
OUTCOMES = ('invoked', 'not_invoked', 'missing', 'out_of_order',
            'duplicate_output', 'unmatched_output')


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed tool-audit operation')
    fields(p, ('dataset', 'calls'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic tool records supported')
    if not isinstance(p['calls'], list) or not 1 <= len(p['calls']) <= 8:
        raise VerdugoError('One to eight synthetic calls required')
    for row in p['calls']:
        fields(row, ('tool', 'format', 'outcome', 'simulated'))
        if row['tool'] not in TOOLS or row['format'] not in ('chat', 'responses'):
            raise VerdugoError('Unknown fixed tool or message format')
        if row['outcome'] not in OUTCOMES or type(row['simulated']) is not bool:
            raise VerdugoError('Unknown synthetic outcome or simulated flag')


def verify_source():
    record = json.loads(CONTRACT.read_text())
    dist = metadata.distribution('pyrit')
    if dist.version != SPECS['pyrit'][2]:
        raise VerdugoError('PyRIT version mismatch')
    count = 0
    for entry in record['files']:
        if entry['installed_path']:
            if hashlib.sha256(dist.locate_file(entry['installed_path']).read_bytes()).hexdigest() != entry['sha256']:
                raise VerdugoError('Installed PyRIT code differs from pinned source')
            count += 1
    stamp = json.loads(dist.locate_file('pyrit/_compatibility.json').read_text())
    expected = {'version': SPECS['pyrit'][2], 'commit': record['commit'], 'dirty': False,
                'compatibility_id': SPECS['pyrit'][2] + '+g' + record['commit']}
    if stamp != expected or count == 0:
        raise VerdugoError('PyRIT source build provenance mismatch')
    # The original backend validates matching frontend provenance at build time.
    # This operation never loads or serves that frontend.
    return {'source_commit': record['commit'], 'original_source_files_verified': count,
            'upstream_build_provenance_verified': True}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    from pyrit.models import Message, MessagePiece, ToolExecutionMetadata
    from pyrit.models.messages.tool_content import validate_tool_conversation
    from pyrit.score.true_false.message_tool_call_scorer import match_message_tool_calls

    pieces = []
    def add(role, body, kind, extra=None):
        pieces.append(MessagePiece(role=role, original_value=json.dumps(body),
            original_value_data_type=kind, sequence=len(pieces), not_in_memory=True,
            prompt_metadata=extra or {}))

    for index, row in enumerate(p['calls']):
        call_id = 'fixed_pyrit_call_' + str(index)
        request = ({'type': 'function', 'id': call_id,
                    'function': {'name': row['tool'], 'arguments': '{}'}}
                   if row['format'] == 'chat' else
                   {'type': 'function_call', 'call_id': call_id,
                    'name': row['tool'], 'arguments': '{}'})
        output = {'call_id': ('unmatched' if row['outcome'] == 'unmatched_output' else call_id),
                  'output': 'fixed synthetic result'}
        role = 'simulated_assistant' if row['simulated'] else 'assistant'
        tool_role = 'simulated_tool' if row['simulated'] else 'tool'
        execution = ToolExecutionMetadata(invoked=row['outcome'] != 'not_invoked').to_metadata()
        if row['outcome'] == 'out_of_order':
            add(tool_role, output, 'function_call_output', execution)
        add(role, request, 'function_call')
        if row['outcome'] not in ('missing', 'out_of_order'):
            add(tool_role, output, 'function_call_output', execution)
            if row['outcome'] == 'duplicate_output':
                add(tool_role, output, 'function_call_output', execution)
    valid = True
    try:
        validate_tool_conversation([Message(message_pieces=[piece]) for piece in pieces])
    except ValueError:
        valid = False
    matched = match_message_tool_calls(pieces=pieces) if valid else set()
    if not matched.issubset(TOOLS):
        raise VerdugoError('Unexpected original tool-match result')
    return evidence | {
        'synthetic_call_count': len(p['calls']), 'synthetic_piece_count': len(pieces),
        'message_links_valid': valid, 'recorded_invoked_tool_kind_count': len(matched),
        'recorded_only': True, 'absence_proves_nonexecution': False,
        'successful_completion_proven': False, 'tool_calls_executed': 0,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}
