"""Ephemeral original Caddy + test-only authenticated proxy, isolated in CI.

Run explicitly with VERDUGO_CADDY_TEST_BINARY and VERDUGO_CADDY_BUILD_INFO.
No deployment, credentials, customer data, DNS or public listener is created.
"""
from contextlib import closing
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdugo.__main__ import template
from verdugo.engine import Engine
from verdugo.operations_reads import PINNED_COMMITS
from verdugo import product

PIN = '7591cff1fb03202ce022982af020197f3f387220'
TOKEN = 'synthetic-caddy-acceptance-only'
ROUTE = '/config/apps/http/servers'


def request(port, path, token=None):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        conn.request('GET', path, headers={'Authorization': 'Bearer '+token} if token else {})
        response = conn.getresponse()
        return response.status, response.read(1024*1024+1)
    finally:
        conn.close()


def ports():
    # Reserve both simultaneously so they cannot accidentally be the same port.
    with socket.socket() as first, socket.socket() as second:
        first.bind(('127.0.0.1', 0)); second.bind(('127.0.0.1', 0))
        return first.getsockname()[1], second.getsockname()[1]


def main():
    binary = Path(os.environ['VERDUGO_CADDY_TEST_BINARY']).resolve(strict=True)
    build_info = Path(os.environ['VERDUGO_CADDY_BUILD_INFO']).read_text()
    assert PINNED_COMMITS['caddy'] == PIN
    assert 'vcs.revision='+PIN in build_info and 'vcs.modified=false' in build_info
    assert 'github.com/caddyserver/caddy/v2/cmd/caddy' in build_info
    admin_port, http_port = ports()
    forwarded = []
    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            if not hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+TOKEN):
                self.send_response(401); self.end_headers(); return
            if self.path != ROUTE:
                self.send_response(404); self.end_headers(); return
            forwarded.append(self.path)
            status, data = request(admin_port, ROUTE)
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers(); self.wfile.write(data)
    with tempfile.TemporaryDirectory(prefix='verdugo-caddy-') as directory:
        root=Path(directory)
        cfg={'admin':{'listen':'127.0.0.1:%d'%admin_port},
             'apps':{'http':{'servers':{'fixture':{
                 'listen':['127.0.0.1:%d'%http_port],
                 'automatic_https':{'disable':True},
                 'routes':[{'handle':[{'handler':'static_response','body':'synthetic-caddy-page'}]}]}}}}}
        config_path=root/'caddy.json'; config_path.write_text(json.dumps(cfg))
        with (root/'server.log').open('wb') as log:
            proc=subprocess.Popen([str(binary),'run','--config',str(config_path)],
                stdout=log,stderr=log,cwd=root,
                env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),
                     'XDG_DATA_HOME':str(root/'data'),'XDG_CONFIG_HOME':str(root/'config')})
            proxy=None; thread=None
            try:
                deadline=time.monotonic()+20
                while True:
                    if proc.poll() is not None: raise AssertionError('Original Caddy did not remain running')
                    try:
                        if request(admin_port,ROUTE)[0]==200: break
                    except (OSError,http.client.HTTPException): pass
                    if time.monotonic()>=deadline: raise AssertionError('Caddy did not become ready')
                    time.sleep(.05)
                assert request(http_port,'/') == (200,b'synthetic-caddy-page')
                proxy=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
                thread=threading.Thread(target=lambda:proxy.serve_forever(poll_interval=.05),daemon=True)
                thread.start()
                proxy_port=proxy.server_port
                assert request(proxy_port,ROUTE)[0]==401
                assert request(proxy_port,ROUTE,'wrong-fixture-token')[0]==401
                assert request(proxy_port,'/config/',TOKEN)[0]==404
                assert not forwarded
                config=template('nexus')
                service=config['tenants']['nexus']['services']['caddy']
                service.update(enabled=True,license_reviewed=True,version=PIN,
                    base_url='http://127.0.0.1:%d'%proxy_port,allow_local_http=True,
                    proxy_auth_reviewed=True)
                observation={'id':'caddy-original-v019','services':['caddy'],'dataset':'demo','currency':'MXN'}
                with patch.dict(os.environ,{service['token_env']:TOKEN}):
                    with closing(Engine(root/'state.sqlite3',config)) as engine:
                        result=product.observe(engine,observation,True)
                        assert result['state']=='succeeded', result
                        summary=result['services'][0]['observation']
                        assert summary['http_servers_in_response']==1
                        assert summary['listeners_in_response']==1
                        assert summary['routes_in_response']==1
                    with closing(Engine(root/'state.sqlite3',config)) as engine:
                        resumed=product.observe(engine,observation,True)
                        assert resumed['reused_observations']==1
                        service['proxy_auth_reviewed']=False
                        assert product.observe(engine,observation,True)['state']=='blocked'
                assert forwarded==[ROUTE]
                evidence={'source_commit':PIN,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                    'verdugo_commit':os.environ.get('GITHUB_SHA'),
                    'actual_upstream_servers_executed':['caddy'],
                    'proxy':'test_only_python_fixed_route_bearer',
                    'proxy_missing_and_wrong_credentials_rejected':True,
                    'proxy_other_paths_rejected':True,'upstream_reads_from_engine':len(forwarded),
                    'original_server_projection':summary,'restart_reused_observations':resumed['reused_observations'],
                    'fixture_data_only':True,'permanent_deployment':False,'live_verified':0,
                    'other_new_upstreams_executed':False}
                output=Path(os.environ['VERDUGO_CADDY_EVIDENCE'])
                output.write_text(json.dumps(evidence,indent=2)+'\n')
                print(json.dumps(evidence,sort_keys=True))
            finally:
                if proxy is not None:
                    proxy.shutdown(); proxy.server_close()
                    if thread is not None: thread.join(3)
                proc.terminate()
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)


if __name__=='__main__': main()
