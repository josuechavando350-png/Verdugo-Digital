"""Contract guards only: original CRM acceptance requires the Docker circuit."""
import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('native_crm_base',ROOT/'scripts/native-pair-acceptance.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
from native_crm_apps import Twenty, Erxes, graphql
from native_provider_registry import REGISTRY

class CRMGuards(unittest.TestCase):
    def test_registry_only_contains_implemented_originals(self):
        self.assertEqual(set(REGISTRY),{'dittofeed','twenty','erxes'})
        for key,kind in REGISTRY.items():self.assertEqual(kind.id,key)
    def test_graphql_does_not_accept_errors_or_leak_private_messages(self):
        app=Twenty(native);app.base='http://127.0.0.1:3000';app.http=Mock()
        app.http.call.return_value={'errors':[{'message':'secret-body','extensions':{'code':'UNAUTHORIZED'}}]}
        with self.assertRaisesRegex(native.AcceptanceError,'^twenty_graphql_UNAUTHORIZED$'):graphql(app,'query{__typename}',token='synthetic')
        app.http.call.return_value={'data':{'__typename':'Query'}}
        self.assertEqual(graphql(app,'query{__typename}'),{'__typename':'Query'})
    def test_twenty_readback_requires_uuid_and_route(self):
        app=Twenty(native);app.base='http://127.0.0.1:3000';app.http=Mock();app.headers={}
        app.identity={'event_id':'event1','route':'route1'}
        app.http.call.return_value={'data':{'person':{'id':'event1','jobTitle':'route1'}}};self.assertTrue(app.read())
        app.http.call.return_value={'data':{'person':{'id':'event2','jobTitle':'route1'}}};self.assertFalse(app.read())
        app.http.call.return_value={'data':{'person':{'id':'event1','jobTitle':'wrong'}}};self.assertFalse(app.read())
    def test_erxes_requires_returned_id_and_shared_event_code(self):
        app=Erxes(native);app.base='http://127.0.0.1:4000';app.http=Mock();app.contact_id='native-contact'
        app.identity={'event_id':'event1','route':'route1'}
        correct={'_id':'native-contact','code':'event1','description':'route1'}
        app.http.call.return_value={'data':{'customerDetail':correct}};self.assertTrue(app.read())
        for field in correct:
            app.http.call.return_value={'data':{'customerDetail':{**correct,field:'wrong'}}};self.assertFalse(app.read())
    def test_crm_images_are_original_publishers_not_mock_images(self):
        self.assertEqual(Twenty.images['twenty'],'twentycrm/twenty:latest')
        self.assertEqual(Erxes.images['erxes_core'],'erxes/erxes-next-core-api:3.4.21')
        self.assertEqual(Erxes.images['erxes_gateway'],'erxes/erxes-next-gateway:3.4.21')
    def test_erxes_authentication_result_is_verified(self):
        app=Erxes(native);app.base='http://127.0.0.1:4000';app.http=Mock();app.password='synthetic'
        app.http.call.return_value={'data':{'login':'not-logged-in'}}
        with self.assertRaisesRegex(native.AcceptanceError,'erxes_login_failed'):app.login()

if __name__=='__main__':unittest.main()
