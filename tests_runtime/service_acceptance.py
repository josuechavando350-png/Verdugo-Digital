"""Disposable real-server acceptance; no target URL or production data inputs.

CI supplies two hash-checked, community release binaries. All writes provision
synthetic test fixtures in fresh private directories bound to 127.0.0.1. They
are NOT exposed as an Engine operation or an MCP deployment/approval tool.
"""
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo.__main__ import template
from verdugo.engine import Engine


def request(port, path, token, service, method='GET', body=None):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    headers = {'api-key': token} if service == 'qdrant' else {'Authorization': 'Bearer '+token}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    try:
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        response = conn.getresponse()
        payload = response.read(1024*1024+1)
        if len(payload) > 1024*1024 or not 200 <= response.status < 300:
            raise RuntimeError('Synthetic server request failed: HTTP '+str(response.status))
        return json.loads(payload) if payload else {}
    finally:
        conn.close()


@contextmanager
def server(service, binary, port, token):
    with tempfile.TemporaryDirectory(prefix='verdugo-service-') as temp:
        directory = Path(temp)
        env = {'PATH':os.defpath, 'HOME':temp, 'TMPDIR':temp, 'LANG':'C.UTF-8',
               'RUST_LOG':'info'}
        if service == 'qdrant':
            settings = {'log_level':'INFO','telemetry_disabled':True,
                'service':{'host':'127.0.0.1','http_port':port,'grpc_port':None,
                           'api_key':token,'enable_cors':False},
                'cluster':{'enabled':False},
                'storage':{'storage_path':str(directory/'storage')}}
            config = directory/'fixture.json'
            config.write_text(json.dumps(settings));config.chmod(0o600)
            env.update(QDRANT__SERVICE__HOST='127.0.0.1',
                       QDRANT__SERVICE__HTTP_PORT=str(port),
                       QDRANT__SERVICE__API_KEY=token,QDRANT__TELEMETRY_DISABLED='true')
            args = [binary,'--config-path',str(config),'--disable-telemetry']
            ready_path = '/collections'
        else:
            env.update(MEILI_HTTP_ADDR='127.0.0.1:'+str(port),
                       MEILI_MASTER_KEY=token, MEILI_NO_ANALYTICS='true',
                       MEILI_ENV='production', MEILI_DB_PATH=str(directory/'database'))
            args = [binary]
            ready_path = '/version'
        with tempfile.TemporaryFile() as logs:
            process = subprocess.Popen(args, cwd=temp, env=env, stdin=subprocess.DEVNULL,
                stdout=logs, stderr=logs, start_new_session=True)
            try:
                deadline = time.monotonic()+40
                last_error = None
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(service+' exited before readiness')
                    try:
                        request(port, ready_path, token, service)
                        break
                    except (OSError, RuntimeError, ValueError) as error:
                        last_error = type(error).__name__+': '+str(error)
                        time.sleep(0.2)
                else:
                    raise RuntimeError(service+' readiness failed: '+str(last_error))
                yield
            except Exception:
                # Only this fixed synthetic harness may emit server diagnostics.
                # Remove the freshly generated test credential and bound output.
                logs.flush();logs.seek(0)
                diagnostic = logs.read(16384).decode('utf-8',errors='replace')
                print('SYNTHETIC SERVER DIAGNOSTICS '+service, file=sys.stderr)
                print(diagnostic.replace(token,'<redacted-test-key>'), file=sys.stderr)
                raise
            finally:
                try:
                    os.killpg(process.pid,signal.SIGTERM)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=5)
                except ProcessLookupError:
                    pass


def check(service, binary, port, expected_version):
    if not Path(binary).is_file() or not Path(binary).is_absolute():
        raise ValueError('A trusted, pre-verified absolute binary path is required')
    token = secrets.token_urlsafe(32)
    with server(service,binary,port,token):
        if service == 'qdrant':
            version = request(port,'/',token,service)['version']
            request(port,'/collections/synthetic',token,service,'PUT',
                    {'vectors':{'size':4,'distance':'Cosine'}})
            operation = 'collections.list'
        else:
            version = request(port,'/version',token,service)['pkgVersion']
            task = request(port,'/indexes',token,service,'POST',{'uid':'synthetic','primaryKey':'id'})
            deadline = time.monotonic()+15
            while time.monotonic() < deadline:
                outcome = request(port,'/tasks/'+str(task['taskUid']),token,service)
                if outcome['status'] == 'succeeded':
                    break
                if outcome['status'] in ('failed','canceled'):
                    raise RuntimeError('Synthetic index creation failed')
                time.sleep(0.1)
            else:
                raise RuntimeError('Synthetic index was not ready within the test budget')
            operation = 'indexes.list'
        if version != expected_version:
            raise AssertionError('Actual server version differs from pinned release')
        envname = 'VERDUGO_SYNTHETIC_'+service.upper()+'_TOKEN'
        config = template('nexus')
        config['tenants']['nexus']['services'][service].update(
            enabled=True,license_reviewed=True,version=expected_version,
            base_url='http://127.0.0.1:'+str(port),allow_local_http=True,token_env=envname)
        with patch.dict(os.environ,{envname:token}):
            engine = Engine(':memory:',config)
            try:
                command={'service':service,'operation':operation,'params':{},'key':'real-server-read'}
                result=engine.execute(command,True)
                if result['state']!='succeeded':
                    raise AssertionError('Engine did not successfully read the actual '+service+' server')
                data=result['result']
                identifiers=([x['name'] for x in data['result']['collections']] if service=='qdrant'
                             else [x['uid'] for x in data['results']])
                if 'synthetic' not in identifiers:
                    raise AssertionError('Actual server response omitted the seeded test object')
                with patch.object(engine,'transport',side_effect=AssertionError('Duplicate HTTP request')):
                    replay=engine.execute(command,True)
                if not replay['replayed'] or replay['result']!=data:
                    raise AssertionError('Actual server read was not persisted idempotently')
                with patch.dict(os.environ,{envname:'incorrect-synthetic-key'}):
                    rejected=engine.execute(dict(command,key='negative-credential-test'),True)
                if rejected['state']!='failed':
                    raise AssertionError('Actual server accepted invalid authentication')
                if token in json.dumps(engine.events()):
                    raise AssertionError('Synthetic server credential leaked into audit events')
            finally:
                engine.close()
        return {'service':service,'server_version':version,'operation':operation,
                'actual_http_result':'passed','fixture_identity':'passed',
                'invalid_credential_rejected':'passed','idempotent_replay':'passed',
                'scope':'disposable loopback instance','production_certified':False}


if __name__=='__main__':
    rows=[check('qdrant',os.environ['VERDUGO_QDRANT_TEST_BINARY'],16333,'1.20.0'),
          check('meilisearch',os.environ['VERDUGO_MEILI_TEST_BINARY'],17700,'1.56.2')]
    evidence={'schema':'verdugo.real-service-acceptance.v1','checks':rows,
              'synthetic_only':True,'production_certified':False,'permanent_services_created':False}
    Path(os.environ['VERDUGO_SERVICE_EVIDENCE']).write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))
