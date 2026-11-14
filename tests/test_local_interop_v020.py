import copy
import json
from pathlib import Path
import sys
import unittest

from verdugo import local_runtime, local_interop
from verdugo.common import VerdugoError
from verdugo.source_evidence import read_sources

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from interop_fixtures import CASES


class InteropContracts(unittest.TestCase):
    def test_source_pins_cover_every_operation(self):
        sources = {r['id']: r for r in read_sources()}
        manifest = json.loads((Path(__file__).resolve().parents[1]/'sources/contracts-v020-interop.json').read_text())
        self.assertEqual(set(local_interop.SPECS), {r['service'] for r in manifest['files']})
        for row in manifest['files']:
            self.assertEqual(40, len(row['blob_sha']))
            self.assertEqual(sources[row['service']]['commit_sha'], row['commit'])

    def test_no_external_entities_or_unbounded_work(self):
        cases = {'parsedmarc': {'xml': '<!DOCTYPE feedback [<!ENTITY x SYSTEM "file:///etc/passwd">]><feedback>&x;</feedback>'},
                 'sentence-transformers': {'left': [[0, 0]]}, 'bertopic': {'counts': [[1, 0], [2, 0]]},
                 'transformers': {'vocabulary': ['a']*7}, 'ax': {'labels': [1, 1, 1, 1]},
                 'cdx-toolkit': {'captures': [{'timestamp': '20260230000000', 'status': 200, 'mime': 'text/html'}]}}
        for sid, changes in cases.items():
            with self.subTest(service=sid), self.assertRaises(VerdugoError):
                local_runtime.validate(sid, local_interop.SPECS[sid][0], dict(CASES[sid], **changes))

    def test_fixed_tool_never_accepts_a_caller_function(self):
        for sid in local_interop.TOOLS:
            p = copy.deepcopy(CASES[sid]); p['function'] = 'arbitrary'
            with self.assertRaises(VerdugoError): local_runtime.validate(sid, 'campaigns.tool', p)


def contract_case(sid):
    def test(self):
        operation = local_interop.SPECS[sid][0]
        local_runtime.validate(sid, operation, CASES[sid])
        for key in ('url', 'path', 'sql', 'token', 'tenant', 'shell', 'python', 'callback', 'model'):
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, operation, dict(CASES[sid], **{key: 'forbidden'}))
        for dataset in ('', None, True, 'production'):
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, operation, dict(CASES[sid], dataset=dataset))
        with self.assertRaises(VerdugoError): local_runtime.validate(sid, operation+'.unsupported', CASES[sid])
    return test


for _sid in local_interop.SPECS:
    setattr(InteropContracts, 'test_contract_'+_sid.replace('-', '_'), contract_case(_sid))
