import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_r, local_runtime
from verdugo.common import VerdugoError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests_runtime'))
from r_fixtures import CASES


class RContracts(unittest.TestCase):
    def test_bounded_numeric_inputs_and_no_code_paths(self):
        for sid, params in CASES.items():
            operation = local_r.SPECS[sid][0]
            local_runtime.validate(sid, operation, params)
            for key in ('script', 'code', 'url', 'path', 'args', 'shell', 'model', 'weights', 'tenant'):
                with self.subTest(service=sid, key=key), self.assertRaises(VerdugoError):
                    local_runtime.validate(sid, operation, dict(params, **{key: 'forbidden'}))
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, operation, dict(params, dataset='implicit'))

    def test_survey_order_and_transform_finiteness(self):
        for value in (float('nan'), float('inf'), -1, True, 'system("id")'):
            survey = copy.deepcopy(CASES['pricesensitivitymeter'])
            survey['responses'][0]['cheap'] = value
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                local_r.validate('pricesensitivitymeter', 'prices.survey', survey)
            with self.assertRaises(VerdugoError):
                local_r.validate('robyn', 'media.transform', dict(CASES['robyn'], theta=value))
        survey = copy.deepcopy(CASES['pricesensitivitymeter'])
        survey['responses'][0]['expensive'] = survey['responses'][0]['cheap']
        with self.assertRaises(VerdugoError):
            local_r.validate('pricesensitivitymeter', 'prices.survey', survey)
        with self.assertRaises(VerdugoError):
            local_r.validate('robyn', 'media.transform', dict(CASES['robyn'], spend=[0, 0]))

    def test_source_integrity_and_missing_runtime_fail_closed(self):
        for sid in CASES:
            local_r.source_path(sid)
            with patch.dict(os.environ, {local_r.ENV: '/nonexistent/verdugo-r'}), patch('subprocess.run', side_effect=AssertionError('Executed')):
                self.assertFalse(local_r.runtime_state(sid)['version_matches'])
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'robyn'; folder.mkdir()
            for name in local_r.contract()['sources']['robyn']:
                (folder / name).write_bytes((local_r.ROOT / 'robyn' / name).read_bytes())
            with patch.object(local_r, 'ROOT', Path(temp)):
                local_r.source_path('robyn')
                (folder / 'transformation.R').write_text('stop("changed")')
                with self.assertRaises(VerdugoError):
                    local_r.source_path('robyn')

    def test_source_evidence_matches_original_file_bytes(self):
        import hashlib
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root / 'sources/contracts-v021-r.json').read_text())
        self.assertEqual(set(CASES), {row['service'] for row in evidence['files']})
        for row in evidence['files']:
            raw = (local_r.ROOT / row['service'] / row['bundled_name']).read_bytes()
            self.assertEqual(row['blob_sha'], hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest())
            self.assertEqual(local_r.SPECS[row['service']][2], row['commit'])
