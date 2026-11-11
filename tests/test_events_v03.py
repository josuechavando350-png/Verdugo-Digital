"""Synthetic acceptance tests: signed intake, durable delivery and manual recovery."""
import copy
import http.client
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from test_core import Base, SECRET
from verdugo import jobs, reconciliation
from verdugo.common import VerdugoError, encode
from verdugo.engine import Engine
from verdugo.ingress import accept, signature, IngressError, MAX_BODY, make_server
from verdugo.mcp import invoke, tool_definitions, Session
from verdugo.transport import TransportError, send
from http.server import HTTPServer, BaseHTTPRequestHandler

KEY = b'synthetic-ingress-key-not-for-production-0123456789'


class EventsBase(Base):
    def setUp(self):
        super().setUp()
        self.cfg = {'enabled': True, 'secret_env': 'VERDUGO_TEST_INGRESS', 'dataset': 'demo',
                    'handler': 'lead.capture', 'max_pending': 10, 'max_attempts': 3}
        for tenant in ('nexus', 'other'):
            self.config['tenants'][tenant]['ingress'] = {'website': copy.deepcopy(self.cfg)}
        self.cfg = self.config['tenants']['nexus']['ingress']['website']
        self.key_env = patch.dict(os.environ, {'VERDUGO_TEST_INGRESS': KEY.decode()})
        self.key_env.start()

    def tearDown(self):
        self.key_env.stop()
        super().tearDown()

    def envelope(self, eid='event-1', external='person-1'):
        return {'id': eid, 'type': 'contact.submitted', 'data': {'external_id': external,
                'first_name': 'Synthetic', 'email': 'synthetic@example.invalid'}}

    def receive(self, envelope=None, engine=None, body=None, timestamp=None, source='website', key=KEY):
        engine = engine or self.engine
        body = body if body is not None else encode(envelope or self.envelope()).encode()
        stamp = timestamp if timestamp is not None else str(int(time.time()))
        return accept(engine, source, body, stamp, signature(key, engine.tenant, source, stamp, body))

    def enqueue(self, **kwargs): return self.receive(**kwargs)['job_id']

    def approve_job(self, jid):
        spec = jobs.plan(self.engine, jid)['plan']
        a = Engine(self.path, self.config, role='approver', actor='reviewer')
        try: a.approve_many(spec['approval_batch'])
        finally: a.close()
        return spec


