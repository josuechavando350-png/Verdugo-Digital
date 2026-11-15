"""Original Tokenizers native encoding on a bounded synthetic vocabulary."""
import hashlib
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

CANDIDATE_SPECS = {'tokenizers': ('sequence.encode', 'tokenizers', '1.0.0.dev2')}
SPECS = {}  # Quarantined: dependency license outside the configured allowlist.
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-encoding666.json'
RECEIPT = 'share/verdugo-tokenizers/build.json'
PACKAGE = 'lib/python3.12/site-packages'
NATIVE = PACKAGE + '/tokenizers/tokenizers.abi3.so'


def home():
    return checked(Path(runtime_profile.interpreter('tokenizers')).parent.parent, directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.tokenizers666.operator-build.v1' or
            any(receipt.get(key) != record[key] for key in
                ('commit', 'archive_sha256', 'cargo_lock_sha256', 'rust_version',
                 'maturin_version', 'build_environment'))):
        raise VerdugoError('Tokenizers source build receipt mismatch')
    package = checked(root / PACKAGE / 'tokenizers', directory=True)
    if {p.name for p in package.glob('*.so')} != {'tokenizers.abi3.so'}:
        raise VerdugoError('Unexpected alternate Tokenizers extension')
    native = checked(root / NATIVE, budget=64*1024*1024).read_bytes()
    actual = hashlib.sha256(native).hexdigest()
    if actual != receipt.get('native_sha256'):
        raise VerdugoError('Compiled Tokenizers artifact changed')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes() + bytes.fromhex(actual))
    for entry in record['files']:
        if entry['installed_path']:
            actual = hashlib.sha256(checked(root / PACKAGE / entry['installed_path']).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed Tokenizers interface differs from original source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = home(); record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        if runtime_profile.versions(service, [distribution]) != {distribution: version}:
            raise VerdugoError('Tokenizers distribution version mismatch')
        digest = hashlib.sha256(str(root).encode() + artifacts.encode())
        digest.update(checked(root / 'bin/python', budget=64*1024*1024).read_bytes())
        digest.update(checked(root / 'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
        'version_matches': present, 'extra_distributions': {}, 'operation': operation,
        'execution_verified': False, 'runtime_binding': binding}


WORDS = ('plan', 'draft', 'review', 'send', 'unknown')
VOCAB = {'[UNK]': 0, 'plan': 1, 'draft': 2, 'review': 3, 'send': 4, '[PAD]': 5}


def validate(service, operation, p):
    if service not in CANDIDATE_SPECS or operation != CANDIDATE_SPECS[service][0]:
        raise VerdugoError('Unknown fixed encoding operation')
    fields(p, ('dataset', 'word_sequences', 'max_length'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic enumerated words supported')
    integer(p['max_length'], 2, 8)
    if not isinstance(p['word_sequences'], list) or not 1 <= len(p['word_sequences']) <= 4:
        raise VerdugoError('One to four word sequences required')
    for sequence in p['word_sequences']:
        if not isinstance(sequence, list) or not 1 <= len(sequence) <= 12:
            raise VerdugoError('One to twelve enumerated words per sequence required')
        if any(not isinstance(word, str) or word not in WORDS for word in sequence):
            raise VerdugoError('Unsupported synthetic word')


def run(service, p):
    raise VerdugoError('Tokenizers dependency license review unresolved; candidate disabled')


def _historical_unregistered_recipe(service, p):
    raise VerdugoError('Quarantined historical candidate')
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed original Tokenizers build unavailable')
    import tokenizers
    from tokenizers import Tokenizer, Padding, Truncation, models, pre_tokenizers

    if Path(tokenizers.tokenizers.__file__).resolve() != (home() / NATIVE).resolve():
        raise VerdugoError('Unexpected Tokenizers native extension resolution')
    spec = Tokenizer(models.WordLevel(vocab=VOCAB, unk_token='[UNK]'))
    spec.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
    compiled = spec.compile()
    texts = [' '.join(words) for words in p['word_sequences']]
    baseline = compiled.encode_batch(texts, add_special_tokens=False)
    limit = p['max_length']
    encoded = compiled.encode_batch(texts, add_special_tokens=False,
        padding=Padding(length=limit, pad_id=5, pad_token='[PAD]', direction='right'),
        truncation=Truncation(max_length=limit, direction='right'))
    if len(baseline) != len(texts) or len(encoded) != len(texts):
        raise VerdugoError('Unexpected native encoding batch length')
    rows = []
    for words, before, after in zip(p['word_sequences'], baseline, encoded):
        reference = [VOCAB.get(word, 0) for word in words]
        kept = min(len(reference), limit)
        if (before.ids != reference or before.attention_mask != [1]*len(reference) or
                after.ids != reference[:limit] + [5]*(limit-kept) or
                after.attention_mask != [1]*kept + [0]*(limit-kept)):
            raise VerdugoError('Native encoding differs from bounded enum reference')
        rows.append({'input_units': len(before.ids), 'retained_units': sum(after.attention_mask),
            'padded_units': after.attention_mask.count(0), 'discarded_units': len(reference)-kept,
            'unknown_input_units': before.ids.count(0), 'unknown_retained_units': after.ids.count(0)})
    return {'sequence_count': len(rows), 'max_length': limit, 'vocabulary_size': len(VOCAB),
        'sequences': rows, 'native_encoding_reference_verified': True,
        'truncation_and_padding_verified': True, 'raw_encodings_persisted': False,
        'pretrained_vocabulary_loaded': False, 'model_weights_loaded': False,
        'upstream_development_api': True, 'quality_calibrated': False,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': json.loads(CONTRACT.read_text())['commit'],
        'native_artifact_receipt_verified': True, 'reproducible_binary_build_proven': False,
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}


