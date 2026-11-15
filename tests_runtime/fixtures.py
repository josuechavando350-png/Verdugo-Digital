"""Synthetic inputs only. No real client data, secrets, payments or campaigns."""
HTML = '''<!doctype html><html><head><title>Synthetic Nexus article</title></head>
<body><main><article><h1>Appointment automation</h1>
<p>A synthetic business wants a clearer appointment booking process. Its staff manually checks schedules,
answers repeated questions and records inquiries. This local example describes appointment automation,
follow-up scheduling and conversion measurement without collecting personal data or contacting anyone.</p>
<p>The planned workflow captures an inquiry, checks an authorized schedule and prepares a follow-up.
Observed conversions and costs must come from real business records before any commercial conclusion.
The example exists to validate text extraction, not to advertise a live product or claim revenue.</p>
<a href="https://example.invalid">Synthetic reference</a></article></main></body></html>'''
X = [[float(i) / 40, float(i % 3) / 3] for i in range(40)]
Y = [0] * 20 + [1] * 20
CASES = {
    'trafilatura': {'dataset': 'demo', 'html': HTML},
    'scrapy': {'dataset': 'demo', 'html': HTML},
    'duckdb': {'dataset': 'demo', 'currency': 'MXN', 'rows': [
        {'channel': 'organic', 'spend_minor': 100, 'revenue_minor': 500, 'leads': 4, 'conversions': 1},
        {'channel': 'organic', 'spend_minor': 200, 'revenue_minor': 700, 'leads': 6, 'conversions': 2},
        {'channel': 'referral', 'spend_minor': 0, 'revenue_minor': 300, 'leads': 1, 'conversions': 1}]},
    'or-tools': {'dataset': 'demo', 'currency': 'MXN', 'budget_minor': 10, 'items': [
        {'id': 'alpha', 'cost_minor': 4, 'value': 5},
        {'id': 'beta', 'cost_minor': 6, 'value': 8},
        {'id': 'gamma', 'cost_minor': 9, 'value': 10}]},
    'optuna': {'dataset': 'demo', 'scores': [0.05,0.1,0.15,0.2,0.25,0.65,0.7,0.8,0.9,0.95],
               'labels': [0,0,0,0,0,1,1,1,1,1]},
    'scikit-learn': {'dataset': 'demo', 'train_x': X, 'train_y': Y, 'score_x': [[0.05,0.1],[0.95,0.1]]},
    'catboost': {'dataset': 'demo', 'train_x': X, 'train_y': Y, 'score_x': [[0.05,0.1],[0.95,0.1]]},
    'haystack': {'dataset': 'demo', 'query': 'appointment booking', 'top_k': 1, 'documents': [
        {'id': 'appointments', 'content': 'Appointment booking and calendar scheduling for a dental clinic.'},
        {'id': 'garden', 'content': 'Garden furniture with tables and chairs.'}]},
    'great-expectations': {'dataset': 'demo', 'rows': [[1,2],[3,None],[5,6]], 'minimum': 0, 'maximum': 10},
    'evidently': {'dataset': 'demo', 'reference': [[i/100, i/200] for i in range(40)],
                  'current': [[100+i/100, 100+i/200] for i in range(40)]},
    'presidio': {'dataset': 'demo', 'text': 'Contact maria@example.com. Test card 4111 1111 1111 1111.'},
    'playwright': {'dataset': 'demo', 'html': '''<!doctype html><html><head><title>Synthetic layout</title>
        <style>.wide { width:1200px; }</style></head><body><div class="wide"><h1>Demo</h1>
        <button>Book</button><img src="https://example.invalid/test.png"></div>
        <script>document.body.appendChild(document.createElement('h1'))</script></body></html>'''},
}

from extended_fixtures import CASES as EXTENDED_CASES
CASES.update(EXTENDED_CASES)

from analytics_fixtures import CASES as ANALYTICS_CASES
CASES.update(ANALYTICS_CASES)

from research_fixtures import CASES as RESEARCH_CASES
from interop_fixtures import CASES as INTEROP_CASES
from knowledge_fixtures import CASES as KNOWLEDGE_CASES
CASES.update(RESEARCH_CASES)
CASES.update(INTEROP_CASES)
CASES.update(KNOWLEDGE_CASES)

from content_fixtures import CASES as CONTENT_CASES
CASES.update(CONTENT_CASES)
from native_fixtures import CASES as NATIVE_CASES
CASES.update(NATIVE_CASES)

from cli_fixtures import CASES as CLI_CASES
CASES.update(CLI_CASES)

from planning_fixtures import CASES as PLANNING_CASES
CASES.update(PLANNING_CASES)

from completion_fixtures import CASES as COMPLETION_CASES
CASES.update(COMPLETION_CASES)

from r_fixtures import CASES as R_CASES
CASES.update(R_CASES)

from database_fixtures import CASES as DATABASE_CASES
CASES.update(DATABASE_CASES)

from native_tools_fixtures import CASES as TOOLS_CASES
CASES.update(TOOLS_CASES)

from source_fixtures import CASES as SOURCE_CASES
CASES.update(SOURCE_CASES)

from media_fixtures import CASES as MEDIA_CASES
CASES.update(MEDIA_CASES)

from images_fixtures import CASES as IMAGES_CASES
CASES.update(IMAGES_CASES)

from lastnode_fixtures import CASES as LASTNODE_CASES
CASES.update(LASTNODE_CASES)