class IntakeTests(EventsBase):
    def test_accept_commits_inbox_job_and_audit_without_external_calls(self):
        result = self.receive()
        self.assertFalse(result['duplicate'])
        self.assertEqual('pending', jobs.get(self.engine, result['job_id'])['state'])
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM inbox').fetchone()[0])
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0])
        self.assertEqual('event.accepted', self.engine.events()[-1]['kind'])
        self.assertFalse(self.calls)

    def test_duplicate_is_idempotent(self):
        first = self.receive()
        second = self.receive()
        self.assertEqual(first['job_id'], second['job_id'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0])

    def test_conflicting_reuse_of_event_id_rejected(self):
        self.receive()
        e = self.envelope(); e['data']['first_name'] = 'Changed'
        with self.assertRaises(IngressError) as c: self.receive(e)
        self.assertEqual(409, c.exception.status)

    def test_tampered_signature_and_body_rejected(self):
        body = encode(self.envelope()).encode(); ts = str(int(time.time()))
        good = signature(KEY, 'nexus', 'website', ts, body)
        for payload, sig in ((body+b' ', good), (body, 'sha256='+'0'*64), (body, 'x'), (body, 'é')):
            with self.subTest(sig=sig), self.assertRaises(IngressError) as c:
                accept(self.engine, 'website', payload, ts, sig)
            self.assertEqual(401, c.exception.status)
        self.assertEqual(0, len(jobs.overview(self.engine)['jobs']))

    def test_old_and_future_timestamps_rejected_even_when_signed(self):
        for delta in (-301, 301, -9999):
            with self.subTest(delta=delta), self.assertRaises(IngressError) as c:
                self.receive(timestamp=str(int(time.time())+delta))
            self.assertEqual(401, c.exception.status)

    def test_signature_is_bound_to_tenant_and_source(self):
        self.config['tenants']['nexus']['ingress']['partner'] = copy.deepcopy(self.cfg)
        body = encode(self.envelope()).encode(); ts = str(int(time.time()))
        other = Engine(self.path, self.config, tenant='other')
        try:
            for eng, source in ((other, 'website'), (self.engine, 'partner')):
                with self.assertRaises(IngressError):
                    accept(eng, source, body, ts, signature(KEY, 'nexus', 'website', ts, body))
        finally: other.close()

    def test_unknown_disabled_or_bad_source_fails_closed(self):
        with self.assertRaises(IngressError): self.receive(source='unknown')
        self.cfg['enabled'] = False
        with self.assertRaises(IngressError): self.receive()
        self.cfg['enabled'] = True; self.cfg['handler'] = 'shell.run'
        with self.assertRaises(IngressError): self.receive()

    def test_missing_or_short_secret_rejected(self):
        for value in ('', 'short', 'a'*31, 'a'*31+'\n'):
            with patch.dict(os.environ, {'VERDUGO_TEST_INGRESS': value}):
                with self.assertRaises(IngressError) as c: self.receive()
                self.assertEqual(503, c.exception.status)

    def test_arbitrary_environment_secret_reference_rejected(self):
        self.cfg['secret_env'] = 'HOME'
        with self.assertRaises(IngressError): self.receive()

    def test_duplicate_fields_and_nonfinite_json_rejected(self):
        bodies = [b'{"id":"a","id":"b"}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'[', b'[]']
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(IngressError): self.receive(body=body)

    def test_payload_cannot_override_route_tenant_role_or_dataset(self):
        for field in ('tenant', 'dataset', 'handler', 'role', 'workflow', 'url'):
            e = self.envelope(); e[field] = 'untrusted'
            with self.subTest(field=field), self.assertRaises(IngressError): self.receive(e)
        e = self.envelope(); e['data']['dataset'] = 'real'
        with self.assertRaises(IngressError): self.receive(e)

    def test_invalid_event_and_profile_rejected(self):
        mutations = [('id', '../path'), ('type', 'payment.received'), ('data', {}), ('data', [])]
        for field, value in mutations:
            e = self.envelope(); e[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(IngressError): self.receive(e)
        for field, value in [('external_id', ''), ('first_name', 'a\nb'), ('email', 'bad'), ('last_name', True)]:
            e = self.envelope(); e['data'][field] = value
            with self.subTest(field=field), self.assertRaises(IngressError): self.receive(e)

    def test_body_limit_enforced_before_persistence(self):
        for body in (b'', b'x'*(MAX_BODY+1)):
            with self.assertRaises(IngressError) as c: self.receive(body=body)
            self.assertEqual(413, c.exception.status)

    def test_queue_capacity_blocks_new_events_but_accepts_duplicate(self):
        self.cfg['max_pending'] = 1
        self.receive()
        self.assertTrue(self.receive()['duplicate'])
        with self.assertRaises(IngressError) as c: self.receive(self.envelope('event-2'))
        self.assertEqual(429, c.exception.status)
        jobs.work(self.engine, True)
        self.receive(self.envelope('event-2'))

    def test_inbox_and_job_insert_are_atomic_on_failure(self):
        self.engine.db.execute("CREATE TRIGGER fail_job BEFORE INSERT ON jobs BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.receive()
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM inbox').fetchone()[0])
        self.assertFalse(self.engine.events())

    def test_secret_rotation_does_not_change_business_route(self):
        jid = self.enqueue()
        self.cfg['secret_env'] = 'VERDUGO_NEW_INGRESS'
        with patch.dict(os.environ, {'VERDUGO_NEW_INGRESS': ('z'*40)}):
            self.assertTrue(self.receive(key=b'z'*40)['duplicate'])
        self.assertEqual('succeeded', jobs.work(self.engine, True)['state'])
        self.assertEqual('succeeded', jobs.get(self.engine, jid)['state'])

    def test_simultaneous_duplicate_deliveries_create_one_job(self):
        barrier = threading.Barrier(2); results = []; failures = []
        def receive_thread():
            e = Engine(self.path, self.config)
            try:
                barrier.wait(timeout=5)
                results.append(self.receive(engine=e))
            except Exception as exc: failures.append(exc)
            finally: e.close()
        ts = [threading.Thread(target=receive_thread) for _ in range(2)]
        for t in ts: t.start()
        for t in ts: t.join(timeout=10)
        self.assertFalse(failures)
        self.assertEqual([False, True], sorted(r['duplicate'] for r in results))
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0])


class DeliveryTests(EventsBase):
    def test_preview_does_not_claim_or_mutate_business_data(self):
        jid = self.enqueue()
        self.assertEqual('planned', jobs.work(self.engine)['state'])
        self.assertEqual(0, jobs.get(self.engine, jid)['attempts'])
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])

    def test_core_delivery_survives_process_reopen(self):
        jid = self.enqueue()
        e = Engine(self.path, self.config)
        try: self.assertEqual('succeeded', jobs.work(e, True)['state'])
        finally: e.close()
        self.assertEqual('succeeded', jobs.get(self.engine, jid)['state'])
        self.assertEqual('idle', jobs.work(self.engine, True)['state'])
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])

    def test_new_event_same_external_identity_does_not_duplicate_record(self):
        self.enqueue(); jobs.work(self.engine, True)
        self.enqueue(envelope=self.envelope('event-2')); jobs.work(self.engine, True)
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])
        self.assertEqual(2, jobs.overview(self.engine)['counts']['succeeded'])

    def test_changed_profile_is_blocked_not_silently_overwritten(self):
        self.enqueue(); jobs.work(self.engine, True)
        e = self.envelope('event-2'); e['data']['email'] = 'different@example.invalid'
        jid = self.enqueue(envelope=e)
        self.assertEqual('blocked', jobs.work(self.engine, True)['state'])
        self.assertEqual('blocked', jobs.get(self.engine, jid)['state'])
        self.assertNotIn('different@', self.engine.db.execute('SELECT payload FROM records').fetchone()[0])

    def test_source_route_change_cannot_reclassify_demo_as_real(self):
        self.enqueue(); self.cfg['dataset'] = 'real'
        self.assertEqual('blocked', jobs.work(self.engine, True)['state'])
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])

    def test_disabled_source_blocks_pending_delivery(self):
        self.enqueue(); self.cfg['enabled'] = False
        self.assertEqual('blocked', jobs.work(self.engine, True)['state'])
        self.assertFalse(self.calls)

    def test_bridge_waits_for_batch_approval_then_completes(self):
        self.cfg['handler'] = 'contact.bridge'; jid = self.enqueue()
        outcome = jobs.work(self.engine, True)
        self.assertEqual('blocked', outcome['state'])
        self.assertEqual('awaiting_approval', outcome['outcome']['reason'])
        self.assertFalse(self.calls)
        plan = self.approve_job(jid)
        self.assertEqual(2, len(plan['approval_batch']))
        jobs.resume(self.engine, jid)
        self.assertEqual('succeeded', jobs.work(self.engine, True)['state'])
        self.assertEqual(2, len(self.calls))
        self.assertEqual(2, self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])

    def test_pending_job_plan_does_not_claim(self):
        self.cfg['handler'] = 'contact.bridge'; jid = self.enqueue()
        self.assertEqual('planned', jobs.plan(self.engine, jid)['plan']['state'])
        self.assertEqual(0, jobs.get(self.engine, jid)['attempts'])
        self.assertFalse(self.calls)

    def test_crash_after_bridge_before_ack_does_not_repeat_writes(self):
        self.cfg['handler'] = 'contact.bridge'; jid = self.enqueue(); self.approve_job(jid)
        claim = jobs.claim(self.engine)
        self.assertEqual('succeeded', jobs.dispatch(self.engine, claim, True)['state'])
        self.engine.db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (jid,))
        self.assertEqual('succeeded', jobs.work(self.engine, True)['state'])
        self.assertEqual(2, len(self.calls))

    def test_crash_with_running_write_does_not_resend(self):
        self.cfg['handler'] = 'contact.bridge'; jid = self.enqueue(); self.approve_job(jid)
        def interrupted(req, cfg):
            self.calls.append(req)
            raise KeyboardInterrupt()
        self.engine.transport = interrupted
        with self.assertRaises(KeyboardInterrupt): jobs.work(self.engine, True)
        self.engine.db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (jid,))
        self.engine.transport = self.transport
        self.assertEqual('blocked', jobs.work(self.engine, True)['state'])
        self.assertEqual('running', jobs.get(self.engine, jid)['outcome']['reason'])
        self.assertEqual(1, len(self.calls))

    def test_stale_ack_rejected_after_lease_reclaimed(self):
        jid = self.enqueue(); old = jobs.claim(self.engine)
        self.engine.db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (jid,))
        new = jobs.claim(self.engine)
        self.assertNotEqual(old['lease'], new['lease'])
        with self.assertRaises(VerdugoError): jobs.settle(self.engine, old, 'succeeded', {})
        self.assertEqual('leased', jobs.get(self.engine, jid)['state'])
        jobs.settle(self.engine, new, 'blocked', {'reason':'fixture'})

    def test_expired_ack_is_rejected_even_without_other_worker(self):
        jid = self.enqueue(); claim = jobs.claim(self.engine)
        self.engine.db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (jid,))
        with self.assertRaises(VerdugoError): jobs.settle(self.engine, claim, 'succeeded', {})

    def test_two_workers_claim_one_job_only_once(self):
        self.enqueue(); barrier = threading.Barrier(2); claims = []; failures = []
        def task():
            e = Engine(self.path, self.config)
            try:
                barrier.wait(timeout=5); claims.append(jobs.claim(e))
            except Exception as exc: failures.append(exc)
            finally: e.close()
        threads = [threading.Thread(target=task) for _ in range(2)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        self.assertFalse(failures)
        self.assertEqual(1, sum(c is not None for c in claims))

    def test_internal_delivery_retry_uses_backoff_and_finite_budget(self):
        self.cfg['max_attempts'] = 2; jid = self.enqueue()
        with patch('verdugo.jobs.dispatch', side_effect=RuntimeError(SECRET)):
            first = jobs.work(self.engine, True)
            self.assertEqual('pending', first['state']); self.assertGreater(first['available'], time.time())
            self.assertEqual('idle', jobs.work(self.engine, True)['state'])
            self.engine.db.execute('UPDATE jobs SET available=0 WHERE id=?', (jid,))
            self.assertEqual('dead', jobs.work(self.engine, True)['state'])
        self.assertNotIn(SECRET, encode(jobs.overview(self.engine)))
        with self.assertRaises(VerdugoError): jobs.resume(self.engine, jid)

    def test_exhausted_expired_lease_becomes_dead_without_dispatch(self):
        self.cfg['max_attempts'] = 1; jid = self.enqueue(); jobs.claim(self.engine)
        self.engine.db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (jid,))
        self.assertIsNone(jobs.claim(self.engine))
        self.assertEqual('dead', jobs.get(self.engine, jid)['state'])
        self.assertFalse(self.calls)

    def test_manual_resume_cannot_touch_active_or_completed_job(self):
        jid = self.enqueue()
        with self.assertRaises(VerdugoError): jobs.resume(self.engine, jid)
        jobs.work(self.engine, True)
        with self.assertRaises(VerdugoError): jobs.resume(self.engine, jid)

    def test_queue_metadata_omits_payload_credentials_and_lease_token(self):
        self.enqueue(); claim = jobs.claim(self.engine)
        result = encode(jobs.overview(self.engine))
        for private in (claim['lease'], SECRET, KEY.decode(), 'synthetic@example.invalid', 'first_name'):
            self.assertNotIn(private, result)

    def test_tenant_isolation_for_jobs_and_records(self):
        jid = self.enqueue(); e = Engine(self.path, self.config, tenant='other')
        try:
            self.assertFalse(jobs.overview(e)['jobs'])
            with self.assertRaises(VerdugoError): jobs.get(e, jid)
            with self.assertRaises(VerdugoError): jobs.plan(e, jid)
            with self.assertRaises(VerdugoError): jobs.resume(e, jid)
            self.assertEqual('idle', jobs.work(e, True)['state'])
            other = self.enqueue(engine=e)
            self.assertNotEqual(jid, other)
        finally: e.close()

    def test_roles_cannot_receive_claim_resume_or_run(self):
        jid = self.enqueue()
        for role in ('viewer', 'approver'):
            e = Engine(self.path, self.config, role=role)
            try:
                for fn in (lambda: self.receive(engine=e), lambda: jobs.claim(e),
                           lambda: jobs.work(e, True), lambda: jobs.resume(e, jid)):
                    with self.assertRaises(VerdugoError): fn()
            finally: e.close()

    def test_argument_validation(self):
        for v in (0, 201, True, '10'):
            with self.assertRaises(VerdugoError): jobs.overview(self.engine, v)
        for v in (None, 1, 'true'):
            with self.assertRaises(VerdugoError): jobs.work(self.engine, v)
        for v in (0, 29, 3601, True):
            with self.assertRaises(VerdugoError): jobs.claim(self.engine, v)


