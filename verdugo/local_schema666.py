"""Original Guidance/LLGuidance conformance checks for fixed synthetic JSON."""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked

SPECS = {'guidance': ('schema.check', 'guidance', '0.3.2')}
EXTRA = {'guidance': {'llguidance': '1.6.1', 'guidance-stitch': '0.1.5'}}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-schema666.json'
SCHEMA = {'type': 'object', 'properties': {
    'decision': {'enum': ['review', 'defer']}, 'approved': {'const': False},
    'item_count': {'enum': [0, 1, 2, 3]}},
    'required': ['decision', 'approved', 'item_count'], 'additionalProperties': False}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed schema operation')
    fields(p, ('dataset', 'cases'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic enum cases supported')
    if not isinstance(p['cases'], list) or not 1 <= len(p['cases']) <= 8:
        raise VerdugoError('One to eight synthetic cases required')
    for case in p['cases']:
        fields(case, ('decision', 'approved', 'item_count', 'variant'))
        if case['decision'] not in ('review', 'defer', 'execute', 'unknown'):
            raise VerdugoError('Unsupported synthetic decision')
        if not isinstance(case['approved'], bool):
            raise VerdugoError('Synthetic approved value must be boolean')
        integer(case['item_count'], 0, 6)
        if case['variant'] not in ('canonical', 'truncated', 'extra_field', 'string_count'):
            raise VerdugoError('Unsupported synthetic representation')


def verify_source():
    record = json.loads(CONTRACT.read_text())
    dist = metadata.distribution('guidance')
    if dist.version != SPECS['guidance'][2]:
        raise VerdugoError('Guidance version mismatch')
    for name, version in record['runtime_versions'].items():
        if metadata.version(name) != version:
            raise VerdugoError('Guidance dependency version mismatch')
    count = 0
    for entry in record['files']:
        if entry['installed_path']:
            data = checked(Path(dist.locate_file(entry['installed_path'])), budget=8*1024*1024).read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise VerdugoError('Installed Guidance differs from original source')
            count += 1
    if count != record['installed_source_count']:
        raise VerdugoError('Incomplete Guidance source evidence')
    for entry in record['dependency_files']:
        dep = metadata.distribution(entry['distribution'])
        path = Path(dep.locate_file(entry['path']))
        data = checked(path, budget=32*1024*1024).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise VerdugoError('Guidance dependency artifact changed')
        if entry['path'].endswith('.so') and {p.name for p in path.parent.glob('*.so')} != {path.name}:
            raise VerdugoError('Alternate native parser extension present')
    return {'source_commit': record['commit'], 'original_source_files_verified': count,
            'dependency_files_verified': len(record['dependency_files'])}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    os.environ['LLGUIDANCE_LOG_LEVEL'] = '0'
    import guidance
    from guidance._parser import ByteParser, ByteParserException

    grammar = guidance.json(schema=SCHEMA, separators=(',', ':'), whitespace_flexible=False)
    compiled = grammar.ll_grammar()
    outcomes = []; remaining_threads = 0
    for case in p['cases']:
        value = {key: case[key] for key in ('decision', 'approved', 'item_count')}
        if case['variant'] == 'extra_field':
            value['fixed_extra'] = 0
        elif case['variant'] == 'string_count':
            value['item_count'] = str(value['item_count'])
        payload = json.dumps(value, separators=(',', ':')).encode()
        if case['variant'] == 'truncated':
            payload = payload[:-1]
        parser = ByteParser(compiled)
        try:
            try:
                parser.consume_bytes(payload)
                parser.force_done()
                accepted = parser.matched()
            except ByteParserException:
                accepted = False
        finally:
            # Upstream exposes the executor but has no public abort method.
            # Do not call cleanup() on a rejected, unfinished parser: it requires completion.
            parser.token_parser._threadpool.shutdown(wait=True, cancel_futures=True)
            parser.token_parser._generator.close()
            remaining_threads += sum(t.is_alive() for t in parser.token_parser._threadpool._threads)
        reference = (case['variant'] == 'canonical' and case['decision'] in ('review', 'defer')
                     and case['approved'] is False and case['item_count'] <= 3)
        if accepted != reference:
            raise VerdugoError('Original schema parser differs from enum reference')
        outcomes.append(accepted)
    if remaining_threads:
        raise VerdugoError('Parser worker threads did not stop')
    return evidence | {'case_count': len(outcomes), 'accepted_count': sum(outcomes),
        'rejected_count': len(outcomes)-sum(outcomes),
        'accepted_indices': [i for i, accepted in enumerate(outcomes) if accepted],
        'fixed_schema_count': 1, 'native_parser_used': True,
        'independent_enum_reference_verified': True, 'parser_threads_remaining': remaining_threads,
        'raw_payloads_persisted': False, 'syntactic_validity_grants_permission': False,
        'content_truth_verified': False, 'model_weights_loaded': False, 'quality_calibrated': False,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}
