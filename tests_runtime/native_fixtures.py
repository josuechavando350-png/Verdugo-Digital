CASES = {
    'promptfoo': {'dataset':'demo','text':'solar energy report','required_terms':['solar','energy']},
    'log4brains': {'dataset':'demo','decisions':[{'title':'One engine','status':'accepted'},{'title':'One product','status':'proposed'}]},
    'lighthouse': {'dataset':'demo','descriptions':['Solar energy report.']},
    'slidev': {'dataset':'demo','text':'# Overview\n\nOne product.\n\n---\n\n# Evidence\n\nVerified execution.\n<!-- Internal speaker note -->'},
    'geo-lint': {'dataset':'demo','title':'Report','description':'An example','text':'# Introduction\n\nShort report.'},
    'site-md': {'dataset':'demo','html':'<title>Report</title><article><h1>Results</h1><p>Sample report.</p></article>'},
    'seo-graph': {'dataset':'demo','host':'example.invalid','entries':[{'slug':'home','name':'Home'},{'slug':'report','name':'Report'}]},
    'structured-data-validator': {'dataset':'demo','graph': {'@context':'https://schema.org','@graph':[
        {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','name':'Home','position':1,'item':'https://example.invalid/'}]}]}},
}


def assert_result(test, sid, value):
    if sid == 'promptfoo':
        test.assertTrue(value['passed']);test.assertEqual(1,value['score']);test.assertEqual(0,value['llm_calls'])
    elif sid == 'log4brains':
        test.assertEqual(2,value['decisions_in_input']);test.assertEqual({'accepted':1,'proposed':1},value['status_counts'])
        test.assertFalse(value['repository_modified'])
    elif sid == 'lighthouse':
        test.assertEqual(1, value['score']); test.assertFalse(value['performance_audited'])
    elif sid == 'slidev':
        test.assertEqual(2, value['count'])
        test.assertEqual(['Overview', 'Evidence'], [s['title'] for s in value['slides']])
        test.assertEqual('Internal speaker note', value['slides'][1]['notes'])
        test.assertFalse(value['rendered']); test.assertFalse(value['external_resources_loaded'])
    elif sid == 'geo-lint':
        test.assertGreater(value['issues'], 0); test.assertIn('title-too-short', value['rules'])
        test.assertFalse(value['search_ranking_verified'])
    elif sid == 'site-md':
        test.assertEqual('Report', value['title']); test.assertIn('Sample report.', value['markdown']); test.assertFalse(value['fetched'])
    elif sid == 'seo-graph':
        test.assertEqual(2, value['entries']); test.assertEqual(2, len(value['graph']['@graph'][0]['itemListElement']))
        test.assertFalse(value['published'])
    elif sid == 'structured-data-validator':
        test.assertGreater(value['warnings'], 0); test.assertIn('itemListElement', value['fields'])
        test.assertFalse(value['search_eligibility_verified'])
