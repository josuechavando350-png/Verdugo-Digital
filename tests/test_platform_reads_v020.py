import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import platform_reads as batch, product, source_evidence
from verdugo.__main__ import template
from verdugo.adapters import build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo.read_contracts import check

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from platform_fixtures import TOKEN, PRIVATE, PATHS, REPLIES, EXPECTED, configure, wire


def command(sid, key='read'):
    return {'service': sid, 'operation': next(iter(batch.SPECS[sid])), 'params': {}, 'key': key}


class PlatformContracts(unittest.TestCase):
    def setUp(self):
        self.config = template('nexus'); env = configure(self.config)
        self.env = patch.dict(os.environ, env); self.env.start(); self.addCleanup(self.env.stop)

    def test_sources_cover_all_nine_pinned_contracts(self):
        rows = json.loads((Path(__file__).resolve().parents[1]/'sources/contracts-v020-platforms.json').read_text())['records']
        self.assertEqual(set(batch.SPECS), {row['id'] for row in rows})
        for row in rows:
            self.assertEqual(source_evidence.report(row['id'])['source_commit_sha'], row['commit'])
            self.assertEqual(batch.PINNED_COMMITS[row['id']], row['commit'])
            for item in row['files']: self.assertRegex(item['git_blob_sha'], r'^[a-f0-9]{40}$')

    def test_template_has_no_automatic_activation_or_proxy_review(self):
        for sid in batch.SPECS:
            cfg = template('nexus')['tenants']['nexus']['services'][sid]
            self.assertIs(False, cfg['enabled']); self.assertIs(False, cfg['license_reviewed'])
            self.assertNotIn('license_policy_exception', cfg)
            if sid in batch.PROXY_ONLY: self.assertIs(False, cfg['proxy_auth_reviewed'])

    def test_authentication_and_scope_changes_cannot_reuse_fingerprint(self):
        for sid in batch.SPECS:
            cfg = self.config['tenants']['nexus']['services'][sid]
            old = build(sid, command(sid)['operation'], {}, cfg)
            with patch.dict(os.environ, {cfg['token_env']: TOKEN+'changed'}):
                new = build(sid, command(sid)['operation'], {}, cfg)
            self.assertNotEqual(old['public']['credential_binding'], new['public']['credential_binding'])
            with self.assertRaises(VerdugoError): build(sid, command(sid)['operation'], {}, cfg | {'auth_mode': 'unreviewed'})
        cases = [('killbill', 'proxy_tenant_binding_reviewed'), ('jitsu', 'proxy_auth_reviewed'),
                 ('datahub', 'native_auth_enforced_reviewed'), ('bifrost', 'native_auth_enforced_reviewed'),
                 ('magentic-ui', 'user_scope_reviewed')]
        for sid, flag in cases:
            for value in (False, None, 1, 'true'):
                with self.assertRaises(VerdugoError):
                    build(sid, command(sid)['operation'], {}, self.config['tenants']['nexus']['services'][sid] | {flag: value})

    def test_types_boundaries_and_partial_envelopes_fail_closed(self):
        bad = {
            'datahub': [dict(REPLIES['datahub'], activeCount=True), dict(REPLIES['datahub'], entityType='user')],
            'jitsu': [{'status': 'fail'}, {'status': True}],
            'magentic-ui': [{'status': True, 'data': [{'session_id': 1}]}, {'status': 'true', 'data': []}],
            'operately': [{'companies': [{'id': 'one', 'setup_completed': 1}]}],
            'signoz': [{'status': 'success', 'data': {'dashboards': [], 'total': -1}}],
            'bifrost': [{'providers': [{'name': 'one'}], 'total': 0}],
            'killbill': [[{'accountId': 'one'}]*51, [{'accountId': 'one'}]*2],
            'taguette': [{'text_direction': 'AUTO', 'highlights': []}, {'text_direction': 'LEFT_TO_RIGHT', 'highlights': [{'id': 1, 'start_offset': 5, 'end_offset': 1, 'tags': []}]}],
            'ckanapi': [{'success': True, 'result': {'count': 1, 'results': [{'name': PRIVATE}]}}],
        }
        for sid, payloads in bad.items():
            for payload in [None, {'error': PRIVATE}, *payloads]:
                with self.subTest(service=sid), self.assertRaises(VerdugoError) as caught:
                    check(sid, command(sid)['operation'], payload)
                self.assertNotIn(PRIVATE, str(caught.exception))

    def test_loopback_product_uses_one_sqlite_then_replays_after_restart(self):
        request = {'id': 'platforms-nine', 'services': list(batch.SPECS), 'dataset': 'demo', 'currency': 'MXN'}
        with tempfile.TemporaryDirectory() as tmp, wire(self.config) as remote:
            state = Path(tmp)/'state.db'
            with closing(Engine(state, self.config)) as engine:
                first = invoke(engine, 'verdugo_product_run', {'request': request, 'execute': True})
                self.assertEqual('succeeded', first['state'], json.dumps(first))
                self.assertEqual(9, first['new_observations']); self.assertEqual(9, len(remote['calls']))
                self.assertEqual(10, engine.db.execute('SELECT count(*) FROM runs').fetchone()[0])
                stored = json.dumps([tuple(r) for r in engine.db.execute('SELECT * FROM runs')])
                for private in (PRIVATE, TOKEN): self.assertNotIn(private, stored)
            with closing(Engine(state, self.config)) as engine:
                again = product.observe(engine, request, True)
                self.assertEqual(9, again['reused_observations']); self.assertEqual(9, len(remote['calls']))
                self.assertEqual(first['services'][0]['evidence']['observed_at'], again['services'][0]['evidence']['observed_at'])

    def test_one_blocked_provider_prevents_all_requests(self):
        self.config['tenants']['nexus']['services']['killbill']['proxy_tenant_binding_reviewed'] = False
        with wire(self.config) as remote, closing(Engine(':memory:', self.config)) as engine:
            r = product.observe(engine, {'id': 'blocked', 'services': list(batch.SPECS), 'dataset': 'demo', 'currency': 'MXN'}, True)
            self.assertEqual('blocked', r['state']); self.assertEqual([], remote['calls'])

    def test_redirect_status_and_malformed_response_are_not_success(self):
        with wire(self.config) as remote, closing(Engine(':memory:', self.config)) as engine:
            for status in (202, 302, 401, 429, 500):
                remote['status'] = status
                self.assertEqual('failed', engine.execute(command('jitsu', 'status-'+str(status)), True)['state'])
            remote.update(status=200, raw=b'not-json '+PRIVATE.encode())
            r = engine.execute(command('jitsu', 'malformed'), True)
            self.assertEqual('failed', r['state']); self.assertNotIn(PRIVATE, json.dumps(r))
            self.assertEqual(6, len(remote['calls']))


