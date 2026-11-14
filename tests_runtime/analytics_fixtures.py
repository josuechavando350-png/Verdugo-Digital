"""Fixed synthetic cases for the v0.17 analytics recipes. No real client data."""
import random

_rng = random.Random(23)
_SHAP_X = [[_rng.uniform(-1, 1), _rng.uniform(-1, 1)] for _ in range(60)]
_SHAP_Y = [1 if row[0] > 0 else 0 for row in _SHAP_X]
_CLUSTER = [[round(1 + 0.01 * (i % 5), 4), round(2 + 0.01 * (i % 7), 4)] for i in range(30)]
CAMPAIGNS = [
    {'channel': 'organic', 'spend_minor': 100, 'revenue_minor': 500, 'leads': 4, 'conversions': 1},
    {'channel': 'organic', 'spend_minor': 200, 'revenue_minor': 700, 'leads': 6, 'conversions': 2},
    {'channel': 'referral', 'spend_minor': 0, 'revenue_minor': 300, 'leads': 1, 'conversions': 1}]
DMARC = '''<?xml version="1.0" encoding="UTF-8"?>
<feedback>
<report_metadata><org_name>example-reporter</org_name><email>noreply@example.net</email>
<report_id>synthetic-1</report_id><date_range><begin>1767225600</begin><end>1767311999</end></date_range></report_metadata>
<policy_published><domain>example.org</domain><adkim>r</adkim><aspf>r</aspf><p>none</p><sp>none</sp><pct>100</pct></policy_published>
<record><row><source_ip>192.0.2.10</source_ip><count>8</count>
<policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf></policy_evaluated></row>
<identifiers><header_from>example.org</header_from></identifiers>
<auth_results><dkim><domain>example.org</domain><result>pass</result><selector>s1</selector></dkim>
<spf><domain>example.org</domain><result>pass</result></spf></auth_results></record>
<record><row><source_ip>198.51.100.7</source_ip><count>2</count>
<policy_evaluated><disposition>none</disposition><dkim>fail</dkim><spf>fail</spf></policy_evaluated></row>
<identifiers><header_from>example.org</header_from></identifiers>
<auth_results><spf><domain>other.example</domain><result>fail</result></spf></auth_results></record>
</feedback>'''
LONG = ('La clinica dental ofrece limpieza profesional ortodoncia invisible y blanqueamiento '
        'con citas en linea todos los dias de la semana para pacientes nuevos y recurrentes')
