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
