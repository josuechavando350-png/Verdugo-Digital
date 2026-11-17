import contextlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from verdugo import ads, commercial, mcp, office, product, subscriptions, tenants
from verdugo.__main__ import main
from verdugo.common import VerdugoError
from verdugo.engine import Engine

CSV = b'Day,Campaign,Cost,Clicks,Impressions,Conversions\n2026-11-01,synthetic-private-campaign,25,4,40,2\n'
LEAD = dict(lead_id='lead-demo', name='Cliente demo', email='demo@example.invalid',
            dataset='demo', channel='paid', evidence_ref='synthetic-001')


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.cfg = self.root/'config.json'; self.db = self.root/'state.sqlite'
        self.config = {'tenants': {'nexus': {'services': {}}, 'cliente-demo': {'services': {}}}}
        self.cfg.write_text(json.dumps(self.config))
        self.e = Engine(self.db, self.config, 'cliente-demo'); self.addCleanup(self.e.close)

    def test_off_switch_blocks_direct_commercial_and_mcp_paths_including_replay(self):
        office.intake(self.e, LEAD, True)
        subscriptions.register(self.e, 'Cliente demo', execute=True)
        count = len(self.e.events())
        event = dict(event_id='event-demo', lead_id='lead-demo', kind='contacted', channel='paid', evidence_ref='synthetic-002')
        calls = [lambda: office.intake(self.e, LEAD, True), lambda: office.intake(self.e, LEAD),
                 lambda: commercial.record(self.e, event, True), lambda: commercial.record(self.e, event),
                 lambda: commercial.report(self.e), lambda: commercial.next_actions(self.e),
                 lambda: office.desk(self.e)]
        for name, args in [('verdugo_sales_intake', {'request': LEAD, 'execute': True}),
                           ('verdugo_sales_desk', {}), ('verdugo_commercial_report', {}),
                           ('verdugo_commercial_next', {}), ('verdugo_commercial_record', {'event': event, 'execute': True})]:
            calls.append(lambda name=name, args=args: mcp.invoke(self.e, name, args))
        for call in calls:
            with self.assertRaisesRegex(VerdugoError, 'apagado'): call()
        self.assertEqual(len(self.e.events()), count)
        # Administrative diagnostics remain available without leaking a sales report.
        self.assertEqual(product.overview(self.e)['business']['state'], 'blocked')
        subscriptions.pay(self.e, months=1, execute=True)
        self.assertTrue(office.intake(self.e, LEAD, True)['replayed'])
        self.assertEqual(commercial.record(self.e, event, True)['state'], 'recorded')

    def test_cli_cannot_bypass_subscription(self):
        subscriptions.register(self.e, 'Cliente demo', execute=True)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
            code = main(['--config', str(self.cfg), '--state', str(self.db), '--tenant', 'cliente-demo', 'sales-intake', json.dumps(LEAD), '--execute'])
        self.assertEqual(code, 2); self.assertIn('apagado', errors.getvalue())
        self.assertIsNone(self.e.record('lead', 'lead-demo'))

    def test_tenant_add_requires_operator_and_preview_does_not_write(self):
        before = self.cfg.read_bytes()
        for role in ('viewer', 'approver'):
            with self.assertRaisesRegex(VerdugoError, 'Operator role'): tenants.add(self.cfg, 'cliente-nuevo', role, True)
        self.assertEqual(tenants.add(self.cfg, 'cliente-nuevo')['state'], 'planned')
        self.assertEqual(self.cfg.read_bytes(), before)
        self.assertFalse(self.cfg.with_suffix('.json.lock').exists())

    def test_new_tenant_stays_off_until_registered_and_paid(self):
        tenants.add(self.cfg, 'cliente-nuevo', execute=True)
        cfg = json.loads(self.cfg.read_text())
        self.assertEqual(self.cfg.stat().st_mode & 0o777, 0o600)
        self.assertFalse(any(s['enabled'] for s in cfg['tenants']['cliente-nuevo']['services'].values()))
        with contextlib.closing(Engine(self.db, cfg, 'cliente-nuevo')) as e:
            self.assertEqual(subscriptions.state(e)['reason'], 'registro_pendiente')
            with self.assertRaises(VerdugoError): office.intake(e, LEAD, True)
            subscriptions.register(e, 'Cliente demo', execute=True)
            self.assertFalse(subscriptions.state(e)['active'])
            subscriptions.pay(e, months=1, execute=True)
            self.assertTrue(subscriptions.state(e)['active'])

    def test_parallel_additions_preserve_existing_configuration(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda name: tenants.add(self.cfg, name, execute=True), ['cliente-uno', 'cliente-dos']))
        self.assertEqual(set(json.loads(self.cfg.read_text())['tenants']), {'nexus', 'cliente-demo', 'cliente-uno', 'cliente-dos'})
        with self.assertRaisesRegex(VerdugoError, 'exists'): tenants.add(self.cfg, 'cliente-uno', execute=True)

    def test_tenant_config_symlink_is_rejected_without_changing_target(self):
        link = self.root/'linked.json'; link.symlink_to(self.cfg)
        before = self.cfg.read_bytes()
        with self.assertRaises(VerdugoError): tenants.add(link, 'cliente-nuevo', execute=True)
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_ad_preview_is_bound_to_content_tenant_and_dataset(self):
        preview = ads.import_bytes(self.e, CSV, 'google', dataset='demo')
        self.assertEqual(preview['totals']['spend'], 25)
        self.assertEqual(self.e.db.execute('SELECT COUNT(*) FROM ads_daily').fetchone()[0], 0)
        fingerprint = preview['preview_fingerprint']
        for raw, dataset in [(CSV.replace(b',25,', b',99,'), 'demo'), (CSV, 'real')]:
            with self.assertRaisesRegex(VerdugoError, 'vista previa'):
                ads.import_bytes(self.e, raw, 'google', True, dataset, expected_fingerprint=fingerprint)
        result = ads.import_bytes(self.e, CSV, 'google', True, 'demo', expected_fingerprint=fingerprint)
        self.assertEqual(result['changed'], 1)
        self.assertTrue(ads.import_bytes(self.e, CSV, 'google', True, 'demo', expected_fingerprint=fingerprint)['replayed'])
        dump = '\n'.join(self.e.db.iterdump())
        self.assertNotIn('synthetic-private-campaign', dump); self.assertNotIn('Day,Campaign', dump)
        with contextlib.closing(Engine(self.db, self.config, 'nexus')) as other:
            with self.assertRaises(VerdugoError): ads.import_bytes(other, CSV, 'google', True, 'demo', expected_fingerprint=fingerprint)

    def test_ad_bytes_preserve_role_size_and_subscription_gates(self):
        for raw in (b'', b'x'*(ads.MAX_BYTES+1)):
            with self.assertRaises(VerdugoError): ads.import_bytes(self.e, raw, 'meta')
        self.e.role = 'viewer'
        with self.assertRaises(VerdugoError): ads.import_bytes(self.e, CSV, 'google')
        self.e.role = 'operator'; subscriptions.register(self.e, 'Cliente demo', execute=True)
        with self.assertRaisesRegex(VerdugoError, 'apagado'): ads.import_bytes(self.e, CSV, 'google', True)

    def test_subscription_dates_require_exact_iso_calendar_form(self):
        subscriptions.register(self.e, 'Cliente demo', execute=True)
        for value in ('20261220', '2026-W50-5', '2026-02-30'):
            with self.assertRaises(VerdugoError): subscriptions.pay(self.e, until=value, execute=True)

    def win_request(self):
        return dict(event_id='win-demo', lead_id='lead-demo', payment_id='payment-demo',
                    dataset='demo', channel='paid', evidence_ref='synthetic-win',
                    amount_minor=120000, cost_minor=20000, currency='MXN')

    def test_win_is_atomic_idempotent_and_scoped_to_supplied_payment(self):
        office.intake(self.e, LEAD, True)
        data = self.win_request()
        self.assertEqual(office.win(self.e, data)['state'], 'planned')
        self.assertIsNone(self.e.record('payment', 'payment-demo'))
        self.assertFalse(office.win(self.e, data, True)['replayed'])
        count = len(self.e.events())
        self.assertTrue(office.win(self.e, data, True)['replayed'])
        self.assertEqual(len(self.e.events()), count)
        report = commercial.report(self.e, {'dataset':'demo'})
        self.assertEqual(report['reported_paid_clients'], 1)
        self.assertEqual(report['reported_receipts_by_currency_minor'], {'MXN':120000})
        self.assertEqual(commercial.report(self.e)['reported_paid_clients'], 0)
        with self.assertRaises(VerdugoError): office.win(self.e, data|{'amount_minor': 999}, True)
        self.assertEqual(self.e.record('payment', 'payment-demo')['amount_minor'], 120000)

    def test_rejected_win_rolls_back_payment_and_all_events(self):
        from unittest.mock import patch
        office.intake(self.e, LEAD, True)
        data = self.win_request(); count = len(self.e.events())
        for invalid in (data|{'channel':'organic'}, data|{'dataset':'real'}, data|{'lead_id':'missing'}):
            with self.assertRaises(VerdugoError): office.win(self.e, invalid, True)
            self.assertIsNone(self.e.record('payment', 'payment-demo'))
        with patch.object(self.e, 'event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError): office.win(self.e, data, True)
        self.assertIsNone(self.e.record('payment', 'payment-demo'))
        self.assertEqual(len(self.e.events()), count)
        self.assertEqual(commercial.report(self.e, {'dataset':'demo'})['reported_paid_clients'], 0)

    def test_win_rejects_suspended_client_and_viewer(self):
        office.intake(self.e, LEAD, True)
        self.e.role = 'viewer'
        with self.assertRaisesRegex(VerdugoError, 'Operator'): office.win(self.e, self.win_request(), True)
        self.e.role = 'operator'; subscriptions.register(self.e, 'Cliente demo', execute=True)
        with self.assertRaisesRegex(VerdugoError, 'apagado'): office.win(self.e, self.win_request(), True)
