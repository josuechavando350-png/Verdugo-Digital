"""Fixed synthetic request-state boundaries, not a browser certification."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from verdugo import local_browserstate666 as browserstate
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry


class BrowserState666Tests(unittest.TestCase):
    def test_real_cookies_urls_paths_and_ambiguous_flags_are_rejected(self):
        params={'dataset':'demo','cookies':[{'slot':0,'secure':True,'http_only':True,
                                           'same_site':'Strict','lifetime':'session'}]}
        browserstate.validate('playwright-python','cookies.check',params)
        for changes in ({'dataset':'real'},{'url':'https://example.invalid'},
                        {'storage_state':'private.json'},{'cookies':[]},
                        {'cookies':params['cookies']*17}):
            with self.subTest(changes=changes),self.assertRaises(VerdugoError):
                browserstate.validate('playwright-python','cookies.check',params|changes)
        for key,value in [('slot',True),('slot',8),('secure','true'),('http_only',1),
                          ('same_site','arbitrary'),('lifetime','future'),
                          ('value','private'),('domain','example.invalid'),('path','/')]:
            changed=copy.deepcopy(params);changed['cookies'][0][key]=value
            with self.subTest(key=key),self.assertRaises(VerdugoError):
                browserstate.validate('playwright-python','cookies.check',changed)

    def test_python_driver_and_node_are_pinned_separately(self):
        contract=json.loads(browserstate.CONTRACT.read_text())
        registered=next(r for r in read_registry()['records'] if r['id']=='playwright-python')
        self.assertEqual(registered['commit_sha'],contract['commit'])
        self.assertNotEqual(contract['commit'],contract['driver']['commit'])
        self.assertEqual(104,contract['source_python_files_verified'])
        self.assertEqual(contract['node']['binary_sha256'],contract['installed_artifacts'][
            'lib/python3.12/site-packages/playwright/driver/node'])

    def test_altered_driver_is_rejected_before_sdk_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'driver.js').write_text('altered')
            with self.assertRaises(VerdugoError):
                browserstate.verify_artifacts(root,{'installed_artifacts':{'driver.js':'0'*64}})
