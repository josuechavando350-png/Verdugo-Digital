"""Unit guards only; authentic Formbricks acceptance requires the native workflow."""
import importlib.util
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('fb_native',ROOT/'scripts/native-pair-acceptance.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
from native_formbricks import Formbricks, ADMIN_BOOTSTRAP

class FormbricksGuards(TestCase):
    def test_bootstrap_is_only_administrative(self):
        for table in ('organization','organizationBilling','workspace','apiKey','apiKeyWorkspace'):
            self.assertIn('p.'+table+'.create',ADMIN_BOOTSTRAP)
        for table in ('survey','response','contact'):
            self.assertNotIn('p.'+table+'.',ADMIN_BOOTSTRAP)
        self.assertIn('bootstrap_requires_empty_instance',ADMIN_BOOTSTRAP)
    def test_native_authorization_is_not_disabled(self):
        import inspect
        source=inspect.getsource(Formbricks.install)
        self.assertIn("'AUTHZED_ENABLED':'true'",source)
        self.assertIn("'formbricks-authzed','upgrade','prepare'",source)
        self.assertIn("'formbricks_spicedb'",source)
    def test_readback_requires_original_survey_and_response_identity(self):
        a=Formbricks(n);a.base='http://127.0.0.1:3000';a.headers={};a.survey_id='s1';a.response_id='r1';a.question='q1'
        a.identity={'event_id':'event1','route':'route1'};a.http=Mock()
        survey={'data':{'id':'s1','name':'Native event1'}}
        response={'data':{'id':'r1','surveyId':'s1','data':{'q1':'route1'}}}
        a.http.call.side_effect=[survey,response];self.assertTrue(a.read())
        for bad in [{'id':'wrong','surveyId':'s1','data':{'q1':'route1'}},
                    {'id':'r1','surveyId':'other','data':{'q1':'route1'}},
                    {'id':'r1','surveyId':'s1','data':{'q1':'other'}}]:
            a.http.call.side_effect=[survey,{'data':bad}];self.assertFalse(a.read())
    def test_uses_official_application_not_local_survey_stub(self):
        self.assertRegex(Formbricks.images['formbricks'],r'^ghcr.io/formbricks/formbricks@sha256:[0-9a-f]{64}$')
        self.assertEqual(Formbricks.id,'formbricks')
        for ref in Formbricks.images.values():self.assertRegex(ref,r'@sha256:[0-9a-f]{64}$')
    def test_successful_empty_health_probe_is_not_a_timeout(self):
        import inspect
        self.assertIn("'-addr=localhost:50051',timeout=10) or True",inspect.getsource(Formbricks.install))

if __name__=='__main__':main()