class ReconciliationTests(EventsBase):
    def uncertain(self):
        self.cfg['handler'] = 'contact.bridge'; jid = self.enqueue(); plan = self.approve_job(jid)
        old = self.engine.transport
        def timeout(req, cfg):
            self.calls.append(req)
            raise TransportError('Synthetic timeout')
        self.engine.transport = timeout
        self.assertEqual('blocked', jobs.work(self.engine, True)['state'])
        self.engine.transport = old
        row = reconciliation.pending(self.engine)['items'][0]
        evidence = {'key': row['key'], 'fingerprint': row['fingerprint'],
                    'response': {'data': {'createPerson': {'id': 'recovered-1'}}},
                    'verified_email': 'synthetic@example.invalid', 'evidence_ref': 'fixture-review-1'}
        return jid, evidence

    def reviewer(self, evidence, tenant='nexus'):
        e = Engine(self.path, self.config, tenant=tenant, role='approver', actor='reviewer')
        try: return reconciliation.confirm(e, evidence)
        finally: e.close()

    def test_verified_human_evidence_unblocks_without_resending_first_write(self):
        jid, evidence = self.uncertain()
        result = self.reviewer(evidence)
        self.assertEqual('human_attestation', result['basis'])
        self.assertFalse(result['upstream_verified_by_code'])
        self.assertEqual(1, len(self.calls))
        jobs.resume(self.engine, jid)
        self.assertEqual('succeeded', jobs.work(self.engine, True)['state'])
        self.assertEqual(2, len(self.calls))
        alias = self.engine.db.execute("SELECT remote_id FROM identities WHERE service='twenty'").fetchone()
        self.assertEqual('recovered-1', alias[0])
        self.assertTrue(any(e['kind']=='action.reconciled_by_human' for e in self.engine.events()))

    def test_operator_and_mcp_cannot_self_attest(self):
        _, ev = self.uncertain()
        with self.assertRaises(VerdugoError): reconciliation.confirm(self.engine, ev)
        for name in ('verdugo_reconcile', 'verdugo_approve', 'verdugo_job_resume'):
            with self.assertRaises(VerdugoError): invoke(self.engine, name, {})

    def test_wrong_fingerprint_email_or_response_cannot_complete_run(self):
        _, ev = self.uncertain()
        for changes in ({'fingerprint':'0'*64}, {'verified_email':'wrong@example.invalid'},
                        {'response':{}}, {'response':{'data':{'createPerson':{'id':False}}}}, {'evidence_ref':''}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError): self.reviewer(ev|changes)
        self.assertEqual('uncertain', reconciliation.pending(self.engine)['items'][0]['state'])

    def test_attestation_is_tenant_bound(self):
        _, ev = self.uncertain()
        with self.assertRaises(VerdugoError): self.reviewer(ev, 'other')

    def test_already_reconciled_cannot_be_changed_again(self):
        _, ev = self.uncertain(); self.reviewer(ev)
        with self.assertRaises(VerdugoError): self.reviewer(ev)
        self.assertEqual(1, self.engine.db.execute('SELECT COUNT(*) FROM reconciliations').fetchone()[0])

    def test_running_run_is_not_treated_as_confirmable(self):
        _, ev = self.uncertain()
        self.engine.db.execute("UPDATE runs SET state='running' WHERE key=?", (ev['key'],))
        with self.assertRaises(VerdugoError): self.reviewer(ev)

    def test_attestation_redacts_credential_values(self):
        _, ev = self.uncertain(); ev['response']['echo'] = SECRET; ev['response']['token'] = SECRET
        self.reviewer(ev)
        row = self.engine.db.execute('SELECT result FROM runs WHERE key=?', (ev['key'],)).fetchone()
        self.assertNotIn(SECRET, row[0])

    def test_evidence_and_run_update_are_atomic(self):
        _, ev = self.uncertain()
        self.engine.db.execute("CREATE TRIGGER no_finish BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.reviewer(ev)
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM reconciliations').fetchone()[0])
        self.assertEqual('uncertain', reconciliation.pending(self.engine)['items'][0]['state'])


class InterfaceTests(EventsBase):
    def server(self):
        cfg = self.config; path = self.path
        server = make_server(lambda: Engine(path, cfg), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=5)))
        return server.server_port

    def request(self, port, body=None, extra=None, path='/v1/events/website'):
        body = body if body is not None else encode(self.envelope()).encode()
        ts = str(int(time.time()))
        headers = {'Content-Type':'application/json', 'X-Verdugo-Timestamp':ts,
                   'X-Verdugo-Signature':signature(KEY, 'nexus', 'website', ts, body)}
        headers.update(extra or {})
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        try:
            conn.request('POST', path, body=body, headers=headers)
            response = conn.getresponse(); return response.status, json.loads(response.read())
        finally: conn.close()

    def test_loopback_http_signed_delivery_persists_and_executes(self):
        port = self.server()
        status, response = self.request(port)
        self.assertEqual(202, status); self.assertFalse(response['duplicate'])
        self.assertEqual(200, self.request(port)[0])
        self.assertEqual('succeeded', jobs.work(self.engine, True)['state'])
        self.assertEqual('succeeded', jobs.get(self.engine, response['job_id'])['state'])

    def test_http_rejects_invalid_signature_route_and_encoding(self):
        port = self.server()
        for extra, path, expected in (({'X-Verdugo-Signature':'x'}, '/v1/events/website', 401),
                ({}, '/v1/events/website?x=1', 404), ({'Content-Type':'text/plain'}, '/v1/events/website', 415),
                ({'Content-Encoding':'gzip'}, '/v1/events/website', 400)):
            with self.subTest(extra=extra): self.assertEqual(expected, self.request(port, extra=extra, path=path)[0])
        self.assertFalse(jobs.overview(self.engine)['jobs'])

    def test_http_rejects_duplicate_auth_headers(self):
        port = self.server(); conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        try:
            conn.putrequest('POST','/v1/events/website')
            for k,v in [('Content-Length','2'), ('Content-Type','application/json'),
                        ('X-Verdugo-Timestamp','1'), ('X-Verdugo-Timestamp','2'), ('X-Verdugo-Signature','x')]:
                conn.putheader(k,v)
            conn.endheaders(b'{}'); response = conn.getresponse()
            self.assertEqual(400, response.status); response.read()
        finally: conn.close()

    def test_mcp_has_twelve_tools_without_approval_or_signer(self):
        names = {t['name'] for t in tool_definitions()}
        self.assertEqual(12, len(names))
        self.assertIn('verdugo_worker', names)
        self.assertFalse(any('approve' in n or 'sign' in n for n in names))
        self.enqueue()
        self.assertEqual('planned', invoke(self.engine, 'verdugo_worker', {})['state'])
        self.assertEqual(0, invoke(self.engine, 'verdugo_queue', {})['jobs'][0]['attempts'])

    def test_mcp_marks_blocked_job_as_incomplete(self):
        self.cfg['handler'] = 'contact.bridge'; self.enqueue()
        session = Session(self.engine)
        session.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}})
        session.handle({'jsonrpc':'2.0','method':'notifications/initialized'})
        result = session.handle({'jsonrpc':'2.0','id':2,'method':'tools/call',
                      'params':{'name':'verdugo_worker','arguments':{'execute':True}}})
        self.assertTrue(result['result']['isError'])

    def test_cli_worker_preview_then_execute(self):
        self.enqueue(); cfg = Path(self.tmp.name)/'config.json'; cfg.write_text(encode(self.config))
        base = [sys.executable, '-m', 'verdugo', '--config', str(cfg), '--state', str(self.path)]
        preview = subprocess.run(base+['worker'], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertEqual('planned', json.loads(preview.stdout)['state'])
        actual = subprocess.run(base+['worker','--execute'], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, actual.returncode, actual.stderr)
        self.assertEqual('succeeded', json.loads(actual.stdout)['state'])

    def test_cli_reconcile_dry_run_does_not_attest(self):
        run = subprocess.run([sys.executable, '-m', 'verdugo', '--state', str(self.path),
                            'reconcile','{}'], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, run.returncode)
        self.assertEqual('planned', json.loads(run.stdout)['state'])
        self.assertEqual(0, self.engine.db.execute('SELECT COUNT(*) FROM reconciliations').fetchone()[0])

    def test_cli_local_ingress_rejects_volatile_state(self):
        run = subprocess.run([sys.executable, '-m', 'verdugo', '--state', ':memory:', 'ingress-local'],
                            capture_output=True, text=True, timeout=10)
        self.assertEqual(2, run.returncode)

    def test_metadata_limits_validate_and_report_truncation(self):
        self.enqueue(); self.enqueue(envelope=self.envelope('event-2'))
        result = jobs.overview(self.engine, 1)
        self.assertEqual(1, len(result['jobs'])); self.assertTrue(result['truncated'])

    def test_migration_preserves_v02_records_and_approvals(self):
        from verdugo.engine import SCHEMA
        from verdugo.identity import SCHEMA as IDENTITY_SCHEMA
        path = Path(self.tmp.name)/'legacy.sqlite3'
        db = sqlite3.connect(path)
        db.executescript(SCHEMA+IDENTITY_SCHEMA)
        db.execute('INSERT INTO records VALUES(?,?,?,?,?)', ('nexus','lead','old-lead','demo',
                   encode({'lead_id':'old-lead','dataset':'demo','email':'old@example.invalid'})))
        db.execute('INSERT INTO plans(tenant,key,hash,document,approved_by,expires) VALUES(?,?,?,?,?,?)',
                   ('nexus','old-plan','old-hash','{}','human',time.time()+600))
        db.commit(); db.close()
        e = Engine(path, self.config)
        try:
            self.assertEqual('demo', e.record('lead','old-lead')['dataset'])
            row = e.db.execute('SELECT * FROM plans WHERE key=?', ('old-plan',)).fetchone()
            self.assertEqual('old-hash', row['hash']); self.assertEqual('human', row['approved_by'])
            for table in ('inbox','jobs','reconciliations'):
                self.assertEqual(0, e.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0])
        finally: e.close()

    def test_http_event_to_two_http_contacts_end_to_end(self):
        paths = []
        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                paths.append(self.path)
                self.rfile.read(int(self.headers['Content-Length']))
                body = encode({'data':{'createPerson':{'id':'wire-crm'}},
                               'payload':{'contact':{'id':89}}}).encode()
                self.send_response(201); self.send_header('Content-Length', str(len(body)))
                self.end_headers(); self.wfile.write(body)
        upstream = HTTPServer(('127.0.0.1',0), Provider)
        t = threading.Thread(target=upstream.serve_forever,daemon=True); t.start()
        self.addCleanup(upstream.server_close)
        self.addCleanup(lambda: (upstream.shutdown(),t.join(timeout=5)))
        for service in ('twenty','chatwoot'):
            self.config['tenants']['nexus']['services'][service].update(
                base_url='http://127.0.0.1:'+str(upstream.server_port), allow_local_http=True)
        self.cfg['handler'] = 'contact.bridge'; self.engine.transport = send
        port = self.server(); status, reply = self.request(port)
        self.assertEqual(202,status); jid = reply['job_id']
        self.approve_job(jid)
        self.assertEqual('succeeded',jobs.work(self.engine,True)['state'])
        self.assertEqual(['/rest/people','/api/v1/accounts/1/contacts'], paths)
        self.assertEqual(200,self.request(port)[0])
        self.assertEqual('idle',jobs.work(self.engine,True)['state'])
        self.assertEqual(2,len(paths))
        self.assertEqual(2,self.engine.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0])
