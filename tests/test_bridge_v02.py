"""Synthetic fixtures and local HTTP only; no production service is certified."""
import copy
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit, parse_qs
from unittest.mock import patch
from test_core import Base, SECRET
from verdugo.adapters import build, remote_id, SPECS
from verdugo.bridge import contact_bridge
from verdugo.common import VerdugoError
from verdugo.diagnostics import doctor
from verdugo.engine import Engine
from verdugo.mcp import invoke, tool_definitions
from verdugo.transport import send
from verdugo import workflow

PROFILE = {'lead_id': 'canonical-1', 'first_name': 'Synthetic', 'last_name': 'Contact',
           'email': 'synthetic@example.invalid', 'dataset': 'demo'}


class NewAdapterTests(Base):
    def test_frappe_lead_fields_and_offset(self):
        cfg = self.config['tenants']['nexus']['services']['frappe-crm']
        req = build('frappe-crm', 'leads.list', {'page': 3}, cfg)
        url = urlsplit(req['public']['url'])
        self.assertEqual('/api/resource/CRM%20Lead', url.path)
        query = parse_qs(url.query)
        self.assertEqual(['100'], query['limit_start'])
        self.assertEqual(['name', 'lead_name', 'email'], json.loads(query['fields'][0]))
        self.assertEqual('token '+SECRET, req['headers']['Authorization'])

    def test_erpnext_has_separate_resource_and_fields(self):
        cfg = self.config['tenants']['nexus']['services']['erpnext']
        req = build('erpnext', 'customers.list', {}, cfg)
        self.assertEqual('/api/resource/Customer', urlsplit(req['public']['url']).path)
        self.assertEqual(['name', 'customer_name'], json.loads(parse_qs(urlsplit(req['public']['url']).query)['fields'][0]))

    def test_frappe_token_format_is_validated(self):
        cfg = self.config['tenants']['nexus']['services']['erpnext']
        with patch.dict(os.environ, {cfg['token_env']: 'no-key-secret-separator'}):
            with self.assertRaises(VerdugoError): build('erpnext', 'customers.list', {}, cfg)

    def test_posthog_project_is_operator_scoped(self):
        cfg = self.config['tenants']['nexus']['services']['posthog']
        cfg['project_id'] = 41
        req = build('posthog', 'dashboards.list', {'page': 2}, cfg)
        self.assertIn('/api/projects/41/dashboards/?limit=50&offset=50', req['public']['url'])
        with self.assertRaises(VerdugoError):
            build('posthog', 'dashboards.list', {'project_id': 99}, cfg)

    def test_lago_pagination_and_bearer(self):
        cfg = self.config['tenants']['nexus']['services']['lago']
        req = build('lago', 'customers.list', {'page': 2}, cfg)
        self.assertTrue(req['public']['url'].endswith('/api/v1/customers?page=2&per_page=50'))
        self.assertEqual('Bearer '+SECRET, req['headers']['Authorization'])

    def test_langfuse_uses_basic_not_bearer(self):
        cfg = self.config['tenants']['nexus']['services']['langfuse']
        req = build('langfuse', 'projects.list', {}, cfg)
        self.assertTrue(req['headers']['Authorization'].startswith('Basic '))
        self.assertTrue(req['public']['url'].endswith('/api/public/projects'))
        self.assertNotIn(SECRET, json.dumps(req['public']))
        with self.assertRaises(VerdugoError): build('langfuse', 'projects.list', {'page': 2}, cfg)

    def test_changedetection_cannot_trigger_recheck(self):
        cfg = self.config['tenants']['nexus']['services']['changedetection']
        req = build('changedetection', 'watches.list', {}, cfg)
        self.assertEqual(SECRET, req['headers']['x-api-key'])
        self.assertTrue(req['public']['url'].endswith('/api/v1/watch'))
        with self.assertRaises(VerdugoError):
            build('changedetection', 'watches.list', {'recheck_all': '1'}, cfg)

    def test_chatwoot_auth_mode_must_be_explicit_if_legacy(self):
        cfg = self.config['tenants']['nexus']['services']['chatwoot']
        cfg['auth_mode'] = 'api_access_token'
        req = build('chatwoot', 'conversations.list', {}, cfg)
        self.assertEqual(SECRET, req['headers']['api_access_token'])
        self.assertNotIn('Authorization', req['headers'])
        cfg['auth_mode'] = 'invented'
        with self.assertRaises(VerdugoError): build('chatwoot', 'conversations.list', {}, cfg)

    def test_auth_configuration_change_invalidates_existing_plan(self):
        cmd = self.command('langfuse', 'projects.list')
        self.engine.plan(cmd)
        self.config['tenants']['nexus']['services']['langfuse']['username'] = 'another-public-key'
        with self.assertRaises(VerdugoError): self.engine.plan(cmd)

    def test_write_requires_workspace_and_result_contract(self):
        cfg = self.config['tenants']['nexus']['services']['twenty']
        del cfg['workspace_id']
        with self.assertRaises(VerdugoError): self.engine.plan(self.write())
        cfg['workspace_id'] = 'fixture'
        del cfg['result_id_path']
        with self.assertRaises(VerdugoError): self.engine.plan(self.write())

    def test_network_policy_change_invalidates_approval(self):
        self.approve(self.write())
        self.config['tenants']['nexus']['services']['twenty']['allow_private_network'] = True
        with self.assertRaises(VerdugoError): self.engine.execute(self.write(), True)
        self.assertFalse(self.calls)

    def test_whitespace_latest_is_not_a_pin(self):
        self.config['tenants']['nexus']['services']['twenty']['version'] = ' latest '
        with self.assertRaises(VerdugoError): self.engine.plan(self.command())


