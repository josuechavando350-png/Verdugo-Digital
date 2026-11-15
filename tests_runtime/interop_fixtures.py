"""Synthetic inputs; all assertions run against the installed original SDKs."""
from verdugo.local_interop import TOOLS

HTML = '<html><head><title>Local campaign article</title><meta name="description" content="Campaign analysis supplied by the operator"></head><body><article><h1>Local campaign article</h1>'+('<p>Appointment automation helps the team manage requests and measure campaign results. The local report uses supplied observations and makes no promise of future revenue.</p>'*5)+'</article></body></html>'
DMARC = '''<feedback><version>1.0</version><report_metadata><org_name>Example</org_name><email>reports@example.invalid</email><report_id>demo-1</report_id><date_range><begin>1704067200</begin><end>1704153600</end></date_range></report_metadata><policy_published><domain>example.invalid</domain><adkim>r</adkim><aspf>r</aspf><p>none</p><sp>none</sp><pct>100</pct></policy_published><record><row><source_ip>192.0.2.1</source_ip><count>7</count><policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf></policy_evaluated></row><identifiers><header_from>example.invalid</header_from></identifiers><auth_results><dkim><domain>example.invalid</domain><selector>demo</selector><result>pass</result></dkim><spf><domain>example.invalid</domain><scope>mfrom</scope><result>pass</result></spf></auth_results></record></feedback>'''
CASES = {
    **{sid: {'dataset': 'demo', 'currency': 'MXN', 'rows': [
        {'channel': 'organic', 'spend_minor': 100, 'revenue_minor': 300, 'leads': 3, 'conversions': 1},
        {'channel': 'paid', 'spend_minor': 200, 'revenue_minor': 800, 'leads': 4, 'conversions': 2}]} for sid in TOOLS},
    **{sid: {'dataset': 'demo', 'candidate': '{"campaign":"local","spend_minor":300}'} for sid in ('guardrails', 'instructor', 'outlines')},
    'llm-guard': {'dataset': 'demo', 'text': 'Contact demo@example.invalid for the report.'},
    'sentence-transformers': {'dataset': 'demo', 'left': [[1., 0.], [0., 1.]], 'right': [[1., 0.], [0., 1.]]},
    'transformers': {'dataset': 'demo', 'text': 'Hello campaign', 'vocabulary': ['[PAD]', '[UNK]', '[CLS]', '[SEP]', '[MASK]', 'hello', 'campaign']},
    'bertopic': {'dataset': 'demo', 'counts': [[8, 1, 0], [0, 1, 8]]},
    'ax': {'dataset': 'demo', 'scores': [0.1, 0.2, 0.8, 0.9]*3, 'labels': [0, 0, 1, 1]*3},
    'geo-optimizer': {'dataset': 'demo', 'html': HTML},
    'parsedmarc': {'dataset': 'demo', 'xml': DMARC},
    'cdx-toolkit': {'dataset': 'demo', 'captures': [{'timestamp': '20260101000000', 'status': 200, 'mime': 'text/html'}, {'timestamp': '20260102000000', 'status': 404, 'mime': 'text/html'}]},
    'news-please': {'dataset': 'demo', 'html': HTML},
}


def assert_result(t, sid, r):
    if sid in TOOLS:
        t.assertEqual(300, r['spend_minor']); t.assertEqual(1100, r['revenue_minor']); t.assertEqual(2, r['rows'])
        t.assertEqual(sid, r['sdk']); t.assertEqual(0, r['model_calls']); t.assertFalse(r['agent_reasoning_tested'])
    elif sid in ('guardrails', 'instructor', 'outlines'):
        t.assertTrue(r['valid']); t.assertEqual(0, r['model_calls']); t.assertFalse(r['content_truth_verified'])
    elif sid == 'llm-guard':
        t.assertNotIn('demo@example.invalid', r['text']); t.assertFalse(r['passed']); t.assertFalse(r['all_sensitive_data_removed'])
    elif sid == 'sentence-transformers':
        t.assertEqual([[1., 0.], [0., 1.]], r['similarities']); t.assertFalse(r['embeddings_generated'])
    elif sid == 'transformers':
        t.assertEqual([2, 5, 6, 3], r['unit_ids']); t.assertEqual(['hello', 'campaign'], r['lexical_units']); t.assertFalse(r['pretrained_model_used'])
    elif sid == 'bertopic':
        t.assertGreater(r['weights'][0][0], r['weights'][0][1]); t.assertEqual(0, r['weights'][0][2]); t.assertEqual(2, r['classes']); t.assertFalse(r['topics_discovered'])
    elif sid == 'ax':
        t.assertEqual(1., r['f1']); t.assertIn(r['threshold'], (0.25, 0.5, 0.75)); t.assertEqual(5, r['evaluated_candidates']); t.assertFalse(r['out_of_sample_verified'])
    elif sid == 'geo-optimizer':
        t.assertTrue(r['has_title']); t.assertTrue(r['has_description']); t.assertFalse(r['has_canonical']); t.assertFalse(r['page_fetched'])
    elif sid == 'parsedmarc':
        t.assertEqual(7, r['message_count']); t.assertEqual({'none': 7}, r['dispositions']); t.assertEqual(0, r['dns_lookups'])
    elif sid == 'cdx-toolkit':
        t.assertEqual(2, r['captures']); t.assertEqual(1, r['successful']); t.assertEqual('20260101000000', r['first_capture']); t.assertEqual(0, r['captures_fetched'])
    elif sid == 'news-please':
        t.assertIn('campaign', r['title']); t.assertIn('Appointment automation', r['text']); t.assertFalse(r['page_fetched']); t.assertFalse(r['images_fetched'])
    else: t.fail('Missing interoperability result assertions: '+sid)
