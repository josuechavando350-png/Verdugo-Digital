"""Bounded SDK interoperability and local content analysis.

SDK tools expose one fixed calculation. No models, autonomous agents, remote
tools, caller code, downloads or persistent stores are started here.
"""
import asyncio
import json

SPECS = {
    'crewai': ('campaigns.tool', 'crewai', '1.15.41'),
    'openai-agents': ('campaigns.tool', 'openai-agents', '0.24.0'),
    'google-adk': ('campaigns.tool', 'google-adk', '2.14.1'),
    'agent-framework': ('campaigns.tool', 'agent-framework-core', '1.26.0'),
    'smolagents': ('campaigns.tool', 'smolagents', '1.26.0'),
    'camel': ('campaigns.tool', 'camel-ai', '0.2.90'),
    'any-agent': ('campaigns.tool', 'any-agent', '1.18.0'),
    'fastmcp': ('campaigns.tool', 'fastmcp', '4.2.0'),
    'guardrails': ('campaign.validate', 'guardrails-ai', '0.11.0'),
    'instructor': ('campaign.validate', 'instructor', '1.17.0'),
    'outlines': ('campaign.validate', 'outlines', '1.3.3'),
    'llm-guard': ('text.filter', 'llm-guard', '0.3.16'),
    'sentence-transformers': ('vectors.compare', 'sentence-transformers', '6.3.0'),
    'transformers': ('text.encode', 'transformers', '5.23.0'),
    'bertopic': ('classes.weight', 'bertopic', '0.17.4'),
    'ax': ('threshold.select', 'ax-platform', '1.3.1'),
    'geo-optimizer': ('html.meta', 'geo-optimizer-skill', '4.23.0'),
    'parsedmarc': ('report.summarize', 'parsedmarc', '11.3.0'),
    'cdx-toolkit': ('captures.summarize', 'cdx-toolkit', '0.9.39'),
    'news-please': ('html.article', 'news-please', '1.6.16'),
}
TOOLS = {sid for sid, spec in SPECS.items() if spec[0] == 'campaigns.tool'}
PROFILES = {
    **{sid: 'AGENTS' for sid in ('openai-agents', 'google-adk', 'agent-framework', 'smolagents', 'fastmcp', 'instructor', 'outlines')},
    'crewai': 'LEGACY_AGENTS', 'guardrails': 'LEGACY_AGENTS',
    'camel': 'CAMEL', 'any-agent': 'ANYAGENT', 'llm-guard': 'GUARD',
    **{sid: 'SEMANTICS' for sid in ('sentence-transformers', 'transformers', 'bertopic', 'ax')},
    **{sid: 'DISCOVERY' for sid in ('geo-optimizer', 'parsedmarc', 'cdx-toolkit', 'news-please')},
}
EXTRA = {'any-agent': {'openai-agents': '0.24.0', 'mcp': '1.30.0'},
         'camel': {'mcp': '1.30.0'},
         'crewai': {'crewai-core': '1.15.41'}, 'fastmcp': {'fastmcp-slim': '4.2.0'}}