class ResponseContractTests(Base):
    def test_path_extracts_only_a_valid_id(self):
        self.assertEqual('43', remote_id({'payload': [{'id': 43}]}, 'payload.0.id'))
        self.assertEqual('uuid-1', remote_id({'data': {'id': 'uuid-1'}}, 'data.id'))

    def test_invalid_and_ambiguous_values_are_rejected(self):
        for value in (True, None, -1, 0, 1.5, {}, [], '', '../remote', 'a.b'):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                remote_id({'id': value}, 'id')

    def test_no_expression_execution_in_id_path(self):
        for path in ('id()', '__import__(os)', '', 'payload.-1.id', 'a..id', '.id'):
            with self.subTest(path=path), self.assertRaises(VerdugoError): remote_id({}, path)

    def test_missing_id_write_is_uncertain_and_not_retried(self):
        self.approve(self.write())
        calls = []
        def malformed(req, cfg):
            calls.append(req)
            return {'http_status': 200}
        self.engine.transport = malformed
        self.assertEqual('uncertain', self.engine.execute(self.write(), True)['state'])
        self.assertEqual('uncertain', self.engine.execute(self.write(), True)['state'])
        self.assertEqual(1, len(calls))

    def test_result_path_change_invalidates_approval(self):
        self.approve(self.write())
        self.config['tenants']['nexus']['services']['twenty']['result_id_path'] = 'data.person.id'
        with self.assertRaises(VerdugoError): self.engine.execute(self.write(), True)


