import copy
import json
from pathlib import Path
import sys
import unittest

from verdugo import local_runtime, local_research
from verdugo.common import VerdugoError
from verdugo.source_evidence import read_sources

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from research_fixtures import CASES


class ResearchContracts(unittest.TestCase):
    def test_source_files_and_catalog_pins_cover_all_operations(self):
        sources = {r['id']: r for r in read_sources()}
        manifest = json.loads((Path(__file__).resolve().parents[1]/'sources/contracts-v020-research.json').read_text())
        self.assertEqual(set(local_research.SPECS), {r['service'] for r in manifest['files']})
        for r in manifest['files']:
            self.assertEqual(40, len(r['blob_sha']))
            if 'commit' in r: self.assertEqual(sources[r['service']]['commit_sha'], r['commit'])

    def test_duplicate_records_features_and_ranking_rejected(self):
        for sid, key in [('splink', 'records'), ('feast', 'rows'), ('recommenders', 'ranked')]:
            p = copy.deepcopy(CASES[sid]); p[key].append(p[key][0])
            with self.assertRaises(VerdugoError): local_runtime.validate(sid, local_research.SPECS[sid][0], p)

    def test_real_data_requires_explicit_assumptions_and_bounds(self):
        changes = {'causalml': {'assumptions_acknowledged': False}, 'opendp': {'scale': 0},
                   'mesa': {'steps': 101}, 'financetoolkit': {'current_liabilities': 0},
                   'osmnx': {'destination': 'unknown'}, 'whisper': {'samples': [0]*399},
                   'pipecat': {'left': [32768]}, 'mcp-python-sdk': {'is_error': 1},
                   'pydantic-ai': {'messages': [{'role': 'system', 'text': 'untrusted'}]}}
        for sid, change in changes.items():
            with self.subTest(service=sid), self.assertRaises(VerdugoError):
                local_runtime.validate(sid, local_research.SPECS[sid][0], dict(CASES[sid], **change))

    def test_incomplete_trade_matrix_is_not_silently_imputed(self):
        p = copy.deepcopy(CASES['py-ecomplexity']); p['rows'].pop()
        with self.assertRaises(VerdugoError): local_runtime.validate('py-ecomplexity', 'trade.structure', p)


def contract_case(sid):
    def test(self):
        op = local_research.SPECS[sid][0]
        local_runtime.validate(sid, op, CASES[sid])
        for field in ('url', 'path', 'sql', 'token', 'tenant', 'shell', 'python', 'callback', 'model'):
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, op, dict(CASES[sid], **{field: 'blocked'}))
        for dataset in ('', None, True, 'production'):
            with self.assertRaises(VerdugoError):
                local_runtime.validate(sid, op, dict(CASES[sid], dataset=dataset))
        with self.assertRaises(VerdugoError): local_runtime.validate(sid, op+'.unsupported', CASES[sid])
    return test


for _sid in local_research.SPECS:
    setattr(ResearchContracts, 'test_contract_'+_sid.replace('-', '_'), contract_case(_sid))