CASES = {
    'networkx': {'dataset': 'demo', 'edges': [['home', 'servicios'], ['home', 'contacto'],
                 ['servicios', 'contacto'], ['blog', 'home'], ['contacto', 'home']]},
    'statsmodels': {'dataset': 'demo', 'values': [10 + 2 * i + (0.5 if i % 2 else -0.5) for i in range(12)]},
    'polars': {'dataset': 'demo', 'currency': 'MXN', 'rows': CAMPAIGNS},
    'ibis': {'dataset': 'demo', 'currency': 'MXN', 'rows': CAMPAIGNS},
    'sqlglot': {'dataset': 'demo', 'dialect': 'duckdb', 'sql':
                "WITH recent AS (SELECT id, channel FROM leads WHERE created_at > '2026-01-01') "
                "SELECT r.channel, count(*) AS n FROM recent r JOIN payments p ON p.lead_id = r.id GROUP BY 1"},
    'faker': {'dataset': 'demo', 'count': 3, 'seed': 7, 'locale': 'es_MX'},
    'pandera': {'dataset': 'demo', 'schema': {
        'lead_id': {'type': 'int', 'nullable': False, 'minimum': 1},
        'score': {'type': 'float', 'nullable': True, 'minimum': 0, 'maximum': 1},
        'channel': {'type': 'str', 'nullable': False}},
        'rows': [{'lead_id': 1, 'score': 0.4, 'channel': 'organic'},
                 {'lead_id': 2, 'score': None, 'channel': 'ads'},
                 {'lead_id': 0, 'score': 0.9, 'channel': 'ads'},
                 {'lead_id': 4, 'score': 1.7, 'channel': 'referral'}]},
    'datasketch': {'dataset': 'demo', 'threshold': 0.5, 'documents': [
        {'id': 'landing-a', 'content': LONG + ' en Polanco'},
        {'id': 'landing-b', 'content': LONG + ' en Coyoacan'},
        {'id': 'garden', 'content': 'Muebles de jardin con mesas sillas y sombrillas para terrazas amplias y patios'}]},
    'h3': {'dataset': 'demo', 'resolution': 7,
           'points': [[19.4326, -99.1332], [19.4327, -99.1331], [19.4333, -99.1900]]},
    'lifelines': {'dataset': 'demo', 'durations': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                  'observed': [1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1]},
    'pyod': {'dataset': 'demo', 'contamination': 0.1, 'rows': _CLUSTER + [[9.0, 9.0], [-7.0, 12.0]]},
    'river': {'dataset': 'demo', 'values': [0.9 if i % 2 else 1.1 for i in range(120)] +
              [4.9 if i % 2 else 5.1 for i in range(120)]},
    'numpy-financial': {'dataset': 'demo', 'currency': 'MXN', 'rate': 0.1,
                        'cashflows_minor': [-100000, 40000, 40000, 40000, 40000]},
    'nashpy': {'dataset': 'demo', 'payoffs_row': [[3, 0], [5, 1]], 'payoffs_column': [[3, 5], [0, 1]]},
    'pymcdm': {'dataset': 'demo', 'criteria': ['cost', 'benefit', 'benefit'], 'weights': [0.5, 0.25, 0.25],
               'alternatives': [{'id': 'plan-a', 'values': [250, 16, 12]},
                                {'id': 'plan-b', 'values': [200, 16, 8]},
                                {'id': 'plan-c', 'values': [300, 32, 16]}]},
    'mlxtend': {'dataset': 'demo', 'min_support': 0.5,
                'baskets': [['web', 'seo']] * 6 + [['web', 'ads']] * 2 + [['seo'], ['ads']]},
    'arrow': {'dataset': 'demo', 'rows': [{'channel': 'organic', 'leads': 10, 'rate': 0.3},
                                          {'channel': 'ads', 'leads': 4, 'rate': None}]},
    'markitdown': {'dataset': 'demo', 'html': '<html><head><title>T</title></head><body><h1>Citas dentales</h1>'
                   '<p>Agenda tu <a href="https://example.invalid/cita">cita</a> hoy.</p>'
                   '<ul><li>Limpieza</li><li>Ortodoncia</li></ul><script>alert(1)</script></body></html>'},
    'great-tables': {'dataset': 'demo', 'title': 'Leads por canal',
                     'rows': [{'canal': 'organico', 'leads': 10}, {'canal': 'anuncios', 'leads': 4}]},
    'spacy': {'dataset': 'demo', 'language': 'es', 'text':
              'Agenda tu cita dental hoy. La clinica ofrece limpieza dental y ortodoncia. Llama para una cita.'},
    'parsedmarc': {'dataset': 'demo', 'xml': DMARC},
    'shap': {'dataset': 'demo', 'train_x': _SHAP_X, 'train_y': _SHAP_Y},
    'statsforecast': {'dataset': 'demo', 'values': [10, 20, 30, 40] * 6, 'horizon': 4, 'season_length': 4},
    'opendp': {'dataset': 'demo', 'true_count': 1000, 'epsilon': 1.0},
    'splink': {'dataset': 'demo', 'records': [
        {'id': 'a1', 'name': 'Maria Lopez', 'email': 'maria@example.org', 'phone': '5550001'},
        {'id': 'a2', 'name': 'Maria Lopes', 'email': 'maria@example.org', 'phone': '5550001'},
        {'id': 'b1', 'name': 'Juan Perez', 'email': 'juan@example.org', 'phone': '5550002'},
        {'id': 'c1', 'name': 'Ana Ruiz', 'email': 'ana@example.org', 'phone': '5550003'}]},
    'advertools': {'dataset': 'demo', 'products': ['dentista', 'ortodoncia'],
                   'words': ['precio', 'cerca'], 'match_types': ['Exact']},
    'dnstwist': {'dataset': 'demo', 'domain': 'example.com', 'limit': 20},
}