class BridgeTests(Base):
    def approve_bridge(self, profile=None):
        plan = contact_bridge(self.engine, profile or PROFILE)
        approver = Engine(self.path, self.config, role='approver', actor='test-human')
        try: approver.approve_many(plan['approval_batch'])
        finally: approver.close()
        return plan

    def test_bridge_plan_is_offline_and_two_writes_one_approval_batch(self):
        plan = contact_bridge(self.engine, PROFILE)
        self.assertEqual(2, len(plan['approval_batch']))
        self.assertEqual(6, len(plan['ordered_steps']))
        self.assertFalse(self.calls)
        self.assertIsNone(self.engine.record('lead', PROFILE['lead_id']))

    def test_bridge_creates_two_linked_identities(self):
        self.approve_bridge()
        result = contact_bridge(self.engine, PROFILE, True)
        self.assertEqual('succeeded', result['state'])
        aliases = result['steps']['summary']['aliases']
        self.assertEqual({'chatwoot': '42', 'twenty': 'fixture'},
                         {a['service']: a['remote_id'] for a in aliases})
        self.assertEqual(2, len(self.calls))
        self.assertFalse(result['steps']['summary']['bidirectional_sync'])

    def test_bridge_restart_does_not_repeat_creation(self):
        self.approve_bridge()
        contact_bridge(self.engine, PROFILE, True)
        engine = Engine(self.path, self.config, transport=self.transport)
        try: self.assertEqual('succeeded', contact_bridge(engine, PROFILE, True)['state'])
        finally: engine.close()
        self.assertEqual(2, len(self.calls))
        self.assertEqual(2, self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])

    def test_changed_profile_cannot_reuse_canonical_workflow(self):
        self.approve_bridge()
        altered = PROFILE | {'email': 'changed@example.invalid'}
        with self.assertRaises(VerdugoError): contact_bridge(self.engine, altered, True)
        self.assertFalse(self.calls)

    def test_bridge_pauses_before_remote_write_without_approval(self):
        result = contact_bridge(self.engine, PROFILE, True)
        self.assertEqual('paused', result['state'])
        self.assertEqual('awaiting_approval', result['outcome']['state'])
        self.assertFalse(self.calls)

    def test_bridge_second_failure_never_duplicates_first_write(self):
        self.approve_bridge()
        calls = []
        def partial(req, cfg):
            calls.append(req['public']['service'])
            if req['public']['service'] == 'chatwoot': raise VerdugoError('Synthetic timeout')
            return {'data': {'createPerson': {'id': 'crm-1'}}}
        self.engine.transport = partial
        first = contact_bridge(self.engine, PROFILE, True)
        second = contact_bridge(self.engine, PROFILE, True)
        self.assertEqual('uncertain', first['outcome']['state'])
        self.assertEqual('uncertain', second['outcome']['state'])
        self.assertEqual(['twenty', 'chatwoot'], calls)
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])

    def test_identity_read_requires_tenant_and_dataset_match(self):
        self.approve_bridge(); contact_bridge(self.engine, PROFILE, True)
        cmd = self.command('core', 'identity.summary',
                           {'lead_id': PROFILE['lead_id'], 'dataset': 'real'}, 'wrong-dataset')
        self.assertEqual('failed', self.engine.execute(cmd, True)['state'])
        engine = Engine(self.path, self.config, tenant='other')
        try:
            cmd['params']['dataset'] = 'demo'
            self.assertEqual('failed', engine.execute(cmd, True)['state'])
        finally: engine.close()

    def test_identity_cannot_bind_an_unexecuted_or_read_only_source(self):
        self.engine.execute(self.lead(), True)
        for source in ('missing', 'read'):
            if source == 'read': self.engine.execute(self.command(key='read'), True)
            cmd = self.command('core', 'identity.bind', {'lead_id': 'lead-1', 'dataset': 'demo',
                'service': 'twenty', 'source_key': source}, 'bind-'+source)
            self.assertEqual('failed', self.engine.execute(cmd, True)['state'])

    def test_identity_cannot_bind_different_email(self):
        self.engine.execute(self.lead(), True)
        create = self.write(); create['params']['email'] = 'another@example.invalid'
        self.approve(create); self.engine.execute(create, True)
        cmd = self.command('core', 'identity.bind', {'lead_id': 'lead-1', 'dataset': 'demo',
            'service': 'twenty', 'source_key': 'write-1'}, 'bad-bind')
        self.assertEqual('failed', self.engine.execute(cmd, True)['state'])

    def test_one_remote_identity_cannot_alias_two_leads(self):
        self.approve_bridge(); contact_bridge(self.engine, PROFILE, True)
        other = PROFILE | {'lead_id': 'another-lead'}
        self.approve_bridge(other)
        result = contact_bridge(self.engine, other, True)
        self.assertEqual('paused', result['state'])
        self.assertEqual('crm-link', result['step'])
        self.assertEqual(2, self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])

    def test_both_workflows_and_bridge_share_engine_tools(self):
        names = {t['name'] for t in tool_definitions()}
        self.assertIn('verdugo_bridge', names); self.assertIn('verdugo_doctor', names)
        self.assertFalse(any('approve' in n for n in names))
        plan = invoke(self.engine, 'verdugo_bridge', {'profile': PROFILE})
        self.assertEqual(2, len(plan['approval_batch']))
        with self.assertRaises(VerdugoError):
            invoke(self.engine, 'verdugo_bridge', {'profile': PROFILE, 'tenant': 'other'})

    def test_real_loopback_bridge_then_resume(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append((self.path, body))
                result = ({'data': {'createPerson': {'id': 'wire-person'}}}
                          if self.path == '/rest/people' else {'payload': {'contact': {'id': 57}}})
                self.send_response(201); self.send_header('Content-Type', 'application/json')
                self.end_headers(); self.wfile.write(json.dumps(result).encode())
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            for sid in ('twenty', 'chatwoot'):
                self.config['tenants']['nexus']['services'][sid].update(
                    base_url='http://127.0.0.1:'+str(server.server_port), allow_local_http=True)
            self.engine.transport = send
            self.approve_bridge()
            self.assertEqual('succeeded', contact_bridge(self.engine, PROFILE, True)['state'])
            self.assertEqual('succeeded', contact_bridge(self.engine, PROFILE, True)['state'])
            self.assertEqual(['/rest/people', '/api/v1/accounts/1/contacts'], [p for p, _ in received])
        finally:
            server.shutdown(); server.server_close(); thread.join(2)


class WorkflowManifestTests(Base):
    def test_same_workflow_id_cannot_change_steps_after_preview(self):
        spec = {'id': 'immutable', 'steps': [{'id': 'first', 'service': 'twenty',
                'operation': 'people.list', 'params': {}}]}
        workflow.run(self.engine, spec)
        spec['steps'].append({'id': 'extra', 'service': 'core',
            'operation': 'lead.capture', 'params': self.lead()['params']})
        with self.assertRaises(VerdugoError): workflow.run(self.engine, spec, True)
        self.assertFalse(self.calls)

    def test_dependent_credentials_checked_before_any_business_effect(self):
        spec = {'id': 'preflight', 'steps': [
            {'id': 'capture', 'service': 'core', 'operation': 'lead.capture', 'params': self.lead()['params']},
            {'id': 'crm', 'service': 'twenty', 'operation': 'people.create', 'depends_on': ['capture'],
             'params': {'first_name': {'$ref': 'capture.lead_id'}, 'email': 'demo@example.invalid'}}]}
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(VerdugoError): workflow.run(self.engine, spec, True)
        self.assertIsNone(self.engine.record('lead', 'lead-1'))


class DoctorTests(Base):
    def test_configuration_checks_never_call_network(self):
        result = doctor(self.engine)
        self.assertEqual(322, len(result['checks']))
        self.assertEqual(58, sum(r['state'] == 'planned' for r in result['checks']))
        self.assertFalse(self.calls)

    def test_bounded_doctor_checks_every_enabled_adapter_once(self):
        result = doctor(self.engine, 'probe-1', True)
        self.assertEqual(58, len(self.calls))
        self.assertTrue(all(r['method'] == 'GET' or (r['service'],r['operation']) in {('plausible','traffic.summary'),('matomo','visits.summary'),('saleor','products.list')} for r in self.calls))
        self.assertEqual(0, result['live_verified'])
        self.assertFalse(any(r['live_verified'] for r in result['checks']))
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertNotIn('createPerson', json.dumps(result))

    def test_read_failures_do_not_hide_other_diagnostics(self):
        def sometimes(req, cfg):
            if req['public']['service'] == 'lago': raise VerdugoError('Synthetic unavailable')
            return {'items': []}
        self.engine.transport = sometimes
        result = doctor(self.engine, 'partial', True)
        rows = {r['service']: r for r in result['checks']}
        self.assertEqual('failed', rows['lago']['state'])
        self.assertEqual('read_succeeded', rows['twenty']['state'])

    def test_fresh_probe_requires_new_identifier(self):
        doctor(self.engine, 'one', True); doctor(self.engine, 'one', True)
        self.assertEqual(58, len(self.calls))
        doctor(self.engine, 'two', True)
        self.assertEqual(116, len(self.calls))

    def test_missing_credentials_report_blocked_without_network(self):
        with patch.dict(os.environ, {}, clear=True): result = doctor(self.engine, 'missing', True)
        self.assertFalse(self.calls)
        self.assertEqual(58, sum(r['state'] == 'blocked' for r in result['checks']))

    def test_viewer_cannot_trigger_remote_probes(self):
        engine = Engine(self.path, self.config, role='viewer', transport=self.transport)
        try:
            with self.assertRaises(VerdugoError): doctor(engine, 'view', True)
            doctor(engine, 'view', False)
        finally: engine.close()
        self.assertFalse(self.calls)

    def test_doctor_mcp_cannot_override_tenant_or_inject_urls(self):
        with self.assertRaises(VerdugoError):
            invoke(self.engine, 'verdugo_doctor', {'probe_id': 'test', 'url': 'https://example.invalid'})
        self.assertEqual('configuration-only', invoke(self.engine, 'verdugo_doctor', {'probe_id': 'test'})['mode'])

    def test_probe_and_boolean_types_are_strict(self):
        for args in (('x'*41, False), ('okay', 'yes'), ('../bad', False)):
            with self.subTest(args=args), self.assertRaises(VerdugoError): doctor(self.engine, *args)

class OperationalTruthTests(Base):
    def test_empty_doctor_does_not_say_connected(self):
        for cfg in self.config['tenants']['nexus']['services'].values(): cfg['enabled'] = False
        result = doctor(self.engine, 'empty', True)
        self.assertEqual('not_configured', result['state'])
        self.assertEqual({'disabled': 322}, result['counts'])
        self.assertFalse(self.calls)

    def test_nonzero_cli_exit_for_unconfigured_live_diagnostics(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-m', 'verdugo', '--state', ':memory:',
                                 'doctor', '--execute'], capture_output=True, text=True, timeout=10)
        self.assertEqual(1, result.returncode)
        self.assertEqual('not_configured', json.loads(result.stdout)['state'])

    def test_mcp_does_not_label_paused_execution_as_success(self):
        from verdugo.mcp import Session
        session = Session(self.engine)
        session.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                        'params': {'protocolVersion': '2025-11-25'}})
        session.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        result = session.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'verdugo_bridge', 'arguments': {'profile': PROFILE, 'execute': True}}})
        self.assertTrue(result['result']['isError'])
        self.assertEqual('paused', json.loads(result['result']['content'][0]['text'])['state'])

    def test_profile_types_are_not_coerced(self):
        for value in (None, False, 0, [], {}):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                contact_bridge(self.engine, PROFILE | {'last_name': value})

    def test_uncertain_first_write_does_not_reach_second_service(self):
        plan = contact_bridge(self.engine, PROFILE)
        approver = Engine(self.path, self.config, role='approver')
        try: approver.approve_many(plan['approval_batch'])
        finally: approver.close()
        calls = []
        def no_id(req, cfg): calls.append(req); return {'acknowledged': True}
        self.engine.transport = no_id
        result = contact_bridge(self.engine, PROFILE, True)
        self.assertEqual('crm', result['step'])
        self.assertEqual('uncertain', result['outcome']['state'])
        self.assertEqual(1, len(calls))
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])

    def test_async_202_is_not_treated_as_completed_write(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(202); self.end_headers()
                self.wfile.write(b'{"data":{"createPerson":{"id":"held-not-created"}}}')
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            self.config['tenants']['nexus']['services']['twenty'].update(
                base_url='http://127.0.0.1:'+str(server.server_port), allow_local_http=True)
            self.engine.transport = send
            self.approve(self.write())
            self.assertEqual('uncertain', self.engine.execute(self.write(), True)['state'])
        finally: server.shutdown(); server.server_close(); thread.join(2)

    def test_upgrade_keeps_existing_records_and_runs(self):
        self.engine.execute(self.lead(), True)
        self.engine.execute(self.pay(), True)
        self.engine.db.execute('DROP TABLE identities')
        engine = Engine(self.path, self.config)
        try:
            self.assertEqual('lead-1', engine.record('lead', 'lead-1')['lead_id'])
            self.assertTrue(engine.execute(self.pay(), True)['replayed'])
            self.assertEqual(0, engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])
        finally: engine.close()
