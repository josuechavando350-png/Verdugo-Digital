import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer
from verdugo.adapters import build
from verdugo.engine import Engine
from verdugo.transport import resolve, send, TransportError
from verdugo.mcp import Session, serve, tool_definitions


class TransportTests(unittest.TestCase):
    def test_metadata_and_loopback_blocked(self):
        for ip in ('169.254.169.254','127.0.0.1','0.0.0.0','224.0.0.1'):
            with self.subTest(ip=ip),patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))]):
                with self.assertRaises(TransportError):resolve('fixture',443)

    def test_link_local_still_blocked_with_private_opt_in(self):
        with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('169.254.169.254',443))]):
            with self.assertRaises(TransportError):resolve('fixture',443,True,True)

    def test_private_requires_opt_in(self):
        addr=(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.1.2.3',443))
        with patch('socket.getaddrinfo',return_value=[addr]):
            with self.assertRaises(TransportError):resolve('fixture',443)
            self.assertEqual(addr,resolve('fixture',443,True))

    def test_real_loopback_http_wire_and_redirect_rejection(self):
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                received.append((self.path,self.headers.get('Authorization')))
                if 'page=2' in self.path:
                    self.send_response(302);self.send_header('Location','http://127.0.0.1:1');self.end_headers();return
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                self.wfile.write(b'{"items": []}')
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        cfg={'base_url':'http://127.0.0.1:'+str(server.server_port),'token_env':'VERDUGO_TEST_TOKEN',
             'allow_local_http':True,'version':'fixture'}
        try:
            with patch.dict(os.environ,{'VERDUGO_TEST_TOKEN':'wire-fixture-token'}):
                self.assertEqual({'items':[]},send(build('umami','websites.list',{},cfg),cfg))
                self.assertEqual(('/api/websites?page=1','Bearer wire-fixture-token'),received[0])
                with self.assertRaises(TransportError):send(build('umami','websites.list',{'page':2},cfg),cfg)
                self.assertEqual(2,len(received))
        finally:
            server.shutdown();server.server_close();thread.join(2)


class MCPTests(unittest.TestCase):
    def setUp(self):
        self.engine=Engine(':memory:')
        self.s=Session(self.engine)
    def tearDown(self):self.engine.close()
    def handshake(self):
        result=self.s.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}})
        self.s.handle({'jsonrpc':'2.0','method':'notifications/initialized'})
        return result
    def test_handshake_and_list(self):
        self.assertEqual('2025-11-25',self.handshake()['result']['protocolVersion'])
        res=self.s.handle({'jsonrpc':'2.0','id':2,'method':'tools/list'})
        self.assertEqual(21,len(res['result']['tools']))
    def test_no_approval_tool_exposed(self):
        self.assertFalse(any('approve' in t['name'] for t in tool_definitions()))
    def test_session_required(self):
        self.assertIn('error',self.s.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'}))
    def test_tool_notification_never_executes(self):
        self.handshake()
        self.assertIsNone(self.s.handle({'jsonrpc':'2.0','method':'tools/call','params':{'name':'verdugo_status'}}))
        self.assertEqual([],self.engine.events())
    def test_tenant_injection_rejected(self):
        self.handshake()
        out=self.s.handle({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'verdugo_status','arguments':{'tenant':'other'}}})
        self.assertTrue(out['result']['isError'])
    def test_status_has_no_fake_live_integrations(self):
        self.handshake()
        out=self.s.handle({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'verdugo_status','arguments':{}}})
        data=json.loads(out['result']['content'][0]['text'])
        self.assertEqual(100,data['registered']);self.assertEqual(0,data['live_verified'])
    def test_bad_json_does_not_pollute_stdout(self):
        out=io.StringIO();serve(self.engine,io.StringIO('{not-json}\n'),out)
        msg=json.loads(out.getvalue());self.assertEqual(-32700,msg['error']['code'])
    def test_bad_request_id(self):
        out=self.s.handle({'jsonrpc':'2.0','id':{},'method':'initialize'})
        self.assertEqual(-32600,out['error']['code'])
    def test_actual_stdio_process(self):
        with tempfile.TemporaryDirectory() as d:
            messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}},
                      {'jsonrpc':'2.0','method':'notifications/initialized'},
                      {'jsonrpc':'2.0','id':2,'method':'tools/list'}]
            out=subprocess.run([sys.executable,'-m','verdugo','--state',str(Path(d)/'db'),'mcp'],
                input='\n'.join(json.dumps(m) for m in messages)+'\n',text=True,capture_output=True,timeout=10)
            self.assertEqual(0,out.returncode,out.stderr)
            lines=[json.loads(line) for line in out.stdout.splitlines()]
            self.assertEqual(2,len(lines));self.assertEqual(21,len(lines[1]['result']['tools']))
