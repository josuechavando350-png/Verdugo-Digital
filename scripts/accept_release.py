#!/usr/bin/env python3
"""Acceptance of the extracted artifact: install without Node/Git, backup and restart."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request


def accept(archive):
    with tempfile.TemporaryDirectory(prefix='verdugo-release-') as directory:
        root = Path(directory); home = root/'operator'; home.mkdir(mode=0o700)
        with tarfile.open(archive) as bundle: bundle.extractall(root, filter='data')
        app = next(root.glob('verdugo-digital-*'))
        blocked = root/'no-dev-tools'; blocked.mkdir()
        for name in ('node', 'npm', 'git'):
            script = blocked/name; script.write_text('#!/bin/sh\necho "Development tool unexpectedly invoked" >&2\nexit 86\n'); script.chmod(0o700)
        env = dict(os.environ, VERDUGO_HOME=str(home), PATH=str(blocked)+os.pathsep+os.environ['PATH'], PYTHON=sys.executable)
        for key in ('CODESPACES', 'CODESPACE_NAME', 'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN'): env.pop(key, None)
        def command(*args, environment=env):
            return subprocess.check_output(args, cwd=app, env=environment, text=True, timeout=180)
        verified = json.loads(command(sys.executable, '-m', 'verdugo.release'))
        command('bash', 'scripts/activar.sh', '--panel', '--solo-instalar')
        python = str(home/('panel-venv-'+verified['version'])/'bin/python')
        @contextmanager
        def server(state_home):
            with socket.socket() as sock: sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            base = 'http://127.0.0.1:'+str(port)
            proc = subprocess.Popen([python, '-m', 'verdugo', '--config', str(state_home/'config.json'),
                    '--state', str(state_home/'estado.sqlite'), 'panel', '--port', str(port)],
                    cwd=app, env=env | {'VERDUGO_HOME': str(state_home)}, stdout=subprocess.DEVNULL)
            try:
                for _ in range(200):
                    if proc.poll() is not None: raise RuntimeError('Extracted panel failed to start')
                    try:
                        with urllib.request.urlopen(base, timeout=1) as response: assert response.status == 200
                        break
                    except (OSError, urllib.error.URLError): time.sleep(.05)
                else: raise RuntimeError('Panel start timeout')
                token = (state_home/'panel-operator.token').read_text().strip(); csrf = ''
                def api(path, body=None):
                    request = urllib.request.Request(base+'/api'+path, data=json.dumps(body).encode() if body is not None else None,
                        headers={'X-Verdugo-Token': token, 'X-Verdugo-CSRF': csrf, 'Origin': base, 'Content-Type':'application/json'})
                    with urllib.request.urlopen(request, timeout=10) as response: return json.load(response)
                csrf = api('/session')['csrf']
                yield api
            finally:
                proc.terminate()
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=10)
        with server(home) as api:
            api('/tenants', {'tenant':'cliente-demo', 'confirm':True})
            api('/clients/cliente-demo/register', {'label':'Cliente demo','confirm':True})
            api('/clients/cliente-demo/pay', {'months':1,'confirm':True})
            api('/sales/intake', {'tenant':'cliente-demo','confirm':True,'request':{'lead_id':'lead-demo',
                'name':'Cliente demo','email':'demo@example.invalid','dataset':'demo','channel':'paid','evidence_ref':'synthetic-intake'}})
            api('/sales/win', {'tenant':'cliente-demo','confirm':True,'request':{'event_id':'sale-demo',
                'lead_id':'lead-demo','payment_id':'pay-demo','dataset':'demo','channel':'paid','evidence_ref':'synthetic-sale',
                'amount_minor':120025,'cost_minor':20000,'currency':'MXN'}})
            before = api('/funnel?tenant=cliente-demo&dataset=demo')['sales']
            assert before['reported_paid_clients'] == 1
            saved = api('/maintenance/backup', {'confirm':True})
            assert api('/installation')['state'] == 'local_checks_passed'
            assert api('/product?tenant=cliente-demo')['product']['live_verified'] == 0
        restored = root/'recovered'
        response = json.loads(command(python, '-m', 'verdugo', 'restore-product', '--from', saved['saved_directory'], '--to', str(restored), '--execute'))
        assert response['state'] == 'restored_offline' and not response['external_calls_made']
        with server(restored) as api:
            after = api('/funnel?tenant=cliente-demo&dataset=demo')['sales']
            # These two fields describe the new query window, not persisted business data.
            query_times = {'window_start_utc', 'window_end_utc'}
            assert {k:v for k,v in after.items() if k not in query_times} == {k:v for k,v in before.items() if k not in query_times}
            assert after['window_end_utc'] >= before['window_end_utc']
            assert api('/funnel?tenant=cliente-demo&dataset=real')['sales']['reported_paid_clients'] == 0
            assert next(c for c in api('/clients')['clients'] if c['tenant']=='cliente-demo')['active']
        return {'state':'passed', 'source_commit':verified['source_commit'], 'version':verified['version'],
                'extracted_install_without_node_npm_git':True, 'loopback_panel_started_twice':True,
                'backup_restore_commercial_parity':True, 'synthetic_only':True, 'live_verified':0}


if __name__ == '__main__': print(json.dumps(accept(sys.argv[1])))
