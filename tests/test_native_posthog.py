"""Unit guards, not proof of analytics capture or original service installation."""
import importlib.util
import inspect
import sys
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('ph_native',ROOT/'scripts/native-pair-acceptance.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
from native_posthog import PostHog, ADMIN_BOOTSTRAP
class PostHogGuards(TestCase):
    def test_only_administration_is_bootstrapped(self):
        for code in ('Organization.objects.create','Team.objects.create','User.objects.create_and_join','mint_personal_api_key'):
            self.assertIn(code,ADMIN_BOOTSTRAP)
        for code in ('FeatureFlag.objects','Event.objects','INSERT INTO'):
            self.assertNotIn(code,ADMIN_BOOTSTRAP)
        self.assertIn('bootstrap_requires_empty_organization',ADMIN_BOOTSTRAP)
    def test_no_test_mode_or_authentication_bypass(self):
        source=inspect.getsource(PostHog.install)
        self.assertIn('python manage.py migrate --noinput',source)
        self.assertIn('posthog.wsgi:application',source)
        for code in ("'TEST':'", "'E2E_TESTING':'", "'DEBUG':'"):
            self.assertNotIn(code,source)
    def test_readback_requires_persisted_id_key_and_route(self):
        a=PostHog(n);a.base='http://127.0.0.1:8000';a.http=Mock();a.headers={}
        a.path='/api/projects/1/feature_flags/';a.flag_id=1;a.flag_key='native-1';a.identity={'route':'r1'}
        correct={'id':1,'key':'native-1','name':'r1','active':True}
        a.http.call.return_value=correct;self.assertTrue(a.read())
        for key in correct:
            a.http.call.return_value={**correct,key:'wrong'};self.assertFalse(a.read())
    def test_scope_does_not_claim_analytics_ingestion(self):
        self.assertIn("'event_capture_verified':False",inspect.getsource(PostHog.exchange))
        self.assertEqual(PostHog.images['posthog'],'posthog/posthog:latest')
if __name__=='__main__':main()
