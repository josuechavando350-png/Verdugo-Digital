"""Original LM Format Enforcer prefix checks against a fixed finite language."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import string

from .common import VerdugoError, fields
from .local_native import checked

SPECS = {'lm-format-enforcer': ('prefix.check', 'lm-format-enforcer', '0.11.3')}
EXTRA = {'lm-format-enforcer': {'interegular': '0.3.3'}}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-prefix666.json'
SCHEMA = {'type': 'object', 'properties': {
    'decision': {'type': 'string', 'enum': ['review', 'defer']},
    'mode': {'type': 'string', 'enum': ['dry_run']}},
    'required': ['decision', 'mode'], 'additionalProperties': False}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed prefix operation')
    fields(p, ('dataset', 'cases'))
    if p['dataset'] != 'demo' or not isinstance(p['cases'], list) or not 1 <= len(p['cases']) <= 8:
        raise VerdugoError('One to eight synthetic prefix cases required')
    for case in p['cases']:
        fields(case, ('decision', 'mode', 'cut'))
        if case['decision'] not in ('review', 'defer', 'execute') or case['mode'] not in ('dry_run', 'send'):
            raise VerdugoError('Unsupported synthetic prefix values')
        if case['cut'] not in ('complete', 'value_prefix', 'object_prefix', 'bad_suffix'):
            raise VerdugoError('Unsupported synthetic prefix cut')


def verify_source():
    record = json.loads(CONTRACT.read_text())
    dist = metadata.distribution('lm-format-enforcer')
    if dist.version != SPECS['lm-format-enforcer'][2]:
        raise VerdugoError('LM Format Enforcer version mismatch')
    count = 0
    for entry in record['files']:
        if entry['installed_path']:
            data = checked(Path(dist.locate_file(entry['installed_path']))).read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise VerdugoError('Installed prefix parser differs from original source')
            count += 1
    if count != record['installed_source_count']:
        raise VerdugoError('Incomplete prefix source evidence')
    dep = metadata.distribution('interegular')
    if dep.version != '0.3.3':
        raise VerdugoError('Prefix dependency version mismatch')
    for entry in record['dependency_files']:
        data = checked(Path(dep.locate_file(entry['path']))).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise VerdugoError('Prefix dependency artifact changed')
    return {'source_commit': record['commit'], 'original_source_files_verified': count,
            'dependency_files_verified': len(record['dependency_files'])}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source()
    from lmformatenforcer import JsonSchemaParser, CharacterLevelParserConfig
    config = CharacterLevelParserConfig(alphabet=string.printable,
        max_consecutive_whitespaces=2, force_json_field_order=True, max_json_array_length=2)
    documents = [json.dumps({'decision': d, 'mode': 'dry_run'}, separators=(',', ':'))
                 for d in ('review', 'defer')]
    viable = []; complete = []; rejections = []
    for case in p['cases']:
        payload = json.dumps({'decision': case['decision'], 'mode': case['mode']}, separators=(',', ':'))
        if case['cut'] == 'value_prefix':
            payload = payload[:-2]
        elif case['cut'] == 'object_prefix':
            payload = payload[:12]
        elif case['cut'] == 'bad_suffix':
            payload += 'x'
        parser = JsonSchemaParser(SCHEMA, config)
        rejected_at = None
        for offset, char in enumerate(payload):
            if char not in parser.get_allowed_characters():
                rejected_at = offset
                break
            parser = parser.add_character(char)
        possible = rejected_at is None
        finished = possible and parser.can_end()
        if possible != any(d.startswith(payload) for d in documents) or finished != (payload in documents):
            raise VerdugoError('Original prefix parser differs from fixed-language reference')
        reference_rejection = next((i for i in range(len(payload))
            if not any(d.startswith(payload[:i+1]) for d in documents)), None)
        if rejected_at != reference_rejection:
            raise VerdugoError('Original prefix rejection offset differs from reference')
        viable.append(possible); complete.append(finished); rejections.append(rejected_at)
    return evidence | {'case_count': len(viable), 'viable_count': sum(viable),
        'complete_count': sum(complete), 'rejected_count': len(viable)-sum(viable),
        'viable_indices': [i for i, v in enumerate(viable) if v],
        'complete_indices': [i for i, v in enumerate(complete) if v],
        'first_rejection_offsets': rejections, 'independent_finite_language_verified': True,
        'vocabulary_lookup_used': False, 'raw_payloads_persisted': False,
        'syntactic_validity_grants_permission': False, 'content_truth_verified': False,
        'model_weights_loaded': False, 'original_sdk': service, 'sdk_version': SPECS[service][2],
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0, 'business_outcome_proven': False}
