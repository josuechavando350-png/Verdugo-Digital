"""Contract tests are synthetic; only the native workflow can accept four originals."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
native=load('native_four','native-pair-acceptance.py')
rudder=load('rudder_native','native_rudderstack.py')
BASE=['verdugo_persisted_lead','mautic_created_and_read_back','countly_recorded_and_read_back',
      'mautic_after_restart','countly_after_restart','verdugo_after_restart',
      'growthbook_feature_created_and_read_back','growthbook_to_mautic_route','countly_route_read_back',
      'growthbook_after_restart','countly_route_after_restart']
EXTRA=['rudderstack_gateway_accepted','rudderstack_rejects_missing_auth','rudderstack_delivery_after_restart']

class RudderNativeGuards(unittest.TestCase):
    def tearDown(self):
        native.REDACT.clear();native.NATIVE_ORIGINS.clear()

    def test_three_originals_do_not_satisfy_four_profile(self):
        report=native.evidence_base(True,True);report['checks']=dict.fromkeys(BASE,True)
        with self.assertRaises(native.AcceptanceError):native.require_all_checks(report)
        report['checks'].update(dict.fromkeys(EXTRA,True));native.require_all_checks(report)
        self.assertEqual(report['verified_originals'],['growthbook','mautic','rudderstack','countly'])
        self.assertFalse(report['all_ten_integrated']);self.assertFalse(report['persistent_installation'])
        self.assertFalse(report['android_verified'])

    def test_rudder_profile_cannot_be_silently_ignored(self):
        with self.assertRaisesRegex(native.AcceptanceError,'native_transport_profile_mismatch'):
            native.run_acceptance(native.evidence_base(True,True),include_growthbook=True)
        report=native.evidence_base(False,True)
        report['checks']=dict.fromkeys(BASE+EXTRA,True)
        with self.assertRaises(native.AcceptanceError):native.require_all_checks(report)

    def test_each_delivery_and_auth_gate_is_mandatory(self):
        for check in EXTRA:
            report=native.evidence_base(True,True);report['checks']=dict.fromkeys(BASE+EXTRA,True)
            report['checks'][check]=False
            with self.subTest(check=check):
                with self.assertRaises(native.AcceptanceError):native.require_all_checks(report)

    def test_native_http_destination_maps_countly_form_fields(self):
        config=rudder.workspace_config('w'*32,'c'*32,'http://countly.native.invalid:3001')
        source=config['sources'][0];dest=source['destinations'][0]
        self.assertEqual(source['writeKey'],'w'*32);self.assertTrue(dest['isProcessorEnabled'])
        self.assertEqual(dest['destinationDefinition']['name'],'HTTP')
        self.assertEqual(dest['config']['format'],'FORM')
        self.assertFalse(dest['config']['isDefaultMapping'])
        self.assertEqual({p['to'] for p in dest['config']['propertiesMapping']},{'$.app_key','$.device_id','$.events'})
        self.assertEqual(dest['config']['apiUrl'],'http://countly.native.invalid:3001/i')
        self.assertEqual(len(source['destinations']),1)

    def test_destination_cannot_be_changed_to_an_external_host(self):
        for url in ['https://example.com','http://evil.invalid:3001','http://countly.native.invalid:3001@evil.invalid',
                    'http://countly.native.invalid:80','http://countly.native.invalid:3001/other',
                    'http://countly.native.invalid:3001?api_key=x']:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):rudder.workspace_config('w'*32,'c'*32,url)

    def test_gateway_success_is_not_downstream_success(self):
        report=native.evidence_base(True,True)
        facade=Mock();facade.AcceptanceError=native.AcceptanceError
        facade.request.return_value={'http_status':200,'body':'OK'}
        adapter=rudder.RudderStackTransport(facade)
        adapter.base='http://172.20.0.8:8080';adapter.write_key='w'*32;adapter.report=report
        params={'app_key':'k'*32,'device_id':'synthetic-id','events':'[{"key":"sample","count":1}]'}
        adapter.deliver(params,'event-id')
        self.assertTrue(report['checks']['rudderstack_gateway_accepted'])
        self.assertNotIn('countly_recorded_and_read_back',report['checks'])
        self.assertEqual(facade.request.call_count,1)
        self.assertEqual(facade.request.call_args.args[0],'http://172.20.0.8:8080/v1/track')
        self.assertEqual(facade.request.call_args.kwargs['data']['messageId'],'event-id')
        self.assertEqual(report['verified_originals'],[])
        with self.assertRaises(native.AcceptanceError):native.require_all_checks(report)

    def test_gateway_wrong_response_does_not_claim_acceptance(self):
        facade=Mock();facade.AcceptanceError=native.AcceptanceError
        facade.request.return_value={'http_status':200,'body':'unexpected'}
        adapter=rudder.RudderStackTransport(facade);adapter.write_key='w'*32
        adapter.base='http://172.20.0.8:8080';adapter.report=native.evidence_base(True,True)
        with self.assertRaises(native.AcceptanceError):
            adapter.deliver({'app_key':'k'*32,'device_id':'synthetic','events':'[{"key":"sample","count":1}]'},'event-id')
        self.assertNotIn('rudderstack_gateway_accepted',adapter.report['checks'])

if __name__=='__main__':unittest.main()
