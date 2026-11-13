"""Guard/unit tests only; original three-product acceptance still requires Docker."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/native-pair-acceptance.py'
spec = importlib.util.spec_from_file_location('native_trio', SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

BASE_CHECKS = ['verdugo_persisted_lead', 'mautic_created_and_read_back', 'countly_recorded_and_read_back',
               'mautic_after_restart', 'countly_after_restart', 'verdugo_after_restart']
TRIO_CHECKS = ['growthbook_feature_created_and_read_back', 'growthbook_to_mautic_route',
               'countly_route_read_back', 'growthbook_after_restart', 'countly_route_after_restart']

class NativeTrioGuardTests(unittest.TestCase):
    def tearDown(self):
        native.NATIVE_ORIGINS.clear()
        native.REDACT.clear()

    def test_pair_success_is_not_trio_success(self):
        report = native.evidence_base(True)
        report['checks'] = dict.fromkeys(BASE_CHECKS, True)
        with self.assertRaisesRegex(native.AcceptanceError, 'incomplete_native_acceptance'):
            native.require_all_checks(report)
        report['checks'].update(dict.fromkeys(TRIO_CHECKS, True))
        native.require_all_checks(report)
        self.assertEqual(report['verified_originals'], ['growthbook', 'mautic', 'countly'])
        self.assertFalse(report['all_ten_integrated'])
        self.assertFalse(report['persistent_installation'])
        self.assertFalse(report['android_verified'])

    def test_every_trio_readback_is_required(self):
        for key in TRIO_CHECKS:
            report = native.evidence_base(True)
            report['checks'] = dict.fromkeys(BASE_CHECKS + TRIO_CHECKS, True)
            report['checks'][key] = False
            with self.subTest(check=key):
                with self.assertRaises(native.AcceptanceError):
                    native.require_all_checks(report)

    def test_report_and_runtime_profile_must_match(self):
        with self.assertRaisesRegex(native.AcceptanceError, 'native_profile_mismatch'):
            native.run_acceptance(native.evidence_base(False), include_growthbook=True)

    def test_growthbook_image_is_immutable(self):
        self.assertRegex(native.GROWTHBOOK_IMAGE, r'^growthbook/growthbook@sha256:[a-f0-9]{64}$')

    def test_contact_route_comes_from_readback_not_an_assumed_label(self):
        self.assertEqual(native.contact_route({'tags': [{'tag':'a'}, {'tag':'b'}]}, 'b'), 'b')
        self.assertEqual(native.contact_route({'tags': {'4': {'tag':'b'}}}, 'b'), 'b')
        with self.assertRaisesRegex(native.AcceptanceError, 'mautic_growthbook_route_mismatch'):
            native.contact_route({'tags':[{'tag':'other'}]}, 'b')

    def test_native_origins_are_exact_and_can_be_rediscovered(self):
        def info(ip):
            return {'NetworkSettings': {'Networks': {'own-net': {'IPAddress': ip}}}}
        self.assertEqual(native.native_origin(info('172.20.0.5'),'own-net',3100),'http://172.20.0.5:3100')
        native.NATIVE_ORIGINS.clear()
        self.assertEqual(native.native_origin(info('172.20.0.6'),'own-net',3100),'http://172.20.0.6:3100')
        with self.assertRaises(native.AcceptanceError):
            native.request('http://172.20.0.5:3100/healthcheck')
        for address in ['8.8.8.8', '0.0.0.0', '127.0.0.1', '::1']:
            with self.subTest(address=address):
                with self.assertRaises(native.AcceptanceError):
                    native.native_origin(info(address),'own-net',3100)
        with self.assertRaises(native.AcceptanceError):
            native.native_origin(info('172.20.0.7'),'other-net',3100)

    def test_growthbook_bootstrap_uses_original_rest_contracts(self):
        calls=[]
        remembered={}
        def http(url, *, data=None, headers=None, **kwargs):
            calls.append((url,data,headers))
            if url.endswith('/healthcheck'):return {'healthy':True}
            if url.endswith('/auth/firsttime'):return {'token':'registration-token','projectId':'project-one'}
            if url.endswith('/auth/login'):return {'token':'access-token'}
            if url.endswith('/user'):return {'organizations':[{'id':'org-one'}]}
            if url.endswith('/keys'):
                self.assertEqual(headers['X-Organization'], 'org-one')
                return {'key':{'key':'generated-native-admin-key'}}
            if url.endswith('/api/v1/features'):
                remembered.update(data)
                return {'feature': {'id':data['id']}}
            return {'feature': {'defaultValue':remembered['defaultValue']}}
        with patch.object(native,'request',side_effect=http):
            state=native.initialize_growthbook('http://172.20.0.5:3100','temporary-password')
        self.assertEqual(state['route'],remembered['defaultValue'])
        self.assertEqual(len(calls),7)
        self.assertIn('generated-native-admin-key',native.REDACT)
        self.assertEqual(calls[5][2],{'Authorization':'Bearer generated-native-admin-key'})

if __name__ == '__main__':
    unittest.main()