from owned_http_fixtures import CASES as OWNED_HTTP_CASES
CASES.update(OWNED_HTTP_CASES)

# Same fixed synthetic goal as the public pilot example.
CASES['semantic-kernel'] = {'dataset': 'demo', 'goal': {
    'dataset': 'demo', 'target_clients': 20, 'horizon_days': 30,
    'budget_minor': 0, 'currency': 'MXN', 'channels': [
        {'channel': 'referral', 'contacts_available': 300, 'cost_per_contact_minor': 0,
         'history_contacts': 200, 'history_clients': 20}]}}

from executive666_fixtures import CASES as EXECUTIVE666_CASES
CASES.update(EXECUTIVE666_CASES)
from reasoning666_fixtures import CASES as REASONING666_CASES
CASES.update(REASONING666_CASES)
from flow666_fixtures import CASES as FLOW666_CASES
CASES.update(FLOW666_CASES)

from planning666_fixtures import CASES as PLANNING666_CASES
CASES.update(PLANNING666_CASES)
CASES['hatchet'] = {'dataset':'demo','operation_kind':'write','previous_state':'uncertain',
                    'max_parallel':2,'requested_retries':3,'timeout_seconds':30,
                    'retention_seconds':600}

CASES['invariant'] = {'dataset': 'demo', 'events': [{'kind': 'read_private', 'previous_state': 'failed', 'hypothetical_review': True}, {'kind': 'send', 'previous_state': 'uncertain', 'hypothetical_review': False}]}

CASES['pyrit'] = {'dataset': 'demo', 'calls': [{'tool': 'draft', 'format': 'chat', 'outcome': 'invoked', 'simulated': False}, {'tool': 'send', 'format': 'responses', 'outcome': 'not_invoked', 'simulated': False}, {'tool': 'plan', 'format': 'chat', 'outcome': 'invoked', 'simulated': True}]}

CASES['llama-cpp'] = {'dataset':'demo', 'context_budget_units':200, 'response_budget_units':900, 'context_limit':512}
CASES['granite-guardian'] = {'dataset':'demo', 'context_budget_units':200, 'response_budget_units':900}

CASES['interpret'] = {'dataset': 'demo', 'training': [{'contacts': 20, 'spend_minor': 0, 'observed_clients': 2}, {'contacts': 30, 'spend_minor': 50, 'observed_clients': 3}, {'contacts': 40, 'spend_minor': 100, 'observed_clients': 4}, {'contacts': 50, 'spend_minor': 150, 'observed_clients': 5}, {'contacts': 60, 'spend_minor': 200, 'observed_clients': 6}, {'contacts': 70, 'spend_minor': 250, 'observed_clients': 7}, {'contacts': 80, 'spend_minor': 300, 'observed_clients': 8}, {'contacts': 90, 'spend_minor': 350, 'observed_clients': 9}, {'contacts': 100, 'spend_minor': 400, 'observed_clients': 10}, {'contacts': 110, 'spend_minor': 450, 'observed_clients': 11}, {'contacts': 120, 'spend_minor': 500, 'observed_clients': 12}, {'contacts': 130, 'spend_minor': 550, 'observed_clients': 13}, {'contacts': 140, 'spend_minor': 600, 'observed_clients': 14}, {'contacts': 150, 'spend_minor': 650, 'observed_clients': 15}, {'contacts': 160, 'spend_minor': 700, 'observed_clients': 16}, {'contacts': 170, 'spend_minor': 750, 'observed_clients': 17}], 'queries': [{'contacts': 35, 'spend_minor': 75}, {'contacts': 80, 'spend_minor': 300}]}

CASES['transformerlens'] = {'dataset':'demo','symbol_ids':[1,3,4,2],'intervention':'zero_residual'}



CASES['bitsandbytes'] = {'dataset':'demo','values':list(range(-32,32))}

CASES['guidance'] = {'dataset': 'demo', 'cases': [{'decision': 'review', 'approved': False, 'item_count': 2, 'variant': 'canonical'}, {'decision': 'execute', 'approved': True, 'item_count': 2, 'variant': 'canonical'}, {'decision': 'defer', 'approved': False, 'item_count': 3, 'variant': 'extra_field'}]}

CASES['lm-format-enforcer'] = {'dataset': 'demo', 'cases': [{'decision': 'review', 'mode': 'dry_run', 'cut': 'complete'}, {'decision': 'defer', 'mode': 'dry_run', 'cut': 'object_prefix'}, {'decision': 'execute', 'mode': 'send', 'cut': 'complete'}]}

CASES['usearch'] = {'dataset': 'demo', 'case': 'plane'}

CASES['rerankers'] = {'dataset': 'demo', 'mode': 'score', 'values': [2, 5, 5, None], 'limit': 3}

CASES['sympy'] = {'dataset':'demo','coefficients':[1,-2,1],'points':[0,1,3]}
CASES['rdflib'] = {'dataset':'demo','node_count':4,'edges':[[0,1],[1,2],[2,0],[0,1]],'start':0}

CASES['z3'] = {'dataset':'demo','spend_limit':8,'unit_limit':3,'minimum_yield':6}
CASES['txtai'] = {'dataset':'demo','rows':[[0,10],[1,-5],[0,20]],'remove':[0]}
CASES['bm25s'] = {'dataset':'demo','documents':[[0,0,1],[1,2],[3]],'query':[0],'k':2}
