import copy
from pathlib import Path
import sys
import unittest

from verdugo import local_completion, local_runtime, local_source
from verdugo.common import VerdugoError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests_runtime'))
from completion_fixtures import CASES


class CompletionContracts(unittest.TestCase):
    def test_no_runtime_control_from_parameters(self):
        for sid, params in CASES.items():
            op = local_runtime.SPECS[sid][0]
            local_runtime.validate(sid, op, params)
            for field in ('url', 'token', 'tenant', 'sql', 'code', 'path', 'model', 'command', 'args'):
                with self.subTest(service=sid, field=field), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, op, dict(params, **{field: 'forbidden'}))

    def test_malformed_inputs_fail_closed(self):
        changes = {'trendspyg': [{'traffic': ['junk']}, {'traffic': ['-1']}, {'traffic': ['1e100']}, {'traffic': []}],
                   'vanna': [{'rows': []}],
                   'youtube-comment-downloader': [{'threads': [{'id': 'a', 'likes': True, 'replies': 0}]}, {'threads': []}],
                   'comtradeapicall': [{'selection': ['MISSING']}, {'selection': ['NORTH', 'NORTH']}],
                   'browser-use': [{'hosts': ['https://example.org/path']}, {'allowed': ['*']}],
                   'storm': [{'reference_count': True}, {'text': '[1234567]'}, {'text': 'x' * 16001}]}
        for sid, diffs in changes.items():
            for diff in diffs:
                with self.subTest(service=sid, diff=diff), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, local_runtime.SPECS[sid][0], dict(CASES[sid], **diff))

    def test_schema_and_dataset_are_required(self):
        for sid, params in CASES.items():
            for dataset in (None, 'synthetic', True):
                with self.subTest(service=sid), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, local_runtime.SPECS[sid][0], dict(params, dataset=dataset))

    def test_duplicate_comments_and_groups_rejected(self):
        for sid, field in [('youtube-comment-downloader', 'threads'), ('comtradeapicall', 'groups')]:
            params = copy.deepcopy(CASES[sid]); params[field].append(params[field][0])
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, local_runtime.SPECS[sid][0], params)

    def test_statistical_assumptions_and_budgets_are_not_implicit(self):
        for sid, diffs in {
            'tfcausalimpact': [{'assumptions_reviewed': False}, {'intervention_index': 3}, {'control': [1]*40}, {'outcome': [float('nan')]*40}],
            'meridian': [{'alpha': True}, {'slope': 0}, {'max_lag': 20}, {'media': [float('inf')]}],
        }.items():
            for diff in diffs:
                with self.subTest(service=sid, diff=diff), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, local_runtime.SPECS[sid][0], dict(CASES[sid], **diff))

    def test_bundled_original_source_cannot_be_silently_replaced(self):
        from unittest.mock import patch
        for sid in local_source.SPECS:
            local_source.source_path(sid)
            with patch.dict(local_source.HASHES, {sid: ('0'*64, local_source.HASHES[sid][1])}), self.assertRaises(VerdugoError):
                local_source.source_path(sid)
