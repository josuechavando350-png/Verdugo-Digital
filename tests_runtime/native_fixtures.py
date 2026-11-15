CASES = {
    'geo-lint': {'dataset':'demo','title':'Report','description':'An example','text':'# Introduction\n\nShort report.'},
    'site-md': {'dataset':'demo','html':'<title>Report</title><article><h1>Results</h1><p>Sample report.</p></article>'},
    'seo-graph': {'dataset':'demo','host':'example.invalid','entries':[{'slug':'home','name':'Home'},{'slug':'report','name':'Report'}]},
    'structured-data-validator': {'dataset':'demo','graph': {'@context':'https://schema.org','@graph':[
        {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','name':'Home','position':1,'item':'https://example.invalid/'}]}]}},
}


def assert_result(test, sid, value):
    if sid == 'geo-lint':
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
