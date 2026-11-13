"""Unit guards only; these do not count as installed original applications."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('native_extensions',ROOT/'scripts/native-extensions-acceptance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from native_extra_apps import NativeSession,Dittofeed

class ExtraGuards(unittest.TestCase):
    def tearDown(self):module.native.NATIVE_ORIGINS.clear();module.native.REDACT.clear()
    def test_reject_unknown_or_duplicate_provider(self):
        for selected in ([],['not-a-program'],['dittofeed','dittofeed']):
            with self.assertRaises(module.native.AcceptanceError):module.ExtendedTransport(selected)
    def test_provider_requires_readback_auth_and_restart(self):
        for phase in ('rejects_missing_auth','native_readback','after_restart'):
            report={'checks':{f'dittofeed_{k}':True for k in ('rejects_missing_auth','native_readback','after_restart')}}
            report['checks']['dittofeed_'+phase]=False
            original=Mock()
            with self.assertRaises(module.native.AcceptanceError):module.enforce_extended(report,['dittofeed'],original)
            original.assert_not_called()
    def test_five_is_not_ten(self):
        report={'checks':{f'dittofeed_{k}':True for k in ('rejects_missing_auth','native_readback','after_restart')},'verified_originals':list(module.BASE)}
        module.enforce_extended(report,['dittofeed'],lambda r:None)
        self.assertEqual(len(report['verified_originals']),5);self.assertFalse(report['all_ten_integrated'])
    def test_all_ten_metadata_contracts_are_not_full_capture_acceptance(self):
        selected=sorted(module.SIX)
        report={'checks':{f'{p}_{phase}':True for p in selected for phase in
            ('rejects_missing_auth','native_readback','after_restart')},'verified_originals':list(module.BASE),
            'extra_proof':{'posthog':{'event_capture_verified':False},'openreplay':{'session_capture_verified':False}}}
        # Passing ten metadata/write-readback gates is NOT enough without
        # the authentic PostHog event and OpenReplay session pipelines.
        with self.assertRaisesRegex(module.native.AcceptanceError,'posthog_original_event_capture_unverified'):
            module.enforce_extended(report,selected,lambda r:None)
        self.assertNotIn('all_ten_integrated',report)
        self.assertNotIn('production_ready',report)
    def test_posthog_metadata_only_never_counts_as_original_accepted(self):
        selected=['posthog']
        checks={f'posthog_{k}':True for k in
                ('rejects_missing_auth','native_readback','after_restart')}
        report={'checks':checks,'verified_originals':list(module.BASE),
                'extra_proof':{'posthog':{'event_capture_verified':False}}}
        with self.assertRaisesRegex(module.native.AcceptanceError,'posthog_original_event_capture_unverified'):
            module.enforce_extended(report,selected,lambda r:None)
        self.assertEqual(report['verified_originals'],list(module.BASE))

    def test_posthog_requires_new_event_capture_after_restart(self):
        selected=['posthog']
        checks={f'posthog_{k}':True for k in
                ('rejects_missing_auth','native_readback','after_restart','event_capture_readback',
                 'event_capture_after_restart')}
        report={'checks':checks,'verified_originals':list(module.BASE),
                'extra_proof':{'posthog':{
                    'event_capture_verified':True,'event_capture_after_restart_verified':False}}}
        with self.assertRaisesRegex(module.native.AcceptanceError,'posthog_original_event_capture_unverified'):
            module.enforce_extended(report,selected,lambda r:None)

    def test_openreplay_project_only_never_counts_as_session_capture(self):
        selected=['openreplay']
        checks={f'openreplay_{k}':True for k in
                ('rejects_missing_auth','native_readback','after_restart')}
        report={'checks':checks,'verified_originals':list(module.BASE),
                'extra_proof':{'openreplay':{'session_capture_verified':False}}}
        with self.assertRaisesRegex(module.native.AcceptanceError,'openreplay_original_session_capture_unverified'):
            module.enforce_extended(report,selected,lambda r:None)

    def test_session_rejects_remote_and_userinfo_before_request(self):
        session=NativeSession(module.native)
        for url in ('https://example.com','http://10.0.0.3','http://name:secret@127.0.0.1','file:///etc/passwd'):
            with self.assertRaises(module.native.AcceptanceError):session.call(url)
    def test_only_exact_private_origin_is_authorized(self):
        module.native.NATIVE_ORIGINS.add('http://172.20.0.5:3000')
        session=NativeSession(module.native)
        for url in ('http://172.20.0.5:3001','http://172.20.0.6:3000','http://172.20.0.5:3000@evil.invalid'):
            with self.assertRaises(module.native.AcceptanceError):session.call(url)
    def test_dittofeed_readback_requires_matching_message_subject_and_route(self):
        app=Dittofeed(module.native);app.base='http://127.0.0.1:3000';app.workspace='workspace'
        app.identity={'event_id':'event1','subject':'subject1','route':'route1','event_name':'name1'}
        app.http=Mock()
        row={'messageId':'event1','userId':'subject1','event':'name1','traits':json.dumps({'route':'route1'})}
        app.http.call.return_value={'events':[row]};self.assertTrue(app.read())
        app.http.call.return_value={'events':[row,row]};self.assertFalse(app.read())
        app.http.call.return_value={'events':[{**row,'traits':json.dumps({'route':'wrong'})}]};self.assertFalse(app.read())
    def test_dittofeed_has_own_original_image_and_dependencies(self):
        self.assertRegex(Dittofeed.images['dittofeed'],r'^dittofeed/dittofeed-lite@sha256:[0-9a-f]{64}$')
        self.assertIn('ditto_temporal',Dittofeed.images);self.assertIn('ditto_clickhouse',Dittofeed.images)

    def test_dittofeed_native_images_have_fixed_observed_digests(self):
        for image in Dittofeed.images.values():self.assertRegex(image,r'^[a-z0-9_/-]+@sha256:[0-9a-f]{64}$')

if __name__=='__main__':unittest.main()
