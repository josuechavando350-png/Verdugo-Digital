"""Bounded, useful calls to real optional libraries. Imports are lazy.

Input validation is performed by local_runtime before this fixed worker runs.
There is no provider/network client, arbitrary callback, SQL, file path or model
loader in these recipes. Outputs are observations of the supplied dataset only.
"""
import json
import math


def run(service, operation, p):
    from local_extended import SPECS as EXTENDED, run as run_extended
    if service in EXTENDED:
        return run_extended(service, p)
    handlers = {
        'trafilatura': extract_html, 'scrapy': inspect_html,
        'duckdb': aggregate_campaigns, 'or-tools': select_items,
        'optuna': optimize_threshold, 'scikit-learn': score_logistic,
        'catboost': score_catboost, 'haystack': search_documents,
        'great-expectations': validate_data, 'evidently': report_drift,
        'presidio': redact_text, 'playwright': audit_html,
    }
    return handlers[service](p)


def extract_html(p):
    from trafilatura import extract
    content = extract(p['html'], output_format='txt', include_comments=False,
                      include_images=False, include_links=False,
                      include_tables=True, no_fallback=True)
    if not content:
        raise ValueError('No article text was extracted')
    return {'text': content[:20000], 'characters_before_limit': len(content),
            'truncated': len(content) > 20000, 'fetched_remote_content': False,
            'content_is_untrusted_data': True}


def inspect_html(p):
    from scrapy import Selector
    selector = Selector(text=p['html'], type='html')
    return {'title': (selector.css('title::text').get() or '')[:300],
            'h1': [v[:300] for v in selector.css('h1::text').getall()[:30]],
            'h2': [v[:300] for v in selector.css('h2::text').getall()[:30]],
            'links': [v[:500] for v in selector.css('a::attr(href)').getall()[:50]],
            'links_followed': 0, 'content_is_untrusted_data': True}


def aggregate_campaigns(p):
    import duckdb
    con = duckdb.connect(':memory:', config={
        'enable_external_access': False, 'autoinstall_known_extensions': False,
        'autoload_known_extensions': False, 'threads': 1})
    try:
        con.execute('CREATE TABLE campaigns(channel VARCHAR, spend BIGINT, revenue BIGINT, leads BIGINT, conversions BIGINT)')
        con.executemany('INSERT INTO campaigns VALUES (?,?,?,?,?)', [
            (r['channel'], r['spend_minor'], r['revenue_minor'], r['leads'], r['conversions'])
            for r in p['rows']])
        rows = con.execute('SELECT channel, SUM(spend), SUM(revenue), SUM(leads), SUM(conversions) '
                           'FROM campaigns GROUP BY channel ORDER BY channel').fetchall()
    finally:
        con.close()
    channels = []
    for channel, spend, revenue, leads, conversions in rows:
        spend, revenue, leads, conversions = map(int, (spend, revenue, leads, conversions))
        channels.append({'channel': channel, 'spend_minor': spend, 'revenue_minor': revenue,
            'leads': leads, 'conversions': conversions,
            'reported_revenue_minus_ad_spend_minor': revenue - spend,
            'reported_roas': revenue / spend if spend else None,
            'reported_conversion_rate': conversions / leads if leads else None})
    return {'currency': p['currency'], 'channels': channels, 'input_rows': len(p['rows']),
            'bank_reconciled': False, 'causal_lift_estimated': False,
            'basis': 'Supplied rows only; revenue minus ad spend is not net profit.'}


