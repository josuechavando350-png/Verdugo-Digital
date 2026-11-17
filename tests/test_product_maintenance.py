"""Recover actual commercial state offline; fail closed on uncertainty or damaged copies."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from verdugo import ads, commercial, maintenance, office, subscriptions
from verdugo.common import VerdugoError
from verdugo.engine import Engine


class ProductMaintenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = self.root/'config.json'
        self.config = {'tenants': {'cliente-demo': {'services': {'plausible': {'enabled': True}},
                        'ingress': {'web': {'enabled': True}}}, 'otro-demo': {'services': {}}}}
        self.cfg.write_text(json.dumps(self.config)); self.cfg.chmod(0o600)
        self.engine = Engine(self.root/'state.sqlite3', self.config, 'cliente-demo')
        self.addCleanup(self.engine.close)
        self.assets = self.root/'assets'; self.assets.mkdir(); (self.assets/'index.html').write_text('demo')

    def backup(self): return maintenance.create_set(self.engine, self.cfg)

    def test_restore_keeps_clients_payments_ads_sales_and_scoping_after_restart(self):
        subscriptions.register(self.engine, 'Cliente demo', execute=True)
        subscriptions.pay(self.engine, months=1, execute=True)
        office.intake(self.engine, {'lead_id':'lead-demo','name':'Cliente demo','email':'demo@example.invalid',
            'dataset':'demo','channel':'paid','evidence_ref':'synthetic-intake'}, True)
        office.win(self.engine, {'event_id':'sale-demo','lead_id':'lead-demo','payment_id':'payment-demo',
            'dataset':'demo','channel':'paid','evidence_ref':'synthetic-sale','amount_minor':120025,
            'cost_minor':20000,'currency':'MXN'}, True)
        ads.import_bytes(self.engine, b'Day,Campaign,Cost,Clicks,Impressions,Conversions\n2026-11-16,demo,250,20,100,4\n', 'google', True, 'demo')
        expected = commercial.report(self.engine, {'dataset':'demo'})
        saved = self.backup(); target = self.root/'recovered'
        self.assertTrue(saved['restore_allowed'])
        self.assertEqual(maintenance.restore_set(saved['saved_directory'], target)['state'], 'planned')
        self.assertFalse(target.exists())
        result = maintenance.restore_set(saved['saved_directory'], target, execute=True)
        self.assertFalse(result['external_calls_made']); self.assertFalse(result['tokens_copied'])
        restored = json.loads((target/'config.json').read_text())
        self.assertFalse(restored['tenants']['cliente-demo']['services']['plausible']['enabled'])
        self.assertFalse(restored['tenants']['cliente-demo']['ingress']['web']['enabled'])
        for _ in range(2):
            with closing(Engine(target/'estado.sqlite', restored, 'cliente-demo')) as e:
                self.assertTrue(subscriptions.state(e)['active'])
                self.assertEqual(commercial.report(e, {'dataset':'demo'}), expected)
                self.assertEqual(ads.report(e, {'dataset':'demo','start_date':'2026-11-01','end_date':'2026-11-30'})['totals']['spend'], 250)
                self.assertEqual(e.record('payment', 'payment-demo')['amount_minor'], 120025)
            with closing(Engine(target/'estado.sqlite', restored, 'otro-demo')) as e:
                self.assertEqual(commercial.report(e, {'dataset':'demo'})['reported_paid_clients'], 0)
        self.assertEqual((target/'config.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertTrue(self.config['tenants']['cliente-demo']['services']['plausible']['enabled'])

    def test_approval_is_not_carried_forward(self):
        self.engine.db.execute("INSERT INTO plans VALUES ('cliente-demo','demo','hash','{}','approver',9999999999,0)")
        saved = self.backup(); target = self.root/'recovered'
        maintenance.restore_set(saved['saved_directory'], target, execute=True)
        with closing(sqlite3.connect(target/'estado.sqlite')) as db:
            self.assertEqual(db.execute('SELECT approved_by,expires FROM plans').fetchone(), (None,None))
        self.assertEqual(self.engine.db.execute('SELECT approved_by FROM plans').fetchone()[0], 'approver')

    def test_uncertain_and_running_work_block_restore_without_creating_target(self):
        for state in ('uncertain','running'):
            self.engine.db.execute("INSERT OR REPLACE INTO runs VALUES ('cliente-demo','demo','hash',?,NULL,0,NULL)", (state,))
            saved = self.backup(); self.assertFalse(saved['restore_allowed'])
            with self.assertRaises(VerdugoError): maintenance.restore_set(saved['saved_directory'], self.root/'recovered', execute=True)
            self.assertFalse((self.root/'recovered').exists())

    def test_all_unfinished_jobs_block_restore_including_other_tenants(self):
        for state in ('pending','leased','blocked','dead'):
            self.engine.db.execute("INSERT OR REPLACE INTO jobs VALUES ('otro-demo','job-demo','demo','hash','lead.capture','{}',?,0,3,0,NULL,NULL,NULL,0,0)", (state,))
            saved = self.backup(); self.assertEqual(saved['unfinished_jobs'], 1)
            with self.assertRaises(VerdugoError): maintenance.restore_set(saved['saved_directory'], self.root/'recovered', execute=True)

    def test_modified_config_or_database_and_extra_files_are_rejected(self):
        for name in ('config.json','estado.sqlite3'):
            saved = Path(self.backup()['saved_directory']); path = saved/name
            path.write_bytes(path.read_bytes()+b'corruption')
            with self.assertRaises(VerdugoError): maintenance.verify_set(saved)
        saved = Path(self.backup()['saved_directory']); (saved/'unexpected').touch()
        with self.assertRaises(VerdugoError): maintenance.verify_set(saved)

    def test_private_permissions_links_and_changed_config_fail_closed(self):
        self.cfg.chmod(0o644)
        with self.assertRaises(VerdugoError): self.backup()
        self.cfg.chmod(0o600)
        self.cfg.write_text(json.dumps({'tenants':{'other':{'services':{}}}}))
        with self.assertRaises(VerdugoError): self.backup()
        self.cfg.write_text(json.dumps(self.config))
        saved = Path(self.backup()['saved_directory'])
        (saved/'config.json').unlink(); (saved/'config.json').symlink_to(self.cfg)
        with self.assertRaises(VerdugoError): maintenance.verify_set(saved)

    def test_no_overwrite_of_live_or_existing_directories_and_role_required(self):
        saved = self.backup()
        with self.assertRaises((OSError,VerdugoError)): maintenance.create_set(self.engine, self.cfg, self.root)
        with self.assertRaises(VerdugoError): maintenance.restore_set(saved['saved_directory'], self.root, execute=True)
        with self.assertRaises(VerdugoError): maintenance.restore_set(saved['saved_directory'], self.root/'new', role='viewer', execute=True)
        self.engine.role = 'viewer'
        with self.assertRaises(VerdugoError): self.backup()

    def test_readiness_shows_missing_and_stale_backup_without_claiming_live_verification(self):
        report = maintenance.readiness(self.engine, self.cfg, self.assets)
        self.assertEqual([c['id'] for c in report['checks'] if not c['ok']], ['recent_backup'])
        self.assertNotIn('demo@example.invalid', json.dumps(report))
        self.backup()
        self.assertEqual(maintenance.readiness(self.engine, self.cfg, self.assets)['state'], 'local_checks_passed')
        with patch('verdugo.maintenance.time.time', return_value=__import__('time').time()+86401):
            self.assertEqual(maintenance.readiness(self.engine, self.cfg, self.assets)['state'], 'attention_required')
        self.assertEqual(report['live_verified'], 0)
        self.assertFalse(report['restoration_tested_on_this_host'])

    def test_failed_snapshot_cleans_only_its_new_destination(self):
        target = self.root/'backup'
        with patch('verdugo.maintenance.backups.create', side_effect=VerdugoError('synthetic disk failure')):
            with self.assertRaises(VerdugoError): maintenance.create_set(self.engine, self.cfg, target)
        self.assertFalse(target.exists()); self.assertTrue(self.cfg.exists())

    def test_cli_preview_and_error_require_no_live_engine_or_existing_state(self):
        saved = self.backup(); target = self.root/'new'
        args = [sys.executable,'-m','verdugo','--state',str(self.root/'never.sqlite'),'restore-product',
                '--from',saved['saved_directory'],'--to',str(target)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['state'], 'planned')
        self.assertFalse(target.exists()); self.assertFalse((self.root/'never.sqlite').exists())

    def test_init_creates_private_config_even_with_shared_umask(self):
        path = self.root/'new-config.json'
        result = subprocess.run([sys.executable,'-m','verdugo','init','--out',str(path)], capture_output=True, text=True, umask=0o022)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
