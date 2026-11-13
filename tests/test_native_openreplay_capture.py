"""Protocol and confinement guards, not a substitute for original capture services."""
import importlib.util
import inspect
import sys
import tempfile
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('capture_native',ROOT/'scripts/native-pair-acceptance.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
from native_openreplay_capture import OpenReplayCapture,uint,text,frame,synthetic_batch
from native_extra_apps import NativeSession
class CaptureGuards(TestCase):
    def test_varint_and_framing_match_original_message_protocol(self):
        self.assertEqual(uint(0),b'\x00');self.assertEqual(uint(127),b'\x7f')
        self.assertEqual(uint(128),b'\x80\x01');self.assertEqual(uint(300),b'\xac\x02')
        self.assertEqual(text('a'),b'\x01a');self.assertEqual(frame(30,b'\x01a\x01b'),b'\x1e\x04\x00\x00\x01a\x01b')
        for bad in (-1,2**64,True):
            with self.assertRaises(ValueError):uint(bad)
    def test_synthetic_batch_contains_real_dom_and_shared_event_without_secrets(self):
        identity={'route':'route-123','subject':'hashed-subject','event_name':'event-name','event_id':'event-uuid'}
        data=synthetic_batch(1000,identity)
        self.assertTrue(data.startswith(b'\x51\x01\x00\x00\xd0\x0f'))
        self.assertIn(b'route-123',data);self.assertIn(b'event-uuid',data)
        self.assertIn(frame(7),data);self.assertIn(frame(14,uint(3)+text('route-123')),data)
        self.assertLess(len(data),1024)
    def test_shared_writes_are_limited_to_private_disposable_child_directories(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as other:
            root=Path(d);child=root/'capture';child.mkdir()
            self.assertIn('src='+str(child),n.private_writable_mount(child,root,'/mnt/efs'))
            for path,dest in [(root,'/mnt/efs'),(Path(other),'/mnt/efs'),(child,'/etc')]:
                with self.assertRaises(n.AcceptanceError):n.private_writable_mount(path,root,dest)
            link=root/'link';link.symlink_to(child)
            with self.assertRaises(n.AcceptanceError):n.private_writable_mount(link,root,'/mnt/efs')
    def test_capture_does_not_insert_business_records_directly(self):
        code=inspect.getsource(OpenReplayCapture)
        for statement in ('INSERT INTO','redis-cli\',\'XADD','open(\'dom.mob'):
            self.assertNotIn(statement,code)
        self.assertIn('/v1/web/start',code);self.assertIn('/v1/web/i',code)
        self.assertIn('object_storage_archive_verified=False',code)
    def test_native_replay_requires_same_subject_route_event_and_stored_dom(self):
        a=OpenReplayCapture(n);a.replay_api='http://127.0.0.1:8080';a.project_id=1;a.session_id='123';a.headers={}
        a.identity={'subject':'s','route':'r','event_name':'name','event_id':'uuid'};a.http=Mock()
        replay={'data':{'projectId':1,'sessionId':'123','userId':'s','metadata':{'verdugo_route':'r'}}}
        events={'data':{'userEvents':[{'name':'name','properties':{'route':'r','event_id':'uuid'}}]}}
        dom=b'\xff'*8+b'\x01r'
        a.http.call.side_effect=[replay,events,dom];self.assertTrue(a.read_capture())
        a.http.call.side_effect=[replay,{'data':{'userEvents':events['data']['userEvents']*2}}];self.assertFalse(a.read_capture())
        a.http.call.side_effect=[replay,events,b'not-a-dom-file-r'];self.assertFalse(a.read_capture())
    def test_binary_transport_retains_origin_and_size_constraints(self):
        session=NativeSession(n)
        with self.assertRaisesRegex(n.AcceptanceError,'extra_origin_not_authorized'):
            session.call('http://external.invalid/i',body_bytes=b'x')
        for kwargs in ({'data':{},'body_bytes':b'x'},{'body_bytes':b'x'*1_048_577},{'body_bytes':'not-bytes'}):
            with self.assertRaisesRegex(n.AcceptanceError,'extra_invalid_binary_body'):
                session.call('http://127.0.0.1:1/i',**kwargs)
if __name__=='__main__':main()