def select_items(p):
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    items = p['items']
    variables = [model.new_bool_var('item_' + str(i)) for i in range(len(items))]
    model.add(sum(x * item['cost_minor'] for x, item in zip(variables, items)) <= p['budget_minor'])
    model.add(sum(variables) <= p.get('max_items', len(items)))
    model.maximize(sum(x * item['value'] for x, item in zip(variables, items)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 17
    status = solver.solve(model)
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        raise ValueError('Solver did not find a feasible solution within the budget')
    chosen = [item for variable, item in zip(variables, items) if solver.value(variable)]
    return {'selected_ids': [item['id'] for item in chosen],
            'total_cost_minor': sum(item['cost_minor'] for item in chosen),
            'budget_minor': p['budget_minor'], 'currency': p['currency'],
            'objective_value': sum(item['value'] for item in chosen),
            'objective_bound': float(solver.best_objective_bound),
            'optimal_for_declared_inputs': status == cp_model.OPTIMAL,
            'spend_executed': False, 'basis': 'Optimization of supplied values, not realized returns.'}


def _f1(scores, labels, threshold):
    predictions = [int(value >= threshold) for value in scores]
    tp = sum(a == 1 and b == 1 for a, b in zip(predictions, labels))
    fp = sum(a == 1 and b == 0 for a, b in zip(predictions, labels))
    fn = sum(a == 0 and b == 1 for a, b in zip(predictions, labels))
    return 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0


def optimize_threshold(p):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.ERROR)
    study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=17))
    study.enqueue_trial({'threshold': 0.5})
    def objective(trial):
        return _f1(p['scores'], p['labels'], trial.suggest_float('threshold', 0.0, 1.0))
    study.optimize(objective, n_trials=32, n_jobs=1, timeout=10, show_progress_bar=False)
    return {'threshold': study.best_params['threshold'], 'selection_f1': study.best_value,
            'baseline_f1_at_half': _f1(p['scores'], p['labels'], 0.5),
            'completed_trials': len(study.trials), 'independent_validation': False,
            'basis': 'Selected on these labels; validate on held-out/time-separated data before operational use.'}


def _score(p, model):
    import numpy as np
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    x = np.asarray(p['train_x'], dtype=float)
    y = np.asarray(p['train_y'], dtype=int)
    fit_x, test_x, fit_y, test_y = train_test_split(x, y, test_size=0.25, stratify=y, random_state=17)
    model.fit(fit_x, fit_y)
    heldout_scores = model.predict_proba(test_x)[:, 1]
    heldout_predictions = (heldout_scores >= 0.5).astype(int)
    metrics = {'holdout_rows': len(test_y), 'accuracy': float(accuracy_score(test_y, heldout_predictions)),
               'f1': float(f1_score(test_y, heldout_predictions, zero_division=0)),
               'roc_auc': float(roc_auc_score(test_y, heldout_scores))}
    model.fit(x, y)
    scores = model.predict_proba(np.asarray(p['score_x'], dtype=float))[:, 1]
    return {'model_scores': [float(s) for s in scores], 'training_rows': len(y),
            'holdout': metrics, 'calibrated_for_deployment': False,
            'basis': 'Model outputs for the supplied labels; random holdout is not a prospective commercial success estimate.'}


def score_logistic(p):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return _score(p, make_pipeline(StandardScaler(), LogisticRegression(max_iter=200, random_state=17)))


def score_catboost(p):
    from catboost import CatBoostClassifier
    return _score(p, CatBoostClassifier(iterations=50, depth=4, random_seed=17,
        thread_count=1, allow_writing_files=False, verbose=False, task_type='CPU'))


def search_documents(p):
    from haystack import Document
    from haystack.document_stores.in_memory import InMemoryDocumentStore
    from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
    store = InMemoryDocumentStore()
    store.write_documents([Document(id=d['id'], content=d['content']) for d in p['documents']])
    result = InMemoryBM25Retriever(document_store=store, top_k=p.get('top_k', 5)).run(query=p['query'])
    return {'matches': [{'id': d.id, 'score': float(d.score), 'snippet': (d.content or '')[:500]}
                        for d in result['documents']],
            'indexed_documents': len(p['documents']), 'llm_called': False,
            'retrieval_only': True, 'content_is_untrusted_data': True}


