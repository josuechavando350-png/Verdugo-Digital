CASES = {
    'chronos': {'dataset':'demo','values':[1,2,3,4]},
    'gliner': {'dataset':'demo','expected':[[{'label':'ORG','start':0,'end':1},{'label':'ORG','start':2,'end':3}]],
               'predicted':[[{'label':'ORG','start':0,'end':1}]]},
    'graphiti': {'dataset':'demo','items':['a','b','c','d','e'],'max_group':3},
    'openbb': {'dataset':'demo','currency':'MXN','rows':[{'date':'2026-01-02','open':10,'high':12,'low':9,'close':11,'volume':500}]},
    'people-also-ask': {'dataset':'demo','html':'<div class="related-question-pair">What is a campaign?</div><div class="related-question-pair">How is it measured?</div>'},
    'jobspy': {'dataset':'demo','html':'<p>Automation engineer</p><p>Remote position.</p>'},
}


def assert_result(test,sid,r):
    if sid == 'chronos':
        test.assertEqual(4,len(r['bins']));test.assertLess(r['maximum_absolute_error'],0.02);test.assertFalse(r['forecast_generated'])
    elif sid == 'gliner':
        test.assertEqual(1,r['precision']);test.assertEqual(.5,r['recall']);test.assertAlmostEqual(2/3,r['f_score']);test.assertFalse(r['entities_predicted'])
    elif sid == 'graphiti':
        test.assertEqual(10,r['covered_pairs']);test.assertTrue(r['coverage_verified']);test.assertFalse(r['graph_written'])
    elif sid == 'openbb':
        test.assertEqual(1,r['row_count']);test.assertEqual(11,r['rows'][0]['close']);test.assertFalse(r['market_data_fetched'])
    elif sid == 'people-also-ask':
        test.assertEqual(['What is a campaign?','How is it measured?'],r['questions']);test.assertFalse(r['search_executed'])
    elif sid == 'jobspy':
        test.assertEqual('Automation engineer Remote position.',r['text']);test.assertFalse(r['jobs_scraped'])
