"""Reviewed, unmodified upstream modules, bundled with their licenses.

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
    'newsjack': ('rewrite.compare', 'bundled-source:newsjack', 'c2df3a0168083d620b9b36518aeca16a4eb72296'),
    'kingfisher-collect': ('releases.inspect', 'bundled-source:kingfisher-collect', '865bbb20ff4e6495bd2aba08bef5f2a0a1a648f6'),
}
HASHES = {
    'cognee': ('a9aac48fa224281886c788ef2e3dd40f8d4dcdb640f9b5ce78a3a51f5f6cdfa6', 'a471e34908f50c3f120e9a56f3c30cb34e133e4ede01a9cbd5ce718fc358ecd4'),
    'autogeo': ('3c12623f138dec50c1c905c92c09aef1f3fe9b0a219a6ff6ffaa404007711b9d', '7db440f0a16ee1bb2b77726e9c693a6171667069c6ac1679efbb2c2fe41cf0b3'),
    'claude-skills-c-level': ('c1c8b1b648f53934925c1cd8583550d1ac6990f229d2d664fafd0cf1f23b5051', 'a20126646f93d32a8989c3cf4772d59194f405034f7babe7daebeac22b8ab151'),
    'newsjack': ('134284b1c0d938d8a2c5b4fcab529303efa7f2fda0cdcd0bbc735556e07fd65b', 'a973d457a5ad23a36205ef48f88c5860680fed6a3d8fdc64df6f43cd0b3e413e'),
    'kingfisher-collect': ('e9ab6e15301976a1db03490219c5e0a4bb4e1f8a36dcddf7e5aaa9ea71b3cbf1', 'c5837dd2d0338223cecd3e7f2e53d1d02e71496343b934cd8cdaeefba52a48d3'),
}
EXTRA = {'autogeo': {'nltk': '3.9.2'}, 'kingfisher-collect': {
    'scrapy': '2.18.0', 'ijson': '3.5.0', 'jsonpointer': '3.1.1', 'jsonref': '1.1.0',
    'orjson': '3.11.9', 'flattentool': '0.28.0', 'pydantic': '2.13.4', 'rarfile': '4.2', 'requests': '2.34.2',
}}
SOURCE_FILES = {'kingfisher-collect': {
    'kingfisher_scrapy/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'kingfisher_scrapy/items.py': 'b57df9b4cfcaef8498ab6add3d385148303ee73b13615b7287f5baf94e351142',
    'kingfisher_scrapy/util.py': '707f16521a0eed153cd68b76c62315d8a57a68c43794ebb19e3cb5815a410048',
}}
ROOT = Path(__file__).with_name('vendor')


def source_path(service):
    from .local_native import checked
    if service not in SPECS:
        raise VerdugoError('Unsupported pinned-source operation')
    folder = checked(ROOT / service, directory=True)
    files = dict(zip(('original.py', 'LICENSE'), HASHES[service])) | SOURCE_FILES.get(service, {})
    for name, expected in files.items():
        if '/' in name:
            checked((folder / name).parent, directory=True)
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
    binding = hashlib.sha256((''.join(HASHES[service]) + ''.join(SOURCE_FILES.get(service, {}).values())
                              + runtime_profile.binding(service)).encode()).hexdigest()
    return {'distribution': distribution, 'distribution_kind': 'bundled-original-source',
            'expected': expected, 'installed': expected if present else None,
            'version_matches': present, 'extra_distributions': extras, 'operation': op,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    from .local_runtime import string, finite
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported pinned-source operation')
    required = {'cognee': ('text',), 'autogeo': ('sentences', 'source_count'),
                'claude-skills-c-level': ('currency', 'cash_minor', 'mrr_minor', 'opex_minor', 'gross_margin', 'growth_rate', 'months'),
                'newsjack': ('original', 'rewrite'), 'kingfisher-collect': ('records',)}[service]
    fields(p, ('dataset', *required))
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')
    if service == 'newsjack':
        string(p['original'], 8000); string(p['rewrite'], 8000)
    elif service == 'kingfisher-collect':
        from .common import identifier
        if not isinstance(p['records'], list) or not 1 <= len(p['records']) <= 100:
            raise VerdugoError('Provide 1..100 supplied file items')
        for row in p['records']:
            fields(row, ('file_id', 'number', 'tender_status'))
            identifier(row['file_id']); integer(row['number'], 1, 10000)
            if row['tender_status'] not in ('planning', 'planned', 'active', 'cancelled', 'unsuccessful', 'complete', 'withdrawn'):
                raise VerdugoError('A supplied OCDS tender status is required')
    elif service == 'cognee':
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
    if service == 'kingfisher-collect':
        # The package initializer, models and utilities are original files too.
        sys.path.insert(0, str(path.parent))
    name = '_verdugo_upstream_' + service.replace('-', '_')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if service == 'newsjack':
        value = module.compare_fact_ledgers(p['original'], p['rewrite'])
        categories = ('numbers', 'dates', 'quotes', 'urls', 'entities')
        return {'hard_categories_unchanged': value['pass'],
                'added_counts': {key: len(value['added'][key]) for key in categories},
                'missing_counts': {key: len(value['missing'][key]) for key in categories},
                'method': 'original regex ledger; English lexical patterns',
                'scope': 'compares tokens in supplied texts; entities do not affect hard-token flag',
                'facts_verified': False, 'semantic_equivalence_verified': False, 'llm_calls': 0}
    if service == 'kingfisher-collect':
        from kingfisher_scrapy.items import FileItem
        from scrapy import Spider
        from scrapy.crawler import Crawler
        from scrapy.exceptions import DropItem
        crawler = Crawler(Spider)
        crawler.spider = Spider(name='supplied-items')
        crawler.spider.pluck = True
        crawler.spider.pluck_package_pointer = None
        crawler.spider.pluck_release_pointer = '/tender/status'
        crawler.spider.pluck_truncate = None
        validator, plucker = module.Validate(), module.Pluck(crawler)
        statuses, duplicates = {}, 0
        for row in p['records']:
            item = FileItem(file_name=row['file_id']+'.json', number=row['number'],
                url='https://example.invalid/supplied', data_type='release_package',
                data={'releases': [{'tender': {'status': row['tender_status']}}]})
            try:
                validator.process_item(item)
            except DropItem:
                duplicates += 1
                continue
            status = plucker.process_item(item).value
            if status != row['tender_status']:
                raise ValueError('Original pipeline returned an unexpected tender status')
            statuses[status] = statuses.get(status, 0) + 1
        return {'input_file_items': len(p['records']), 'unique_file_items': len(p['records'])-duplicates,
                'duplicate_file_items': duplicates, 'tender_status_counts': statuses,
                'deduplication_key': 'supplied file_id and item number; first item retained',
                'scope': 'provided file metadata; not unique procurement contracts',
                'records_fetched': False, 'full_ocds_schema_validated': False}
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