def validate_data(p):
    import pandas as pd
    import great_expectations as gx
    columns = ['feature_' + str(i) for i in range(len(p['rows'][0]))]
    frame = pd.DataFrame(p['rows'], columns=columns)
    context = gx.get_context(mode='ephemeral')
    source = context.data_sources.add_pandas(name='verdugo')
    asset = source.add_dataframe_asset(name='input')
    definition = asset.add_batch_definition_whole_dataframe('batch')
    batch = definition.get_batch(batch_parameters={'dataframe': frame})
    checks = []
    for column in columns:
        for expectation in (
            gx.expectations.ExpectColumnValuesToNotBeNull(column=column),
            gx.expectations.ExpectColumnValuesToBeBetween(column=column,
                min_value=p['minimum'], max_value=p['maximum']),
        ):
            result = batch.validate(expectation)
            checks.append({'column': column, 'expectation': type(expectation).__name__,
                           'success': bool(result.success)})
    return {'data_valid': all(c['success'] for c in checks), 'checks': checks,
            'rows': len(frame), 'checks_executed': len(checks),
            'coverage': 'Nulls and numeric bounds only; not a full business-data audit.'}


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def report_drift(p):
    import pandas as pd
    from evidently import Report
    from evidently.presets import DataDriftPreset
    columns = ['feature_' + str(i) for i in range(len(p['reference'][0]))]
    reference = pd.DataFrame(p['reference'], columns=columns)
    current = pd.DataFrame(p['current'], columns=columns)
    snapshot = Report([DataDriftPreset()]).run(current_data=current, reference_data=reference)
    data = _json_safe(json.loads(snapshot.json()))
    return {'reference_rows': len(reference), 'current_rows': len(current),
            'report': data, 'basis': 'Distribution comparison only; drift is not proof of causal change or revenue loss.'}


def redact_text(p):
    from presidio_analyzer.predefined_recognizers import EmailRecognizer, PhoneRecognizer, CreditCardRecognizer
    from presidio_anonymizer import AnonymizerEngine
    recognizers = [EmailRecognizer(), PhoneRecognizer(), CreditCardRecognizer()]
    entities = ['EMAIL_ADDRESS', 'PHONE_NUMBER', 'CREDIT_CARD']
    matches = []
    for recognizer in recognizers:
        matches.extend(recognizer.analyze(text=p['text'], entities=entities, nlp_artifacts=None))
    redacted = AnonymizerEngine().anonymize(text=p['text'], analyzer_results=matches)
    counts = {}
    for item in redacted.items:
        counts[item.entity_type] = counts.get(item.entity_type, 0) + 1
    return {'text': redacted.text, 'redactions_by_type': counts,
            'supported_entities': entities, 'exhaustive_privacy_guarantee': False,
            'basis': 'Pattern-based coverage only; names, addresses and context-dependent identifiers are not certified.'}


def audit_html(p):
    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True,
            args=['--disable-background-networking', '--disable-component-update'])
        try:
            for label, width, height in [('mobile', 390, 844), ('desktop', 1440, 900)]:
                context = browser.new_context(java_script_enabled=False,
                    viewport={'width': width, 'height': height}, service_workers='block')
                blocked = []
                def abort(route):
                    blocked.append(True)
                    route.abort()
                context.route('**/*', abort)
                page = context.new_page()
                page.set_content(p['html'], wait_until='domcontentloaded', timeout=10000)
                observed = page.evaluate('''() => ({
                    title: document.title.slice(0, 300),
                    h1_count: document.querySelectorAll('h1').length,
                    forms: document.querySelectorAll('form').length,
                    buttons: document.querySelectorAll('button,input[type="submit"]').length,
                    images_missing_alt: [...document.images].filter(i => !i.hasAttribute('alt')).length,
                    horizontal_overflow: document.documentElement.scrollWidth > innerWidth
                })''')
                results.append({'viewport': label, 'width': width, 'height': height,
                                'observations': observed, 'blocked_resource_requests': len(blocked)})
                context.close()
        finally:
            browser.close()
    return {'views': results, 'javascript_enabled': False, 'network_resources_allowed': False,
            'basis': 'Static HTML checks, not a WCAG certification or live-site conversion test.'}