def assert_result(test, service, value):
    if service == 'networkx':
        test.assertEqual((4, 5), (value['nodes'], value['edges']))
        test.assertEqual('home', value['top'][0]['id'])
        test.assertAlmostEqual(0.386942, value['top'][0]['pagerank'], places=3)
        test.assertEqual(['blog'], value['without_inbound'])
        test.assertFalse(value['crawled_anything'])
    elif service == 'statsmodels':
        test.assertEqual(12, value['observations'])
        test.assertAlmostEqual(2.0, value['slope_per_step'], delta=0.1)
        test.assertGreater(value['r_squared'], 0.98)
        test.assertFalse(value['forecast_guarantee'])
    elif service in ('polars', 'ibis'):
        organic = value['channels'][0]
        test.assertEqual(('organic', 300, 1200, 10, 3), (organic['channel'], organic['spend_minor'],
                         organic['revenue_minor'], organic['leads'], organic['conversions']))
        test.assertEqual(0.3, organic['conversion_rate'])
        test.assertEqual({'spend_minor': 300, 'revenue_minor': 1500, 'leads': 11, 'conversions': 4}, value['totals'])
        test.assertFalse(value['bank_reconciled'])
    elif service == 'sqlglot':
        test.assertEqual(1, value['statements'])
        test.assertEqual(['select'], value['statement_kinds'])
        test.assertTrue(value['read_only'])
        test.assertTrue({'leads', 'payments'} <= set(value['tables']))
        test.assertFalse(value['executed'])
    elif service == 'faker':
        test.assertEqual(3, len(value['contacts']))
        test.assertTrue(all(c['email'].rsplit('@', 1)[1] in ('example.org', 'example.com', 'example.net')
                            for c in value['contacts']))
        test.assertTrue(value['synthetic'])
        test.assertFalse(value['real_people'])
    elif service == 'pandera':
        test.assertEqual(4, value['rows'])
        test.assertFalse(value['valid'])
        test.assertEqual(2, value['failed_checks'])
        test.assertEqual({'lead_id', 'score'}, {f['column'] for f in value['failures']})
        test.assertFalse(value['values_returned'])
    elif service == 'datasketch':
        test.assertEqual(1, value['pairs_found'])
        test.assertEqual(('landing-a', 'landing-b'), (value['pairs'][0]['a'], value['pairs'][0]['b']))
        test.assertGreater(value['pairs'][0]['estimated_jaccard'], 0.7)
    elif service == 'h3':
        test.assertEqual((3, 2), (value['points'], value['cells']))
        test.assertEqual(2, value['top_cells'][0]['count'])
        test.assertFalse(value['coordinates_returned'])
    elif service == 'lifelines':
        test.assertEqual((12, 9), (value['subjects'], value['events']))
        probabilities = [row['probability'] for row in value['survival']]
        test.assertEqual(sorted(probabilities, reverse=True), probabilities)
        test.assertTrue(all(0 <= v <= 1 for v in probabilities))
        test.assertGreater(value['median_survival'], 3)
    elif service == 'pyod':
        test.assertEqual(32, value['rows'])
        test.assertTrue({30, 31} <= set(value['outlier_indices']))
        test.assertLessEqual(value['outliers'], 5)
    elif service == 'river':
        test.assertEqual(240, value['observations'])
        test.assertGreaterEqual(value['drifts'], 1)
        test.assertTrue(120 <= value['drift_indices'][0] < 240)
        test.assertAlmostEqual(3.0, value['mean'], delta=0.01)
    elif service == 'numpy-financial':
        test.assertEqual(26795, value['npv_minor'])
        test.assertAlmostEqual(0.2186, value['irr_per_period'], delta=0.001)
        test.assertEqual(3, value['payback_period'])
        test.assertFalse(value['investment_advice'])
    elif service == 'nashpy':
        test.assertEqual(1, value['equilibria_found'])
        test.assertEqual([0.0, 1.0], value['equilibria'][0]['row_strategy'])
        test.assertEqual([0.0, 1.0], value['equilibria'][0]['column_strategy'])
    elif service == 'pymcdm':
        test.assertEqual({'plan-a', 'plan-b', 'plan-c'}, {r['id'] for r in value['ranking']})
        scores = [r['score'] for r in value['ranking']]
        test.assertEqual(sorted(scores, reverse=True), scores)
        test.assertTrue(all(0 <= s <= 1 for s in scores))
    elif service == 'mlxtend':
        test.assertEqual(3, value['itemsets_found'])
        test.assertEqual([{'items': ['web'], 'support': 0.8}, {'items': ['seo'], 'support': 0.7},
                          {'items': ['seo', 'web'], 'support': 0.6}], value['itemsets'])
    elif service == 'arrow':
        test.assertEqual(2, value['rows'])
        columns = {c['name']: c for c in value['columns']}
        test.assertEqual((4, 10), (columns['leads']['minimum'], columns['leads']['maximum']))
        test.assertEqual(1, columns['rate']['nulls'])
        test.assertFalse(value['values_returned'])
    elif service == 'markitdown':
        test.assertTrue(value['markdown'].startswith('# Citas dentales'))
        test.assertIn('[cita](https://example.invalid/cita)', value['markdown'])
        test.assertNotIn('alert(1)', value['markdown'])
        test.assertFalse(value['fetched_remote_content'])
    elif service == 'great-tables':
        test.assertEqual(2, value['rows'])
        test.assertIn('Leads por canal', value['html'])
        test.assertIn('organico', value['html'])
        test.assertFalse(value['published'])
    elif service == 'spacy':
        test.assertEqual(3, value['sentences'])
        terms = {t['term']: t['count'] for t in value['top_terms']}
        test.assertEqual(2, terms.get('cita'))
        test.assertEqual(2, terms.get('dental'))
        test.assertFalse(value['trained_model_loaded'])
    elif service == 'parsedmarc':
        test.assertEqual('example.org', value['domain'])
        test.assertEqual((10, 8, 2), (value['messages'], value['dmarc_aligned'], value['dmarc_failed']))
        test.assertEqual({'none': 10}, value['dispositions'])
        test.assertFalse(value['source_ips_returned'])
    elif service == 'shap':
        test.assertEqual(60, value['rows'])
        test.assertGreater(value['features'][0]['share'], 0.8)
        test.assertFalse(value['causal_claim'])
    elif service == 'statsforecast':
        test.assertEqual([10.0, 20.0, 30.0, 40.0], value['seasonal_naive'])
        test.assertEqual([25.0] * 4, value['historic_average'])
        test.assertTrue(value['baseline_models_only'])
    elif service == 'opendp':
        test.assertIsInstance(value['noisy_count'], int)
        test.assertLess(abs(value['noisy_count'] - 1000), 100)
        test.assertAlmostEqual(1.0, value['epsilon'], places=3)
        test.assertFalse(value['true_count_returned'])
    elif service == 'splink':
        test.assertEqual(4, value['records'])
        test.assertEqual(1, value['pairs_found'])
        test.assertEqual(('a1', 'a2'), (value['candidate_pairs'][0]['a'], value['candidate_pairs'][0]['b']))
        test.assertFalse(value['merged_anything'])
    elif service == 'advertools':
        test.assertGreater(value['keywords'], 0)
        test.assertEqual({'Exact'}, {row['match_type'] for row in value['sample']})
        test.assertIn('dentista precio', {row['keyword'] for row in value['sample']})
        test.assertFalse(value['spend_executed'])
    elif service == 'dnstwist':
        test.assertGreater(value['permutations'], 20)
        test.assertEqual(20, len(value['sample']))
        test.assertNotIn('example.com', {row['domain'] for row in value['sample']})
        test.assertFalse(value['dns_lookups_made'])
    else:
        test.fail('No assertions for ' + service)
