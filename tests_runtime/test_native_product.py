import copy
from contextlib import closing
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_native, product
from verdugo.__main__ import template
from verdugo.engine import Engine
from native_fixtures import CASES, assert_result


class NativeProduct(unittest.TestCase):
    def test_original_npm_operations_compose_and_restart(self):
        selected = set(filter(None, os.getenv('VERDUGO_RUNTIME_SERVICES','').split(',')))
        if selected and not set(CASES) <= selected: self.skipTest('Other runtime group selected')
        missing = [s for s in CASES if not local_native.runtime_state(s)['version_matches']]
        if missing:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1': self.fail('Missing native profiles')
            self.skipTest('Native profile not installed')
        config = template('nexus')
        for sid in CASES: config['tenants']['nexus']['services'][sid].update(enabled=True,license_reviewed=True,runtime_reviewed=True)
        tasks = [{'id':s,'service':s,'params':copy.deepcopy(p)} for s,p in CASES.items()]
        by_service = {task['service']: task for task in tasks}
        by_service['geo-lint']['params']['text'] = {'$ref':'analysis-site-md.result.markdown'}
        by_service['geo-lint']['depends_on'] = ['analysis-site-md']
        by_service['structured-data-validator']['params']['graph'] = {'$ref':'analysis-seo-graph.result.graph'}
        by_service['structured-data-validator']['depends_on'] = ['analysis-seo-graph']
        request={'id':'native-demo','services':[],'dataset':'demo','currency':'MXN','analyses':tasks}
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)/'state.db'
            with closing(Engine(state,config)) as e:
                first=product.observe(e,request,True)
                self.assertEqual('succeeded',first['state'],json.dumps(first))
                rows={x['service']:x['analysis']['result'] for x in first['analyses']}
                self.assertIn('Sample report.',rows['site-md']['markdown'])
                self.assertGreater(rows['geo-lint']['issues'],0)
                self.assertEqual(2,rows['seo-graph']['entries'])
                self.assertEqual(0,rows['structured-data-validator']['issues'])
                for sid in CASES:
                    if sid not in ('geo-lint', 'structured-data-validator'):assert_result(self,sid,rows[sid])
                self.assertEqual(len(CASES)+1,e.db.execute("SELECT count(*) FROM runs WHERE state='succeeded'").fetchone()[0])
            with closing(Engine(state,config)) as e, patch('verdugo.local_runtime.execute',side_effect=AssertionError('Replay executed worker')):
                replay=product.observe(e,request,True)
                self.assertEqual('succeeded',replay['state']);self.assertEqual(len(CASES),replay['reused_analyses'])
                for a,b in zip(first['analyses'],replay['analyses']):self.assertEqual(a['analysis'],b['analysis'])
