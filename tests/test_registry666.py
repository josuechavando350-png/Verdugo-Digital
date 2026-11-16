"""Identity, original license integrity and truthful readiness of expansion 666."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from verdugo import connections, license_policy, source_evidence
from verdugo.__main__ import template
from verdugo.catalog import catalog
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.registry666 import PATH, TEXTS, read_registry


class Registry666Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = read_registry()

    def test_all_688_github_identities_are_distinct_including_aliases(self):
        d = self.document
        ids = [r['github_id'] for r in d['base_identities']] + [r['repository_id'] for r in d['records']]
        self.assertEqual(688, len(set(ids)))
        self.assertEqual(366, len(d['records']))
        self.assertEqual(list(range(323, 689)), [r['number'] for r in d['records']])

    def test_six_corrections_preserve_evidence_without_double_counting(self):
        changes = self.document['corrections']
        self.assertEqual(5, sum(r['reason'] == 'duplicate_repository_identity' for r in changes))
        self.assertEqual({'ragas', 'presidio', 'fastmcp', 'recommenders', 'great-expectations'},
                         {r['existing_id'] for r in changes if r['existing_id']})
        ten = next(r for r in changes if r['reason'] == 'restricted_license')
        self.assertEqual('TEN-framework/ten-framework', ten['canonical_repository'])
        self.assertNotIn(ten['canonical_repository'], {r['repository'] for r in catalog()})
        text = (TEXTS / (ten['license_evidence'][0]['sha256'] + '.txt')).read_text()
        self.assertIn('competes with Agora', text)

    def test_two_ordered_batches_of_183_and_simulator_is_phase_three(self):
        q = self.document['work_queue']
        self.assertEqual([183, 183], [sum(r['batch'] == n for r in q) for n in (1, 2)])
        self.assertEqual(366, len({r['id'] for r in q}))
        sim = {r['id'] for r in self.document['records'] if r['origin'] == 'simulador-mercado'}
        self.assertEqual(50, len(sim))
        self.assertEqual(sim, {r['id'] for r in q if r['phase'] == 3})

    def test_registration_does_not_create_operational_connections(self):
        self.assertEqual({'conectado': 285, 'pieza_de_construccion': 56,
                          'pendiente': 325, 'excluido': 22}, connections.summary()['states'])
        self.assertEqual(666, license_policy.summary()['allowed'])
        for r in self.document['records']:
            with self.subTest(project=r['id']):
                state = connections.summary(r['id'])
                self.assertEqual('conectado' if r['id'] in ('semantic-kernel', 'agno', 'ag2', 'langroid', 'griptape', 'beeai-framework', 'harness-sdk', 'unified-planning', 'voltagent', 'servers', 'monty', 'playwright-python', 'hatchet', 'invariant', 'pyrit', 'llama-cpp', 'granite-guardian', 'interpret', 'transformerlens', 'bitsandbytes', 'guidance', 'lm-format-enforcer', 'tensorzero', 'opik', 'memos', 'lightrag', 'kernel-memory', 'chroma', 'milvus', 'usearch', 'ragflow', 'infinity', 'rerankers', 'sympy', 'rdflib', 'jena', 'z3', 'txtai', 'kag', 'bm25s', 'egg', 'oxigraph') else 'pendiente', state['state'])
                self.assertEqual({'tensorzero':['inferences.summary'], 'opik':['projects.summary'], 'memos':['scheduler.summary'], 'lightrag':['documents.summary'], 'kernel-memory':['indexes.summary'], 'chroma':['collections.summary'], 'milvus':['collections.summary'], 'ragflow':['datasets.summary'], 'infinity':['models.summary'], 'jena':['datasets.summary'], 'kag':['task.summary']}.get(r['id'], []), state['http_actions'])
                self.assertEqual({'semantic-kernel':['objective.plan'], 'agno':['objective.plan'], 'ag2':['actions.check'], 'langroid':['claims.check'], 'griptape':['objective.scenarios'], 'beeai-framework':['review.route'], 'harness-sdk':['limits.parallel'], 'unified-planning':['sequence.validate'], 'voltagent':['measurement.review'], 'servers':['graph.audit'], 'monty':['budget.evaluate'], 'playwright-python':['cookies.check'], 'hatchet':['policy.compile'], 'invariant':['trace.check'], 'pyrit':['tools.audit'], 'llama-cpp':['tokens.check'], 'granite-guardian':['risk.assess'], 'interpret':['prediction.explain'], 'transformerlens':['activations.check'], 'bitsandbytes':['quantization.check'], 'guidance':['schema.check'], 'lm-format-enforcer':['prefix.check'], 'usearch':['neighbors.check'], 'rerankers':['results.rank'], 'sympy':['polynomial.check'], 'rdflib':['reachability.check'], 'z3':['constraints.check'], 'txtai':['content.reconcile'], 'bm25s':['retrieval.check'], 'egg':['congruence.check'], 'oxigraph':['paths.check']}.get(r['id'], []), state['local_actions'])
                self.assertFalse(state['live_verified'])

    def test_unimplemented_projects_fail_even_when_configuration_is_enabled(self):
        cfg = template('nexus')
        calls = []
        engine = Engine(':memory:', cfg, transport=lambda *args: calls.append(args))
        try:
            for r in self.document['records']:
                sid = r['id']
                cfg['tenants']['nexus']['services'][sid].update(enabled=True, license_reviewed=True)
                with self.subTest(project=sid), self.assertRaises(VerdugoError):
                    engine.plan({'service': sid, 'operation': 'invented.action', 'params': {}, 'key': 'check-' + sid})
        finally:
            engine.close()
        self.assertEqual([], calls)

    def test_offline_evidence_and_original_licenses_are_read_without_network(self):
        with patch('socket.socket', side_effect=AssertionError('network attempted')):
            self.assertEqual(688, read_registry()['registered'])
        self.assertEqual(69, len(source_evidence.PART_NAMES))
        self.assertEqual(8, len(json.loads((source_evidence.PARTS / '69.json').read_text())))

    def test_tampered_manifest_fails_closed(self):
        mutations = [
            lambda d: d['records'][0].update(repository_id=d['base_identities'][0]['github_id']),
            lambda d: d['base_identities'][0].update(canonical=d['records'][0]['repository']),
            lambda d: d['records'][0].update(commit_sha='main'),
            lambda d: d['records'][0]['license_evidence'][0].update(path='../LICENSE'),
            lambda d: d['records'][0]['license_evidence'][0].update(blob_sha='0'*40),
            lambda d: d['records'][0]['license_evidence'][0].update(source_url='https://example.invalid'),
            lambda d: d['records'][0].update(license_evidence=[]),
            lambda d: d['work_queue'][183].update(batch=1),
            lambda d: d['work_queue'][1].update(id=d['work_queue'][0]['id']),
            lambda d: d['work_queue'][0].update(live_verified=True),
            lambda d: d['work_queue'][0].update(status='connected'),
            lambda d: d['corrections'][0].update(existing_id='invented'),
            lambda d: d['corrections'].pop(),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'registry.json'
            for index, mutate in enumerate(mutations):
                changed = copy.deepcopy(self.document)
                mutate(changed)
                target.write_text(json.dumps(changed))
                with self.subTest(mutation=index), self.assertRaises(VerdugoError):
                    read_registry(target)

    def test_original_license_tampering_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            texts = Path(tmp) / 'texts'
            shutil.copytree(TEXTS, texts)
            ev = self.document['records'][0]['license_evidence'][0]
            license_file = texts / (ev['sha256'] + '.txt')
            license_file.write_bytes(license_file.read_bytes() + b' altered')
            with self.assertRaises(VerdugoError):
                read_registry(texts=texts)
            license_file.unlink()
            license_file.symlink_to(TEXTS / license_file.name)
            with self.assertRaises(VerdugoError):
                read_registry(texts=texts)

    def test_license_policy_cannot_switch_pin_or_permissive_label_without_evidence(self):
        source = json.loads(license_policy.PATH.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'licenses.json'
            for field, value in [('scanned_commit', 'a'*40), ('spdx', 'MIT'), ('license_files', ['OTHER'])]:
                changed = copy.deepcopy(source)
                changed['records'][322][field] = value
                target.write_text(json.dumps(changed))
                license_policy._CACHE.pop(str(target), None)
                with self.subTest(field=field), self.assertRaises(VerdugoError):
                    license_policy.read_policy(target)
