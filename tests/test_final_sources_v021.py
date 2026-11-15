import json
from pathlib import Path
import unittest
from verdugo import local_cli,local_content,local_native,local_pycli
from verdugo.source_evidence import read_sources

class FinalSources(unittest.TestCase):
    def test_every_new_operation_has_pinned_original_api_evidence(self):
        sources={r['id']:r for r in read_sources()}
        groups={'cli':set(local_cli.SPECS),'content':{*local_content.SPECS,*local_pycli.SPECS},'native':set(local_native.SPECS)}
        for group,expected in groups.items():
            rows=json.loads((Path(__file__).resolve().parents[1]/f'sources/contracts-v021-{group}.json').read_text())['files']
            self.assertEqual(expected,{r['service'] for r in rows})
            for row in rows:
                self.assertEqual(sources[row['service']]['commit_sha'],row['commit'])
                self.assertRegex(row['blob_sha'],r'^[0-9a-f]{40}$')
                self.assertIn('/blob/'+row['commit']+'/',row['url'])