def validate(service, operation, p):
    from .common import VerdugoError, fields, integer
    from .local_runtime import string, matrix, validate as base
    if service not in SPECS or SPECS[service][0] != operation:
        raise VerdugoError('Unsupported interoperability operation')
    required = {
        **{sid: ('currency', 'rows') for sid in TOOLS},
        **{sid: ('candidate',) for sid in ('guardrails', 'instructor', 'outlines')},
        'llm-guard': ('text',), 'sentence-transformers': ('left', 'right'),
        'transformers': ('text', 'vocabulary'), 'bertopic': ('counts',),
        'ax': ('scores', 'labels'), 'geo-optimizer': ('html',),
        'parsedmarc': ('xml',), 'cdx-toolkit': ('captures',), 'news-please': ('html',),
    }
    try:
        fields(p, ('dataset', *required[service]))
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerdugoError('Input must be bounded finite JSON') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('Explicit dataset required')
    if service in TOOLS:
        base('duckdb', 'campaigns.aggregate', p)
    elif service in ('guardrails', 'instructor', 'outlines'):
        string(p['candidate'], 4000)
    elif service == 'llm-guard':
        string(p['text'], 16000)
    elif service == 'sentence-transformers':
        if matrix(p['left']) != matrix(p['right']): raise VerdugoError('Vector widths differ')
        for key in ('left', 'right'):
            if len(p[key]) > 50 or any(not any(v for v in row) for row in p[key]):
                raise VerdugoError('At most fifty nonzero vectors are supported')
    elif service == 'transformers':
        string(p['text'], 4000)
        vocab = p['vocabulary']
        if not isinstance(vocab, list) or not 5 <= len(vocab) <= 200:
            raise VerdugoError('Provide 5..200 vocabulary entries')
        for value in vocab: string(value, 50)
        if len(set(vocab)) != len(vocab) or not {'[PAD]', '[UNK]', '[CLS]', '[SEP]', '[MASK]'} <= set(vocab):
            raise VerdugoError('Unique vocabulary with BERT special entries required')
    elif service == 'bertopic':
        width = matrix(p['counts'], minimum=2)
        if len(p['counts']) > 50 or width < 2: raise VerdugoError('Bounded class matrix required')
        for row in p['counts']:
            for value in row: integer(value, 0, 100000)
            if sum(row) == 0: raise VerdugoError('Empty class is unsupported')
        if any(sum(row[i] for row in p['counts']) == 0 for i in range(width)):
            raise VerdugoError('Empty term is unsupported')
    elif service == 'ax':
        base('optuna', 'threshold.optimize', p)
    elif service in ('geo-optimizer', 'news-please'):
        base('trafilatura', 'html.extract', p)
    elif service == 'parsedmarc':
        string(p['xml'], 40000)
        if '<!DOCTYPE' in p['xml'].upper() or '<!ENTITY' in p['xml'].upper():
            raise VerdugoError('XML declarations and external entities are forbidden')
        # Reject excessive nested/record structure before the upstream parser.
        import xml.etree.ElementTree as ET
        try: root = ET.fromstring(p['xml'])
        except ET.ParseError as exc: raise VerdugoError('Invalid aggregate XML') from exc
        if root.tag != 'feedback' or len(list(root.iter())) > 1000 or len(root.findall('record')) > 100:
            raise VerdugoError('Bounded DMARC aggregate feedback required')
    elif service == 'cdx-toolkit':
        import datetime
        if not isinstance(p['captures'], list) or not 1 <= len(p['captures']) <= 100:
            raise VerdugoError('Provide 1..100 capture descriptors')
        for row in p['captures']:
            fields(row, ('timestamp', 'status', 'mime'))
            string(row['timestamp'], 14); string(row['mime'], 80)
            if len(row['timestamp']) != 14 or not row['timestamp'].isascii() or not row['timestamp'].isdigit():
                raise VerdugoError('Fourteen-digit capture timestamp required')
            try: datetime.datetime.strptime(row['timestamp'], '%Y%m%d%H%M%S')
            except ValueError as exc: raise VerdugoError('Invalid capture timestamp') from exc
            integer(row['status'], 100, 599)


def campaign_totals(spend_minor: list[int], revenue_minor: list[int]) -> dict:
    """Sum supplied campaign amounts; these are not reconciled bank revenues.

    Args:
        spend_minor: Nonnegative campaign costs in one declared currency.
        revenue_minor: Nonnegative attributed revenues in the same currency.
    """
    return {'spend_minor': sum(spend_minor), 'revenue_minor': sum(revenue_minor),
            'rows': len(spend_minor)}


