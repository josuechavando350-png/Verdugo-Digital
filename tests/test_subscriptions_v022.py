from pathlib import Path
from datetime import date, timedelta
import json
import subprocess
import sys
from unittest.mock import patch

from test_core import Base, ROOT
from verdugo import subscriptions
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.mcp import invoke, tool_definitions
from verdugo import product

DAY = date(2026, 11, 16)


class ClientSwitchTests(Base):
    def client(self, role='operator'):
        return Engine(self.path, self.config, tenant='other', role=role, transport=self.transport)

    def registered(self, grace=0):
        e = self.client()
        subscriptions.register(e, 'Cliente de prueba', grace, execute=True)
        return e

    def test_operator_tenant_without_switch_is_never_turned_off(self):
        state = subscriptions.state(self.engine, DAY)
        self.assertEqual('unmanaged', state['state']); self.assertTrue(state['active'])
        self.assertEqual('succeeded', self.engine.execute(self.command(key='own-1'), True)['state'])

    def test_registered_client_starts_off_and_blocks_every_service(self):
        e = self.registered()
        try:
            self.assertEqual('sin_pago', subscriptions.state(e)['reason'])
            with self.assertRaisesRegex(VerdugoError, 'Servicio apagado'):
                e.execute(self.command(key='blocked-1'), True)
            with self.assertRaisesRegex(VerdugoError, 'Servicio apagado'):
                e.plan(self.command(key='blocked-2'))
            self.assertEqual([], self.calls)
        finally: e.close()

    def test_payment_turns_service_on_until_date_then_off(self):
        e = self.registered()
        try:
            with patch.object(subscriptions, 'today', return_value=DAY):
                result = subscriptions.pay(e, months=1, execute=True)
                self.assertEqual('2026-12-16', result['subscription']['paid_until'])
                self.assertEqual('succeeded', e.execute(self.command(key='paid-1'), True)['state'])
            with patch.object(subscriptions, 'today', return_value=date(2026, 12, 16)):
                self.assertTrue(subscriptions.state(e)['active'])
            with patch.object(subscriptions, 'today', return_value=date(2026, 12, 17)):
                self.assertEqual('pago_vencido', subscriptions.state(e)['reason'])
                with self.assertRaisesRegex(VerdugoError, 'pago_vencido'):
                    e.execute(self.command(key='late-1'), True)
                # A saved run is not replayed for a client whose service is off.
                with self.assertRaisesRegex(VerdugoError, 'Servicio apagado'):
                    e.execute(self.command(key='paid-1'), True)
        finally: e.close()

    def test_grace_days_extend_service(self):
        e = self.registered(grace=3)
        try:
            with patch.object(subscriptions, 'today', return_value=DAY):
                subscriptions.pay(e, until='2026-11-20', execute=True)
            self.assertTrue(subscriptions.state(e, date(2026, 11, 23))['active'])
            self.assertFalse(subscriptions.state(e, date(2026, 11, 24))['active'])
        finally: e.close()

    def test_months_extend_from_current_paid_date_not_today(self):
        e = self.registered()
        try:
            with patch.object(subscriptions, 'today', return_value=DAY):
                subscriptions.pay(e, until='2026-12-10', execute=True)
                self.assertEqual('2027-01-10', subscriptions.pay(e, months=1, execute=True)['change']['paid_until'])
        finally: e.close()

    def test_month_addition_clamps_to_month_end(self):
        self.assertEqual(date(2027, 2, 28), subscriptions.add_months(date(2027, 1, 31), 1))
        self.assertEqual(date(2028, 2, 29), subscriptions.add_months(date(2028, 1, 31), 1))
        with self.assertRaises(VerdugoError): subscriptions.add_months(DAY, 0)

    def test_pause_and_resume(self):
        e = self.registered()
        try:
            subscriptions.pay(e, months=2, execute=True)
            subscriptions.pause(e, 'Acuerdo con el cliente', execute=True)
            self.assertEqual('pausado', subscriptions.state(e)['reason'])
            with self.assertRaises(VerdugoError): e.execute(self.command(key='paused-1'), True)
            subscriptions.resume(e, execute=True)
            self.assertTrue(subscriptions.state(e)['active'])
        finally: e.close()

    def test_preview_changes_nothing_and_only_operator_applies(self):
        e = self.registered()
        try:
            self.assertEqual('planned', subscriptions.pay(e, months=1)['state'])
            self.assertEqual('sin_pago', subscriptions.state(e)['reason'])
        finally: e.close()
        for role in ('viewer', 'approver'):
            v = self.client(role)
            try:
                with self.assertRaisesRegex(VerdugoError, 'Operator role'):
                    subscriptions.pay(v, months=1, execute=True)
                with self.assertRaisesRegex(VerdugoError, 'Operator role'):
                    subscriptions.resume(v, execute=True)
            finally: v.close()

    def test_rejects_bad_dates_and_double_registration(self):
        e = self.registered()
        try:
            for bad in ('2020-01-01', '16/11/2026', '2030-01-01'):
                with self.assertRaises(VerdugoError): subscriptions.pay(e, until=bad, execute=True)
            with self.assertRaises(VerdugoError): subscriptions.pay(e, until='2026-12-01', months=1)
            with self.assertRaises(VerdugoError): subscriptions.register(e, 'Otra vez', execute=True)
        finally: e.close()
        fresh = Engine(self.path, self.config, tenant='nexus', transport=self.transport)
        try:
            with self.assertRaises(VerdugoError): subscriptions.register(fresh, 'x', 99)
        finally: fresh.close()

    def test_changes_are_audited_and_tenant_scoped(self):
        e = self.registered()
        try:
            subscriptions.pay(e, months=1, execute=True)
            kinds = [x['kind'] for x in e.events()]
            self.assertIn('subscription.registered', kinds); self.assertIn('subscription.paid', kinds)
            paid = [x for x in e.events() if x['kind'] == 'subscription.paid'][0]
            self.assertEqual('operator_declared', paid['details']['verification'])
        finally: e.close()
        self.assertNotIn('subscription.paid', [x['kind'] for x in self.engine.events()])
        self.assertEqual('unmanaged', subscriptions.state(self.engine)['state'])
        listing = subscriptions.listing(self.engine)
        self.assertEqual(['other'], [c['tenant'] for c in listing['clients']])

    def test_product_status_and_read_only_mcp_tool(self):
        e = self.registered()
        try:
            self.assertEqual('suspended', product.overview(e)['subscription']['state'])
            self.assertEqual('sin_pago', invoke(e, 'verdugo_client_status', {})['reason'])
        finally: e.close()
        tool = [t for t in tool_definitions() if t['name'] == 'verdugo_client_status'][0]
        self.assertTrue(tool['annotations']['readOnlyHint'])
        self.assertEqual({}, tool['inputSchema']['properties'])
        names = {t['name'] for t in tool_definitions()}
        self.assertFalse(any(n.startswith('verdugo_client_') and n != 'verdugo_client_status' for n in names))

    def test_cli_tenant_add_and_switch_round_trip(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.chmod(d, 0o700)
            cfg, state = os.path.join(d, 'c.json'), os.path.join(d, 's.db')
            run = lambda *a: subprocess.run([sys.executable, '-m', 'verdugo', '--config', cfg, '--state', state, *a],
                                            cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, subprocess.run([sys.executable, '-m', 'verdugo', 'init', '--out', cfg], cwd=ROOT,
                                               capture_output=True).returncode)
            self.assertEqual('planned', json.loads(run('tenant-add', 'cliente-a').stdout)['state'])
            self.assertEqual('applied', json.loads(run('tenant-add', 'cliente-a', '--execute').stdout)['state'])
            config = json.loads(Path(cfg).read_text())
            self.assertFalse(any(s['enabled'] for s in config['tenants']['cliente-a']['services'].values()))
            run('--tenant', 'cliente-a', 'client-register', '--label', 'Cliente A', '--execute')
            self.assertEqual('suspended', json.loads(run('--tenant', 'cliente-a', 'client-status').stdout)['state'])
            out = json.loads(run('--tenant', 'cliente-a', 'client-pay', '--months', '1', '--execute').stdout)
            self.assertTrue(out['subscription']['active'])
            self.assertEqual(1, json.loads(run('client-list').stdout)['active'])
