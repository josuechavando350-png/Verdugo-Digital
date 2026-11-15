"""Pinned local model and native tokenizer on fixed synthetic budget statements.

The model's verdict is an uncalibrated observation, never authorization. No
caller-controlled prompts, model paths, templates, commands or endpoints.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {
    'llama-cpp': ('tokens.check', 'native:llama.cpp', '1.0.0-dev'),
    'granite-guardian': ('risk.assess', 'weights:granite-guardian', '3.2-3b-a800m-Q4_K_M'),
}
CLI = {'llama-cpp'}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-guardian666.json'
ASSETS = CONTRACT.parent / 'guardian666'
RECEIPT = 'share/verdugo-guardian/build.json'
MODEL = 'share/verdugo-guardian/model.gguf'
NATIVE = ('bin/llama-completion', 'bin/llama-tokenize')
CONTEXT = 512
OUTPUT_TOKENS = 12
INFERENCE_ARGS = ('--ctx-size', '512', '--n-predict', '12', '--threads', '2',
    '--threads-batch', '2', '--batch-size', '128', '--ubatch-size', '128',
    '--temp', '0', '--seed', '666', '--n-gpu-layers', '0', '--no-repack',
    '--no-warmup', '--no-conversation', '--no-display-prompt', '--simple-io',
    '--no-escape', '--offline')
_MODEL_DIGEST_CACHE = {}


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_uid, info.st_gid, info.st_mode)


def file_digest(path, budget, reuse=False):
    path = checked(path, budget=budget)
    identity = _identity(path.stat())
    key = str(path)
    # Trusted operator-owned artifacts: reuse within this Python process only
    # while inode, size, owner, mode, mtime AND ctime remain unchanged. A fresh
    # worker hashes the entire model again. This is not protection against a
    # malicious privileged administrator or a hostile filesystem.
    if reuse and _MODEL_DIGEST_CACHE.get(key, (None,))[0] == identity:
        return _MODEL_DIGEST_CACHE[key][1]
    h = hashlib.sha256()
    with path.open('rb') as stream:
        if _identity(os.fstat(stream.fileno())) != identity:
            raise VerdugoError('Artifact changed while opening for verification')
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
        if _identity(os.fstat(stream.fileno())) != identity:
            raise VerdugoError('Artifact changed while hashing')
    actual = h.hexdigest()
    if reuse:
        if len(_MODEL_DIGEST_CACHE) >= 4: _MODEL_DIGEST_CACHE.clear()
        _MODEL_DIGEST_CACHE[key] = (identity, actual)
    return actual


def home():
    return checked(Path(runtime_profile.interpreter('granite-guardian')).parent.parent,
                   directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    expected = {'schema': 'verdugo.guardian666.operator-build.v1',
        'commit': record['native']['commit'],
        'archive_sha256': record['native']['archive_sha256'],
        'cmake_version': record['native']['cmake_version'],
        'cmake_flags': record['native']['cmake_flags'],
        'model_revision': record['weights']['revision'],
        'model_sha256': record['weights']['sha256']}
    if (any(receipt.get(k) != v for k, v in expected.items()) or
            set(receipt.get('native_artifacts', {})) != set(NATIVE)):
        raise VerdugoError('Missing or inconsistent native model build receipt')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes())
    for name in NATIVE:
        actual = file_digest(root / name, 128 * 1024 * 1024)
        if actual != receipt['native_artifacts'][name] or not os.access(root / name, os.X_OK):
            raise VerdugoError('Native model executable changed after preparation')
        digest.update(bytes.fromhex(actual))
    if (root / MODEL).stat().st_size != record['weights']['bytes']:
        raise VerdugoError('Pinned model size mismatch')
    actual = file_digest(root / MODEL, record['weights']['bytes'], reuse=True)
    if actual != record['weights']['sha256']:
        raise VerdugoError('Pinned model weights changed')
    digest.update(bytes.fromhex(actual))
    for asset in record['assets']:
        actual = file_digest(ASSETS / asset['local_name'], 1024 * 1024)
        if actual != asset['sha256']:
            raise VerdugoError('Original model template or license evidence changed')
        digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        record = json.loads(CONTRACT.read_text())
        root = home()
        artifacts = verify_build(root, record)
        versions = runtime_profile.versions(service, ['Jinja2', 'MarkupSafe'])
        if versions != {'Jinja2': '3.1.6', 'MarkupSafe': '3.0.3'}:
            raise VerdugoError('Original template renderer version mismatch')
        digest = hashlib.sha256(str(root).encode() + artifacts.encode())
        digest.update(checked(root / 'bin/python', budget=64 * 1024 * 1024).read_bytes())
        digest.update(checked(root / 'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version,
        'installed': version if present else None, 'version_matches': present,
        'extra_distributions': {}, 'operation': operation,
        'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed local model operation')
    fields(p, ('dataset', 'context_budget_units', 'response_budget_units'),
           ('context_limit',) if service == 'llama-cpp' else ())
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic demo budget statements supported')
    integer(p['context_budget_units'], 0, 10**6)
    integer(p['response_budget_units'], 0, 10**6)
    if 'context_limit' in p:
        integer(p['context_limit'], 64, CONTEXT)


def render_prompt(p):
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    config = json.loads((ASSETS / 'tokenizer_config.json').read_text())
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    def reject(message):
        raise VerdugoError('Original model template rejected fixed messages')
    env.globals['raise_exception'] = reject
    prompt = env.from_string(config['chat_template']).render(
        messages=[{'role': 'context', 'content':
            f"The synthetic plan has a budget of {p['context_budget_units']} pesos."},
            {'role': 'assistant', 'content':
            f"The plan budget is {p['response_budget_units']} pesos."}],
        guardian_config={'risk_name': 'groundedness'}, add_generation_prompt=True)
    if not isinstance(prompt, str) or not 1 <= len(prompt.encode()) <= 8192:
        raise VerdugoError('Unexpected original model prompt size')
    return prompt


def invoke_native(binary, args, prompt=None):
    # No shell or environment inheritance, no user-selected command arguments.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        result = subprocess.run([str(home() / binary), *args],
            input=prompt.encode() if prompt is not None else None,
            stdout=out, stderr=err, timeout=40, check=False,
            env={'PATH': os.defpath, 'HOME': os.getcwd(), 'TMPDIR': os.getcwd(),
                 'LANG': 'C.UTF-8', 'HF_HUB_OFFLINE': '1'})
        out.seek(0); raw = out.read(65537)
    if result.returncode or len(raw) > 65536:
        raise VerdugoError('Original native model process failed or exceeded output budget')
    return raw.decode('utf-8')


def tokenize(prompt):
    ids = json.loads(invoke_native('bin/llama-tokenize',
        ['--model', str(home() / MODEL), '--stdin', '--ids', '--no-escape', '--offline'], prompt))
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 4096 or
            any(type(value) is not int or not 0 <= value <= 1000000 for value in ids)):
        raise VerdugoError('Unexpected original tokenizer output')
    return len(ids)


def parse_verdict(text):
    # Upstream reads the first Yes/No word. This wrapper additionally rejects
    # truncated/unknown output instead of inferring approval from it.
    match = re.fullmatch(r'\s*(Yes|No)\s*(?:<confidence>\s*(?:High|Medium|Low)\s*</confidence>)?'
                         r'\s*(?:\[end of text\])?\s*', text)
    if not match:
        raise VerdugoError('Unrecognized or incomplete original model verdict')
    return match.group(1) == 'Yes'


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed local model runtime unavailable')
    record = json.loads(CONTRACT.read_text())
    prompt = render_prompt(p)
    count = tokenize(prompt)
    limit = p.get('context_limit', CONTEXT)
    result = {'unit': 'tokens', 'input_units': count, 'output_unit_limit': OUTPUT_TOKENS,
        'context_limit': limit, 'fits_context': count + OUTPUT_TOKENS <= limit,
        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': record['native' if service == 'llama-cpp' else 'guardian']['commit'],
        'native_source_commit': record['native']['commit'],
        'model_revision': record['weights']['revision'],
        'model_sha256': record['weights']['sha256'],
        'model_weights_loaded_for_inference': False,
        'original_template_verified': True, 'native_artifact_receipt_verified': True,
        'reproducible_binary_build_proven': False, 'quality_calibrated': False,
        'probability_estimated': False, 'dataset': 'demo', 'dry_run': True,
        'llm_calls': 0, 'autonomous_agent': False, 'external_calls_made': False,
        'external_execution_authorized': False, 'approvals_granted': 0,
        'operator_approval_required': True, 'business_outcome_proven': False}
    if service == 'granite-guardian':
        if not result['fits_context']:
            raise VerdugoError('Synthetic prompt exceeds fixed model context budget')
        # Completion reads the same template bytes from an ephemeral fixed file.
        # No arbitrary free-form conversation or prompt file is accepted.
        with tempfile.TemporaryDirectory(prefix='guardian-prompt-') as temp:
            path = Path(temp) / 'prompt.txt'; path.write_text(prompt)
            text = invoke_native('bin/llama-completion',
                ['--model', str(home() / MODEL), '--file', str(path), *INFERENCE_ARGS])
        says_risk = parse_verdict(text)
        reference_risk = p['context_budget_units'] != p['response_budget_units']
        result.update(model_says_unsupported=says_risk,
            synthetic_reference_unsupported=reference_risk,
            agrees_with_synthetic_reference=says_risk == reference_risk,
            model_weights_loaded_for_inference=True, llm_calls=1,
            verbal_confidence_is_not_probability=True)
    return result
