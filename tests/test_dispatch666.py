"""Boundaries and source-integrity checks for queue policy compilation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_dispatch666 as dispatch
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset': 'demo', 'operation_kind': 'write', 'previous_state': 'uncertain',
        'max_parallel': 2, 'requested_retries': 3, 'timeout_seconds': 30,
        'retention_seconds': 600}


class Dispatch666Tests(unittest.TestCase):
    def test_rejects_extra_execution_credentials_destinations_and_code(self):
        dispatch.validate('hatchet', 'policy.compile', CASE)
        for key, value in [('token', 'secret'), ('url', 'https://example.invalid'),
                           ('code', 'run'), ('expression', 'input.other'), ('dataset', 'real')]:
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                dispatch.validate('hatchet', 'policy.compile', dict(CASE, **{key: value}))
        with self.assertRaises(VerdugoError):
            dispatch.validate('hatchet', 'dispatch', CASE)

    def test_bounded_numbers_and_fixed_states_fail_closed(self):
        for key, value in [('max_parallel', True), ('max_parallel', 0), ('max_parallel', 5),
                           ('requested_retries', -1), ('requested_retries', 4),
                           ('timeout_seconds', 121), ('retention_seconds', 59),
                           ('retention_seconds', 86401), ('previous_state', 'approved'),
                           ('operation_kind', 'shell')]:
            with self.subTest(key=key, value=value), self.assertRaises(VerdugoError):
                dispatch.validate('hatchet', 'policy.compile', dict(CASE, **{key: value}))

    def test_original_source_pin_and_modified_installed_code(self):
        record = json.loads(dispatch.CONTRACT.read_text())
        source = next(r for r in read_registry()['records'] if r['id'] == 'hatchet')
        self.assertEqual(source['commit_sha'], record['commit'])
        self.assertEqual(411, sum(bool(f['installed_path']) for f in record['files']))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'modified.py'; path.write_text('# modified')
            with patch.object(dispatch.metadata, 'distribution') as dist:
                dist.return_value.version = dispatch.SPECS['hatchet'][2]
                dist.return_value.locate_file.return_value = path
                with self.assertRaises(VerdugoError):
                    dispatch.verify_source()
