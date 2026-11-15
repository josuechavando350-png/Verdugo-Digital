"""Langroid dispatches one fixed arithmetic checker, with llm/vecdb/parser disabled.

MetaGPT is intentionally absent from SPECS: its pinned dependencies did not
resolve. Source review alone never creates an operational adapter.
"""
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, encode, fields, integer

SPECS = {'langroid': ('claims.check', 'langroid', '0.69.23')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-reasoning666.json'
CLAIMS = {'conversion_rate_increased', 'cost_per_client_decreased', 'revenue_above_ad_spend'}
TOKENIZER_URL = 'https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken'
TOKENIZER_SHA256 = '223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7'


def tokenizer_directory():
    from .runtime_profile import interpreter
    return Path(interpreter('langroid')).parent.parent / 'share/verdugo-tokenizers'


def verify_tokenizer():
    path = tokenizer_directory() / hashlib.sha1(TOKENIZER_URL.encode()).hexdigest()
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != TOKENIZER_SHA256:
        raise VerdugoError('Prepare the pinned offline tokenizer before using Langroid')


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed claim-checking operation')
    fields(p, ('dataset', 'currency', 'before', 'after', 'claims'))
    if p['dataset'] != 'demo' or p['currency'] not in ('MXN', 'USD', 'EUR'):
        raise VerdugoError('Synthetic demo and explicit currency are required')
    for key in ('before', 'after'):
        r = p[key]
        fields(r, ('contacts', 'clients', 'spend_minor', 'revenue_minor'))
        integer(r['contacts'], 0, 10**9)
        integer(r['clients'], 0, r['contacts'])
        integer(r['spend_minor'], 0, 10**12)
        integer(r['revenue_minor'], 0, 10**12)
    claims = p['claims']
    if not isinstance(claims, list) or not 1 <= len(claims) <= 3 or any(
            not isinstance(c, str) or c not in CLAIMS for c in claims) or len(set(claims)) != len(claims):
        raise VerdugoError('Select one to three distinct fixed arithmetic claims')


def check_claims(p):
    before, after = p['before'], p['after']
    results = []
    for claim in p['claims']:
        if claim == 'conversion_rate_increased':
            supported = (after['clients']*before['contacts'] > before['clients']*after['contacts']) \
                if before['contacts'] and after['contacts'] else None
        elif claim == 'cost_per_client_decreased':
            supported = (after['spend_minor']*before['clients'] < before['spend_minor']*after['clients']) \
                if before['clients'] and after['clients'] else None
        else:
            supported = after['revenue_minor'] > after['spend_minor']
        results.append({'claim': claim, 'verdict': 'insufficient_data' if supported is None else
                        'supported' if supported else 'contradicted'})
    return {'claims': results, 'currency': p['currency'], 'basis': 'Supplied synthetic aggregate counts only',
            'causality_established': False, 'real_clients_verified': 0, 'net_profit_verified': False,
            'semantic_truth_verified': False, 'external_execution_authorized': False}


def verify_source():
    record = next(r for r in json.loads(CONTRACT.read_text())['records'] if r['id'] == 'langroid')
    distribution = metadata.distribution('langroid')
    checked = 0
    for f in record['files']:
        if f['installed_path']:
            if hashlib.sha256(distribution.locate_file(f['installed_path']).read_bytes()).hexdigest() != f['sha256']:
                raise VerdugoError('Installed Langroid differs from reviewed source')
            checked += 1
    if checked != 3:
        raise VerdugoError('Incomplete Langroid original source evidence')
    return record['commit']


def run(service, p):
    validate(service, SPECS[service][0], p)
    commit = verify_source()
    verify_tokenizer()
    from langroid.agent.base import Agent, AgentConfig
    from langroid.agent.chat_document import ChatDocument
    from langroid.agent.tool_message import ToolMessage
    from pydantic import ConfigDict

    class ClaimsTool(ToolMessage):
        request: str = 'check_synthetic_claims'
        purpose: str = 'Check three fixed arithmetic predicates on synthetic counts'
        payload_json: str
        model_config = ConfigDict(extra='forbid')

        def handle(self):
            return encode(check_claims(json.loads(self.payload_json)))

    agent = Agent(AgentConfig(name='verdugo', llm=None, vecdb=None, parsing=None, prompts=None,
                             show_stats=False, add_to_registry=False, allow_multiple_tools=False))
    agent.enable_message_handling(ClaimsTool)
    result = agent.handle_tool_message(ClaimsTool(payload_json=encode(p)))
    if agent.llm is not None or agent.vecdb is not None or agent.parser is not None or not isinstance(result, ChatDocument):
        raise ValueError('Unexpected fixed Langroid dispatch')
    return json.loads(result.content) | {'original_sdk': 'langroid', 'sdk_version': SPECS[service][2],
        'source_commit': commit, 'reviewed_modules_verified': 3, 'fixed_tool_dispatches': 1,
        'dataset': 'demo', 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'dry_run': True}