def sdk_tool(service, p):
    args = {key: [row[key] for row in p['rows']] for key in ('spend_minor', 'revenue_minor')}
    if service == 'crewai':
        from crewai.tools import tool
        result = tool(campaign_totals).run(**args)
    elif service in ('openai-agents', 'any-agent'):
        from agents import function_tool, set_tracing_disabled
        from agents.tool_context import ToolContext
        set_tracing_disabled(True)
        if service == 'any-agent':
            from any_agent.config import AgentFramework
            from any_agent.tools.wrappers import _wrap_tools
            wrapped, clients = asyncio.run(_wrap_tools([campaign_totals], AgentFramework.OPENAI))
            if clients: raise ValueError('Remote clients are not allowed')
            native = wrapped[0]
        else:
            native = function_tool(campaign_totals, failure_error_function=None)
        encoded = json.dumps(args)
        context = ToolContext(context=None, tool_name='campaign_totals', tool_call_id='local', tool_arguments=encoded)
        result = asyncio.run(native.on_invoke_tool(context, encoded))
    elif service == 'google-adk':
        from google.adk.tools import FunctionTool
        result = asyncio.run(FunctionTool(campaign_totals).run_async(args=args, tool_context=None))
    elif service == 'agent-framework':
        from agent_framework import tool
        result = asyncio.run(tool(campaign_totals).invoke(arguments=args, skip_parsing=True))
    elif service == 'smolagents':
        from smolagents import tool
        result = tool(campaign_totals)(**args)
    elif service == 'camel':
        from camel.toolkits import FunctionTool
        result = FunctionTool(campaign_totals)(**args)
    elif service == 'fastmcp':
        from fastmcp.tools.function_tool import FunctionTool
        result = asyncio.run(FunctionTool.from_function(campaign_totals, run_in_thread=False).run(args)).structured_content
    if isinstance(result, str): result = json.loads(result)
    if result != campaign_totals(**args): raise ValueError('SDK tool result mismatch')
    return {**result, 'currency': p['currency'], 'sdk': service,
            'execution': 'fixed-native-sdk-tool', 'model_calls': 0,
            'agent_reasoning_tested': False, 'bank_reconciled': False}


def campaign_schema():
    from pydantic import BaseModel, ConfigDict, Field
    class Campaign(BaseModel):
        model_config = ConfigDict(extra='forbid', strict=True)
        campaign: str = Field(min_length=1, max_length=64)
        spend_minor: int = Field(ge=0, le=10**9)
    return Campaign


