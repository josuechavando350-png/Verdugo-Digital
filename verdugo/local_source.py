"""Three reviewed, unmodified upstream modules, bundled with their licenses.

Only fixed module paths and functions are executed; no dynamically supplied code.
The SHA-256 of both source and license is checked before loading each module.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys

from .common import VerdugoError, fields, integer

SPECS = {
    'cognee': ('text.segment', 'bundled-source:cognee', '4053f6cc5536757f26a3665eed95c50088e6dc0b'),
    'autogeo': ('citations.score', 'bundled-source:autogeo', '49456df236774ea24087c44f45e9e52005b8e6a4'),
    'claude-skills-c-level': ('cashflow.scenario', 'bundled-source:claude-skills-c-level', '08cd8a9fc86cc370e2c0d448e8171fbcfdbc5a30'),
}
HASHES = {
    'cognee': ('a9aac48fa224281886c788ef2e3dd40f8d4dcdb640f9b5ce78a3a51f5f6cdfa6', 'a471e34908f50c3f120e9a56f3c30cb34e133e4ede01a9cbd5ce718fc358ecd4'),
    'autogeo': ('3c12623f138dec50c1c905c92c09aef1f3fe9b0a219a6ff6ffaa404007711b9d', '7db440f0a16ee1bb2b77726e9c693a6171667069c6ac1679efbb2c2fe41cf0b3'),
    'claude-skills-c-level': ('c1c8b1b648f53934925c1cd8583550d1ac6990f229d2d664fafd0cf1f23b5051', 'a20126646f93d32a8989c3cf4772d59194f405034f7babe7daebeac22b8ab151'),
}
EXTRA = {'autogeo': {'nltk': '3.9.2'}}
ROOT = Path(__file__).with_name('vendor')


def source_path(service):
    from .local_native import checked
    if service not in SPECS:
        raise VerdugoError('Unsupported pinned-source operation')
    folder = checked(ROOT / service, directory=True)
    for name, expected in zip(('original.py', 'LICENSE'), HASHES[service]):
        data = checked(folder / name, budget=128 * 1024).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise VerdugoError('Pinned upstream source or license changed')
    return folder / 'original.py'


def runtime_state(service):
    from . import runtime_profile
    op, distribution, expected = SPECS[service]
    present = False
    wanted = EXTRA.get(service, {})
    versions = runtime_profile.versions(service, list(wanted)) if wanted else {}
    extras = {key: {'expected': version, 'installed': versions.get(key)} for key, version in wanted.items()}
    try:
        source_path(service)
        present = all(versions.get(key) == version for key, version in wanted.items())
    except (OSError, VerdugoError):
        pass
    binding = hashlib.sha256((''.join(HASHES[service]) + runtime_profile.binding(service)).encode()).hexdigest()
    return {'distribution': distribution, 'distribution_kind': 'bundled-original-source',
            'expected': expected, 'installed': expected if present else None,
            'version_matches': present, 'extra_distributions': extras, 'operation': op,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    from .local_runtime import string, finite
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported pinned-source operation')
    required = {'cognee': ('text',), 'autogeo': ('sentences', 'source_count'),
                'claude-skills-c-level': ('currency', 'cash_minor', 'mrr_minor', 'opex_minor', 'gross_margin', 'growth_rate', 'months')}[service]
    fields(p, ('dataset', *required))
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')
    if service == 'cognee':
        string(p['text'], 12000)
    elif service == 'autogeo':
        integer(p['source_count'], 1, 20)
        rows = p['sentences']
        if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
            raise VerdugoError('Provide 1..100 tokenized sentences')
        for row in rows:
            fields(row, ('tokens', 'citations'))
            if not isinstance(row['tokens'], list) or not 1 <= len(row['tokens']) <= 100:
                raise VerdugoError('Provide 1..100 tokens per sentence')
            for token in row['tokens']:
                string(token, 100)
            citations = row['citations']
            if not isinstance(citations, list) or len(citations) > p['source_count']:
                raise VerdugoError('Bounded citation indices required')
            for index in citations:
                integer(index, 0, p['source_count'] - 1)
            if len(set(citations)) != len(citations):
                raise VerdugoError('Duplicate citation')
    else:
        if p['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('Explicit supported currency required')
        for key in ('cash_minor', 'mrr_minor', 'opex_minor'):
            integer(p[key], 0, 10**12)
        finite(p['gross_margin'], 0, 1); finite(p['growth_rate'], -0.5, 0.5)
        integer(p['months'], 1, 24)


def run(service, p):
    # The code object always comes from one fixed, hash-checked original file.
    path = source_path(service)
    name = '_verdugo_upstream_' + service.replace('-', '_')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if service == 'cognee':
        rows = list(module.chunk_by_word(p['text']))
        if ''.join(row[0] for row in rows) != p['text']:
            raise ValueError('Original chunker did not preserve input')
        if len(rows) > 2000:
            raise ValueError('Chunk output budget exceeded')
        return {'segments': [{'text': value, 'boundary': boundary} for value, boundary in rows],
                'lossless': True, 'knowledge_graph_created': False, 'llm_calls': 0}
    if service == 'autogeo':
        sentences = [[(row['tokens'], '', row['citations']) for row in p['sentences']]]
        return {'word_shares': module.impression_word_count_simple(sentences, n=p['source_count']),
                'position_word_shares': module.impression_wordpos_count_simple(sentences, n=p['source_count']),
                'citation_index_base': 0, 'scope': 'heuristic shares over supplied tokenized sentences',
                'measured_engine_visibility': False, 'causal_effect_demonstrated': False,
                'upstream_zero_evidence_policy': 'uniform_shares'}
    config = module.ModelConfig(name='operator-scenario', starting_cash=p['cash_minor'], starting_mrr=p['mrr_minor'],
        starting_headcount=0, avg_loaded_salary=0, base_non_headcount_opex=p['opex_minor'],
        gross_margin_pct=p['gross_margin'], mrr_growth_rate=p['growth_rate'], model_months=p['months'])
    rows = module.RunwayCalculator(config).run()
    return {'months': [{'month': row.month, 'mrr_minor': row.mrr, 'net_burn_minor': row.net_burn,
                         'cash_end_minor': row.cash_end} for row in rows],
            'currency': p['currency'], 'scenario_only': True, 'reconciled_cash': False,
            'scope': 'constant expense scenario; no hires, taxes, financing or validated forecast'}