def contract_case(sid):
    def test(self):
        cfg = self.config['tenants']['nexus']['services'][sid]
        request = build(sid, command(sid)['operation'], {}, cfg)
        self.assertEqual('GET', request['public']['method']); self.assertIsNone(request['public']['body'])
        self.assertEqual('https://example.invalid'+PATHS[sid], request['public']['url'])
        self.assertFalse(request['mutates']); self.assertNotIn(TOKEN, json.dumps(request['public']))
        result = check(sid, command(sid)['operation'], REPLIES[sid])
        for key, value in EXPECTED[sid].items(): self.assertEqual(value, result[key])
        for secret in (PRIVATE, TOKEN): self.assertNotIn(secret, json.dumps(result))
        for params in ({'page': 2}, {'page': True}, {'url': 'https://evil.invalid'}, {'query': 'arbitrary'}, {'tenant': 'other'}, {'method': 'POST'}, {'user_id': 'other'}):
            with self.assertRaises(VerdugoError): build(sid, command(sid)['operation'], params, cfg)
        with self.assertRaises(VerdugoError): build(sid, 'unsupported', {}, cfg)
    return test


for _sid in batch.SPECS:
    setattr(PlatformContracts, 'test_contract_'+_sid.replace('-', '_'), contract_case(_sid))
