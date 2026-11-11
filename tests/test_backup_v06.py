"""Backups are local, private, unencrypted and independently integrity-checked."""
import os
import errno
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from test_core import Base
from verdugo import backups
from verdugo.common import VerdugoError, encode
from verdugo.engine import Engine


class BackupsTests(Base):
    def target(self,name='snapshot.sqlite3'):
        return str(Path(self.tmp.name)/name)

    def test_sqlite_online_snapshot_is_consistent_and_private(self):
        self.engine.execute(self.lead(),True)
        r=backups.create(self.engine,self.target())
        self.assertEqual('created_and_verified_local_copy',r['state'])
        self.assertTrue(r['contains_personal_data']);self.assertFalse(r['encrypted'])
        self.assertEqual(0o600,Path(self.target()).stat().st_mode & 0o777)
        self.assertEqual('verified_local_copy',backups.verify(self.target())['state'])
        with closing(sqlite3.connect(self.target())) as db:
            self.assertEqual(1,db.execute("SELECT COUNT(*) FROM records WHERE kind='lead'").fetchone()[0])
        self.engine.execute(self.lead(key='later',lead_id='later'),True)
        with closing(sqlite3.connect(self.target())) as db:
            self.assertEqual(1,db.execute("SELECT COUNT(*) FROM records WHERE kind='lead'").fetchone()[0])

    def test_backup_cannot_overwrite_existing_or_live_db(self):
        backups.create(self.engine,self.target())
        with self.assertRaises(VerdugoError):backups.create(self.engine,self.target())
        with self.assertRaises(VerdugoError):backups.create(self.engine,str(self.path))
        self.assertEqual('ok',self.engine.db.execute('PRAGMA integrity_check').fetchone()[0])

    def test_memory_not_accepted(self):
        e=Engine(':memory:')
        try:
            with self.assertRaises(VerdugoError):backups.create(e,self.target())
        finally:e.close()

    def test_viewer_cannot_export_records(self):
        e=Engine(self.path,self.config,role='viewer')
        try:
            with self.assertRaises(VerdugoError):backups.create(e,self.target())
        finally:e.close()
        self.assertFalse(Path(self.target()).exists())

    def test_shared_directory_rejected_before_file_creation(self):
        dest=Path(self.tmp.name)/'shared';dest.mkdir(mode=0o755);dest.chmod(0o755)
        with self.assertRaises(VerdugoError):backups.create(self.engine,str(dest/'copy.sqlite3'))
        self.assertFalse((dest/'copy.sqlite3').exists())

    def test_symlink_and_world_readable_backup_rejected(self):
        backups.create(self.engine,self.target())
        link=self.target('link.sqlite3');Path(link).symlink_to(self.target())
        with self.assertRaises(VerdugoError):backups.verify(link)
        os.chmod(self.target(),0o644)
        with self.assertRaises(VerdugoError):backups.verify(self.target())

    def test_backup_detects_corruption(self):
        backups.create(self.engine,self.target())
        p=Path(self.target())
        with p.open('r+b') as f:f.write(b'NOT SQLITE')
        with self.assertRaises(VerdugoError):backups.verify(p)

    def test_path_must_have_sqlite_suffix(self):
        for name in ('snapshot.txt','snapshot.db','', 'x'*165+'.sqlite3'):
            with self.subTest(name=name),self.assertRaises(VerdugoError):backups.create(self.engine,self.target(name))

    def test_backup_cli_and_verify_cli(self):
        dest=self.target();base=[sys.executable,'-m','verdugo','--state',str(self.path)]
        r=subprocess.run(base+['backup-local','--to',dest],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,r.returncode,r.stderr)
        c=subprocess.run(base+['verify-backup','--file',dest],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,c.returncode,c.stderr)
        self.assertIn('sha256',c.stdout)

    def test_duplicate_parallel_creation_fails_without_overwrite(self):
        workers=[]; results=[]; errors=[]; barrier=threading.Barrier(2)
        def task():
            engine=Engine(self.path,self.config)
            try:
                barrier.wait(timeout=3)
                results.append(backups.create(engine,self.target())['state'])
            except (VerdugoError,FileExistsError) as exc:errors.append(type(exc).__name__)
            finally:engine.close()
        for i in range(2):workers.append(threading.Thread(target=task))
        for t in workers:t.start()
        for t in workers:t.join(10)
        self.assertEqual(1,len(results));self.assertEqual(1,len(errors))
        self.assertEqual('verified_local_copy',backups.verify(self.target())['state'])

    def test_termux_without_os_link_uses_safe_exclusive_copy(self):
        with patch.object(os, 'link', None, create=True):
            result = backups.create(self.engine, self.target())
        self.assertEqual('exclusive_copy_verified', result['publish_method'])
        self.assertFalse(result['atomic_publication'])
        self.assertTrue(result['verify_before_use'])
        self.assertEqual(result['sha256'], backups.verify(self.target())['sha256'])
        with self.assertRaises(VerdugoError): backups.create(self.engine, self.target())

    def test_unsupported_hardlink_syscall_uses_copy(self):
        with patch.object(os, 'link', side_effect=OSError(errno.ENOSYS, 'unsupported'), create=True):
            result = backups.create(self.engine, self.target())
        self.assertEqual('exclusive_copy_verified', result['publish_method'])
        self.assertEqual('verified_local_copy', backups.verify(self.target())['state'])

    def test_fallback_copy_failure_leaves_no_misleading_backup(self):
        with patch.object(os, 'link', None, create=True):
            with patch('verdugo.backups.shutil.copyfileobj', side_effect=OSError('synthetic interrupted copy')):
                with self.assertRaises(OSError): backups.create(self.engine, self.target())
        self.assertFalse(Path(self.target()).exists())

    def test_backup_inspection_closes_connection(self):
        backups.create(self.engine, self.target())
        with closing(sqlite3.connect(self.target())) as db:
            self.assertEqual('ok', db.execute('PRAGMA integrity_check').fetchone()[0])
        with self.assertRaises(sqlite3.ProgrammingError):
            db.execute('SELECT 1')

    def test_old_snapshot_cannot_claim_running_recovery(self):
        # A local backup does not certify that a remote request completed.
        self.engine.execute(self.lead(),True)
        report=backups.create(self.engine,self.target())
        self.assertFalse(report['remote_execution_resumed'])
        self.assertFalse(report['restoration_tested'])
        self.assertFalse(report['bank_reconciled'])
