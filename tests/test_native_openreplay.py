"""Unit guards; do not treat these as successful session capture."""
import importlib.util
import inspect
import sys
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('or_native',ROOT/'scripts/native-pair-acceptance.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
from native_openreplay import OpenReplay,source_schema
class OpenReplayGuards(TestCase):
    def test_only_administrative_data_seeded(self):
        source=inspect.getsource(OpenReplay.install)
        for table in ('tenants','users','basic_authentication'):self.assertIn('INSERT INTO public.'+table,source)
        for table in ('projects','sessions'):self.assertNotIn('INSERT INTO public.'+table,source)
        self.assertIn('source_schema(self.n,k)',source)
    def test_readback_requires_returned_project_and_shared_route(self):
        a=OpenReplay(n);a.base='http://127.0.0.1:8000';a.http=Mock();a.headers={};a.project_id=1;a.identity={'route':'shared-route'}
        correct={'projectId':1,'name':'shared-route','platform':'web'}
        a.http.call.return_value={'data':correct};self.assertTrue(a.read())
        for key in correct:
            a.http.call.return_value={'data':{**correct,key:'wrong'}};self.assertFalse(a.read())
    def test_scope_does_not_claim_session_capture(self):
        source=inspect.getsource(OpenReplay.exchange)
        self.assertIn("'session_capture_verified':False",source)
        self.assertRegex(OpenReplay.images['openreplay'],r'^public.ecr.aws/p1t3u8a3/chalice@sha256:[0-9a-f]{64}$')
    def test_synthetic_email_passes_native_email_syntax_without_delivery(self):
        source=inspect.getsource(OpenReplay.install)+inspect.getsource(OpenReplay.login)
        self.assertNotIn('operator@example.invalid',source)
        self.assertIn('operator@example.com',source)
        for ref in OpenReplay.images.values():self.assertRegex(ref,r'@sha256:[0-9a-f]{64}$')
    def test_schema_revision_mismatch_is_fatal(self):
        facade=Mock();facade.AcceptanceError=n.AcceptanceError;facade.command.return_value='wrong'
        with self.assertRaisesRegex(n.AcceptanceError,'source_revision_mismatch'):source_schema(facade,'init_pg_schema.sql')
if __name__=='__main__':main()
