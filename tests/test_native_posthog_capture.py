"""Fail-closed safety contracts for the original PostHog capture pipeline.

These unit tests do not certify Rust capture/Kafka/ClickHouse running.
"""
import importlib.util
from pathlib import Path
import sys
from unittest import TestCase,main
from unittest.mock import Mock
import json
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('native_ph_guard',root/'scripts/native-pair-acceptance.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
from native_posthog_capture import recorded_event, normalize_event_result, PostHogCapture, IMAGES
from native_posthog import PostHog

EVENT={'event_id':'5fe62e6a-905e-4ba2-8e34-7fb55e1942be','event_name':'verdugo-test',
       'subject':'pseudonymous-user','route':'native-route'}

class PostHogCaptureGuards(TestCase):
    def result(self, **changes):
        return {'results':[{'uuid':EVENT['event_id'],'event':EVENT['event_name'],
                    'distinct_id':EVENT['subject'],
                    'properties':{'verdugo_route':EVENT['route'],'native_synthetic':True},**changes}]}

    def test_valid_original_api_readback_is_not_just_status_200(self):
        self.assertTrue(recorded_event(self.result(),event_id=EVENT['event_id'],
            event_name=EVENT['event_name'],subject=EVENT['subject'],route=EVENT['route']))
        self.assertFalse(recorded_event({'status':1},event_id=EVENT['event_id'],
            event_name=EVENT['event_name'],subject=EVENT['subject'],route=EVENT['route']))
        self.assertFalse(recorded_event({'results':[]},event_id=EVENT['event_id'],
            event_name=EVENT['event_name'],subject=EVENT['subject'],route=EVENT['route']))

    def test_wrong_event_identity_route_subject_and_duplicates_fail(self):
        args=dict(event_id=EVENT['event_id'],event_name=EVENT['event_name'],
                  subject=EVENT['subject'],route=EVENT['route'])
        for field in ('uuid','event','distinct_id'):
            with self.subTest(field=field):
                self.assertFalse(recorded_event(self.result(**{field:'wrong'}),**args))
        self.assertFalse(recorded_event({'results':[{'uuid':EVENT['event_id'],
            'event':EVENT['event_name'],'distinct_id':EVENT['subject'],
            'properties':{'verdugo_route':'wrong','native_synthetic':True}}]},**args))
        data=self.result()
        self.assertFalse(recorded_event({'results':data['results']*2},**args))
        self.assertFalse(recorded_event({'results':[{'uuid':EVENT['event_id'],
            'event':EVENT['event_name'],'distinct_id':EVENT['subject'],
            'properties':{'verdugo_route':EVENT['route'],'native_synthetic':False}}]},**args))

    def test_json_serialized_original_properties_can_be_verified(self):
        data=self.result()
        data['results'][0]['properties']=json.dumps(data['results'][0]['properties'])
        self.assertTrue(recorded_event(data,event_id=EVENT['event_id'],
            event_name=EVENT['event_name'],subject=EVENT['subject'],route=EVENT['route']))

    def test_capture_cannot_run_without_native_service_and_project_token(self):
        a=PostHog(native)
        cap=PostHogCapture(a)
        with self.assertRaises(native.AcceptanceError):
            cap.capture_and_readback(EVENT,project_token='s'*32)
        cap.base='http://127.0.0.1:3000'
        with self.assertRaises(native.AcceptanceError):
            cap.capture_and_readback(EVENT,project_token='short')

    def test_capture_posts_to_original_not_django_feature_flags(self):
        app=Mock()
        app.n=native
        app.team=1
        app.headers={'Authorization':'Bearer synthetic-key'}
        app.base='http://127.0.0.1:8000'
        app.http.call.side_effect=[{'status':1},self.result()]
        app.wait.side_effect=lambda fn,seconds:fn()
        cap=PostHogCapture(app)
        cap.base='http://127.0.0.1:3000'
        self.assertTrue(cap.capture_and_readback(EVENT,project_token='p'*32))
        send=app.http.call.call_args_list[0]
        self.assertEqual(send.args[0],'http://127.0.0.1:3000/i/v0/e/')
        data=send.kwargs['data']
        self.assertEqual(data['uuid'],EVENT['event_id'])
        self.assertEqual(data['token'],'p'*32)
        self.assertEqual(data['properties']['verdugo_route'],EVENT['route'])
        self.assertFalse(data['properties']['$process_person_profile'])
        self.assertNotIn('email',json.dumps(data).lower())
        read=app.http.call.call_args_list[1]
        self.assertIn('/api/projects/1/events/',read.args[0])
        self.assertEqual(read.kwargs['headers'],app.headers)

    def test_http_acceptance_does_not_bypass_failed_readback(self):
        app=Mock()
        app.n=native
        app.team=1
        app.headers={'Authorization':'Bearer synthetic-key'}
        app.base='http://127.0.0.1:8000'
        app.http.call.side_effect=[{'status':1},{'results':[]}]
        def wait(fn,seconds):
            if not fn():raise native.AcceptanceError('readiness_timeout_not_read_back')
            return True
        app.wait.side_effect=wait
        cap=PostHogCapture(app);cap.base='http://127.0.0.1:3000'
        with self.assertRaises(native.AcceptanceError):
            cap.capture_and_readback(EVENT,project_token='p'*32)

    def test_images_are_original_not_test_servers(self):
        self.assertIn('ghcr.io/posthog/posthog/capture:',IMAGES['posthog_capture'])
        self.assertIn('ghcr.io/posthog/posthog-node:',IMAGES['posthog_ingestion'])
        self.assertIn('redpandadata/redpanda:',IMAGES['posthog_kafka'])
        for key in IMAGES:self.assertIn(key,PostHog.images)

if __name__=='__main__':
    main()
