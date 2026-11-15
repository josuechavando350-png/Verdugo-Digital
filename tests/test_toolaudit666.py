"""PyRIT source migration, fixed data boundaries and source integrity."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_toolaudit666 as audit
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'calls': [
    {'tool': 'draft', 'format': 'chat', 'outcome': 'invoked', 'simulated': False}]}


class ToolAudit666Tests(unittest.TestCase):
    def test_rejects_raw_messages_and_remote_operations(self):
        audit.validate('pyrit', 'tools.audit', CASE)
        for key, value in [('dataset', 'real'), ('token', 'secret'), ('messages', []),
                           ('url', 'https://example.invalid'), ('calls', []),
                           ('calls', CASE['calls'] * 9)]:
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                audit.validate('pyrit', 'tools.audit', dict(CASE, **{key: value}))
        with self.assertRaises(VerdugoError):
            audit.validate('pyrit', 'tools.execute', CASE)

    def test_rejects_arbitrary_tools_arguments_and_boolean_coercion(self):
        for key, value in [('tool', 'shell'), ('format', 'url'), ('outcome', 'approved'),
                           ('simulated', 1), ('arguments', 'private'), ('call_id', 'private')]:
            p = copy.deepcopy(CASE); p['calls'][0][key] = value
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                audit.validate('pyrit', 'tools.audit', p)

    def test_original_source_change_fails_closed(self):
        record = json.loads(audit.CONTRACT.read_text())
        source = next(r for r in read_registry()['records'] if r['id'] == 'pyrit')
        self.assertEqual(source['commit_sha'], record['commit'])
        self.assertEqual(946, sum(bool(f['installed_path']) for f in record['files']))
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / 'changed.py'; changed.write_text('# changed')
            with patch.object(audit.metadata, 'distribution') as dist:
                dist.return_value.version = '1.3.0.dev0'
                dist.return_value.locate_file.return_value = changed
                with self.assertRaises(VerdugoError):
                    audit.verify_source()

    def test_migration_preserves_previous_identity_and_original_announcement(self):
        root = audit.CONTRACT.parent
        revision = json.loads((root / 'registry-666-revisions.json').read_text())['revisions'][0]
        source = next(r for r in read_registry()['records'] if r['id'] == revision['id'])
        self.assertEqual('Azure/PyRIT', revision['previous']['repository'])
        self.assertEqual('microsoft/PyRIT', source['repository'])
        self.assertEqual(revision['current_commit'], source['commit_sha'])
        self.assertEqual(revision['current_repository_id'], source['repository_id'])
        notice = revision['announcement']; data = notice['text'].encode()
        self.assertIn('https://github.com/microsoft/PyRIT', notice['text'])
        self.assertEqual(notice['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(notice['blob_sha'], hashlib.sha1(
            ('blob ' + str(len(data))).encode() + bytes([0]) + data).hexdigest())
