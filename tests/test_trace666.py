"""Fixed policy input boundaries and original-source integrity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_trace666 as trace
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'events': [
    {'kind': 'read_private', 'previous_state': 'failed', 'hypothetical_review': True},
    {'kind': 'send', 'previous_state': 'uncertain', 'hypothetical_review': False}]}


class Trace666Tests(unittest.TestCase):
    def test_rejects_code_credentials_real_data_and_unbounded_traces(self):
        trace.validate('invariant', 'trace.check', CASE)
        for key, value in [('policy', 'import os'), ('token', 'secret'),
                           ('url', 'https://example.invalid'), ('dataset', 'real'),
                           ('events', []), ('events', CASE['events'] * 7), ('events', {})]:
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                trace.validate('invariant', 'trace.check', dict(CASE, **{key: value}))

    def test_rejects_tool_arguments_and_approval_coercion(self):
        for key, value in [('kind', 'shell'), ('previous_state', 'approved'),
                           ('hypothetical_review', 1), ('hypothetical_review', 'true'),
                           ('arguments', {'body': 'private data'}), ('content', 'private')]:
            p = copy.deepcopy(CASE); p['events'][0][key] = value
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                trace.validate('invariant', 'trace.check', p)
        for service, operation in [('invariant', 'policy.execute'), ('other', 'trace.check')]:
            with self.assertRaises(VerdugoError):
                trace.validate(service, operation, CASE)

    def test_source_pin_and_modified_installed_dependency_fail_closed(self):
        record = json.loads(trace.CONTRACT.read_text())
        source = next(r for r in read_registry()['records'] if r['id'] == 'invariant')
        self.assertEqual(source['commit_sha'], record['sources'][0]['commit'])
        self.assertEqual(80, sum(bool(f['installed_path']) for s in record['sources'] for f in s['files']))
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / 'changed.py'; changed.write_text('# changed')
            with patch.object(trace.metadata, 'distribution') as dist:
                dist.return_value.version = '0.3.5'
                dist.return_value.locate_file.return_value = changed
                with self.assertRaises(VerdugoError):
                    trace.verify_source()
