import json
from pathlib import Path
import unittest
from verdugo import local_cli,local_content,local_native,local_pycli,local_planning
from verdugo.source_evidence import read_sources

class FinalSources(unittest.TestCase):
    def test_completion_sources_cover_every_declared_operation(self):
        from verdugo import local_completion, local_source, completion_reads, public_reads
        root=Path(__file__).resolve().parents[1]
        document=json.loads((root/'sources/contracts-v021-completion.json').read_text())
        expected=set(local_completion.SPECS)|set(local_source.SPECS)|set(completion_reads.SPECS)|set(public_reads.SPECS)
        sources={r['id']:r for r in read_sources()}
        self.assertEqual(expected,{r['id'] for r in document['records']})
        self.assertEqual(len(expected),len(document['records']))
        for record in document['records']:
            self.assertEqual(sources[record['id']]['commit_sha'],record['catalog_commit'])
            self.assertFalse(record['live_verified']);self.assertTrue(record['files'])
            for source in record['files']:
                self.assertEqual(record['catalog_commit'],source['commit'])
                self.assertRegex(source['git_blob_sha'],r'^[0-9a-f]{40}$')
                self.assertRegex(source['sha256'],r'^[0-9a-f]{64}$')
        plan=json.loads((root/'docs/plan_conexion.json').read_text())
        self.assertEqual(expected|{'lighthouse','slidev','promptfoo','log4brains','pricesensitivitymeter','robyn'},{r['id'] for r in plan['implemented_v021_completion']})

    def test_every_new_operation_has_pinned_original_api_evidence(self):
        sources={r['id']:r for r in read_sources()}
        groups={'planning':set(local_planning.SPECS),'cli':set(local_cli.SPECS),'content':{*local_content.SPECS,*local_pycli.SPECS},'native':set(local_native.SPECS)}
        for group,expected in groups.items():
            rows=json.loads((Path(__file__).resolve().parents[1]/f'sources/contracts-v021-{group}.json').read_text())['files']
            self.assertEqual(expected,{r['service'] for r in rows})
            for row in rows:
                self.assertEqual(sources[row['service']]['commit_sha'],row['commit'])
                self.assertRegex(row['blob_sha'],r'^[0-9a-f]{40}$')
                self.assertIn('/blob/'+row['commit']+'/',row['url'])