def structure(service, p):
    from pydantic import ValidationError
    model = campaign_schema()
    if service == 'guardrails':
        from guardrails import Guard
        guard = Guard.for_pydantic(model)
        guard.configure(allow_metrics_collection=False)
        outcome = guard.parse(p['candidate'], num_reasks=0)
        valid = bool(outcome.validation_passed)
    elif service == 'instructor':
        from instructor import openai_schema, Mode
        from openai.types.chat import ChatCompletion
        response = ChatCompletion(id='local-supplied-content', created=0, model='none', object='chat.completion',
            choices=[{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': p['candidate']}}])
        try:
            openai_schema(model).from_response(response, mode=Mode.JSON, strict=True)
            valid = True
        except (ValidationError, json.JSONDecodeError): valid = False
    else:
        from outlines.types import JsonSchema
        valid = bool(JsonSchema(model.model_json_schema()).matches(p['candidate']))
    return {'valid': valid, 'schema': 'campaign-v1', 'candidate_returned': False,
            'model_calls': 0, 'content_truth_verified': False}


def filter_text(p):
    from llm_guard.input_scanners import Regex
    scanner = Regex([r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'], match_type='all', redact=True)
    text, valid, risk = scanner.scan(p['text'])
    return {'text': text, 'passed': bool(valid), 'risk_score': float(risk),
            'scope': 'email-pattern-only', 'all_sensitive_data_removed': False}


def similarity(p):
    from sentence_transformers.util import cos_sim
    scores = cos_sim(p['left'], p['right']).tolist()
    return {'similarities': scores, 'embeddings_generated': False, 'models_downloaded': 0}


def encode_text(p):
    from transformers import BertTokenizer
    tokenizer = BertTokenizer(vocab={v: i for i, v in enumerate(p['vocabulary'])}, do_lower_case=True)
    encoded = tokenizer(p['text'], add_special_tokens=True)
    return {'unit_ids': encoded['input_ids'], 'lexical_units': tokenizer.tokenize(p['text']),
            'vocabulary_size': len(p['vocabulary']), 'pretrained_model_used': False}


def weight_classes(p):
    import numpy as np
    from scipy.sparse import csr_matrix
    from bertopic.vectorizers import ClassTfidfTransformer
    matrix = csr_matrix(np.asarray(p['counts'], dtype=float))
    model = ClassTfidfTransformer()
    weights = model.fit(matrix).transform(matrix).toarray().tolist()
    return {'weights': weights, 'classes': len(weights), 'terms': len(weights[0]),
            'class_labels_supplied': True, 'topics_discovered': False}


def select_threshold(p):
    from ax.api.client import Client
    from ax.api.configs import ChoiceParameterConfig
    choices = [0.0, 0.25, 0.5, 0.75, 1.0]
    client = Client(random_seed=7)
    client.configure_experiment(parameters=[ChoiceParameterConfig(name='threshold', values=choices, parameter_type='float', is_ordered=True)])
    client.configure_optimization(objective='f1')
    for value in choices:
        prediction = [int(s >= value) for s in p['scores']]
        tp = sum(a == b == 1 for a, b in zip(prediction, p['labels']))
        denominator = sum(prediction)+sum(p['labels'])
        score = 2*tp/denominator if denominator else 0.0
        trial = client.attach_trial(parameters={'threshold': value})
        client.complete_trial(trial_index=trial, raw_data={'f1': (score, 0.0)})
    params, outcomes, _, _ = client.get_best_parameterization(use_model_predictions=False)
    score = outcomes['f1']
    return {'threshold': params['threshold'], 'f1': float(score[0] if isinstance(score, tuple) else score),
            'evaluated_candidates': len(choices), 'evaluation_scope': 'supplied-sample', 'out_of_sample_verified': False}


def meta(p):
    from bs4 import BeautifulSoup
    from geo_optimizer.core.audit_meta import audit_meta_tags
    r = audit_meta_tags(BeautifulSoup(p['html'], 'html.parser'), 'https://example.invalid/')
    return {**{key: getattr(r, key) for key in ('has_title', 'title_length', 'has_description', 'description_length', 'has_canonical', 'has_noai', 'has_og_title', 'has_og_description', 'has_og_image')},
            'page_fetched': False, 'rank_or_ai_visibility_measured': False}


def dmarc(p):
    import parsedmarc
    report = parsedmarc.parse_aggregate_report_xml(p['xml'], offline=True, always_use_local_files=True)
    rows = report['records']
    dispositions = {}
    for row in rows:
        disposition = row['policy_evaluated']['disposition']
        dispositions[disposition] = dispositions.get(disposition, 0)+row['count']
    return {'records': len(rows), 'message_count': sum(row['count'] for row in rows),
            'dispositions': dispositions, 'dns_lookups': 0, 'raw_report_returned': False,
            'report_authenticity_verified': False}


def captures(p):
    from types import SimpleNamespace
    from cdx_toolkit import cdx_to_captures
    # The real upstream CDX JSON parser handles supplied capture descriptors.
    response = SimpleNamespace(status_code=200, text=json.dumps(
        [['timestamp', 'status', 'mime']]+[[r['timestamp'], str(r['status']), r['mime']] for r in p['captures']]))
    rows = cdx_to_captures(response)
    times = sorted(row['timestamp'] for row in rows)
    return {'captures': len(rows), 'successful': sum(int(row['status']) == 200 for row in rows),
            'first_capture': times[0], 'last_capture': times[-1], 'captures_fetched': 0}


def article(p):
    from newsplease import NewsPlease
    document = NewsPlease.from_html(p['html'], fetch_images=False)
    return {'title': document.title, 'text': document.maintext or '',
            'page_fetched': False, 'images_fetched': False, 'content_is_untrusted_data': True}


HANDLERS = {'llm-guard': filter_text, 'sentence-transformers': similarity, 'transformers': encode_text,
            'bertopic': weight_classes, 'ax': select_threshold, 'geo-optimizer': meta,
            'parsedmarc': dmarc, 'cdx-toolkit': captures, 'news-please': article}


def run(service, params):
    if service in TOOLS: return sdk_tool(service, params)
    if service in ('guardrails', 'instructor', 'outlines'): return structure(service, params)
    return HANDLERS[service](params)
