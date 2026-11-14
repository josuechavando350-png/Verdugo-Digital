"""v0.14: unified 322-entry catalogue and fail-closed license policy."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo.__main__ import template
from verdugo.catalog import catalog, CORE_COUNT
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo import license_policy
from verdugo.license_policy import EXCLUDED, PATH, read_policy, summary, check
from verdugo.mcp import invoke, tool_definitions
from verdugo.source_evidence import read_sources

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'synthetic-key:synthetic-secret-not-real'


def fresh_policy(path):
    license_policy._CACHE.pop(str(path), None)
    return read_policy(path)


class CatalogueTests(unittest.TestCase):
    def test_catalogue_is_core_plus_expansion_without_duplicates(self):
        rows = catalog()
        self.assertEqual(100, CORE_COUNT)
        self.assertEqual(322, len(rows))
        self.assertEqual(list(range(1, 323)), [r['number'] for r in rows])
        self.assertEqual(322, len({r['repository'].casefold() for r in rows}))
        domains = {r['domain'] for r in rows[CORE_COUNT:]}
        self.assertEqual({'marketing', 'authority', 'strategy', 'agents', 'platform', 'dataengine'}, domains)

    def test_new_blocks_have_expected_sizes(self):
        rows = catalog()[CORE_COUNT:]
        count = lambda d: sum(r['domain'] == d for r in rows)
        self.assertEqual(40, count('agents'))
        self.assertEqual(40, count('platform'))
        self.assertEqual(42, count('dataengine'))
        self.assertEqual(100, count('marketing') + count('authority') + count('strategy'))

    def test_every_entry_is_pinned_and_matches_policy_evidence(self):
        pins = {r['id']: r['commit_sha'] for r in read_sources()}
        for row in read_policy().values():
            if row['origin'] != 'core-100':
                self.assertEqual(pins[row['id']], row['scanned_commit'])


class PolicyEvidenceTests(unittest.TestCase):
    def test_exactly_300_allowed_and_22_excluded(self):
        value = summary()
        self.assertEqual(322, value['registered'])
        self.assertEqual(300, value['allowed'])
        self.assertEqual(sorted(EXCLUDED), value['excluded'])
        self.assertEqual(322, value['license_review_pending'])
        self.assertFalse(value['legal_advice'])

    def test_no_copyleft_or_source_available_license_is_allowed(self):
        bad = ('GPL', 'Elastic', 'SUL', 'BUSL-1.1', 'FSL', 'LicenseRef', 'NONE', 'UNKNOWN')
        for sid, row in read_policy().items():
            if row['policy'] in ('libre', 'libre_nucleo'):
                with self.subTest(sid=sid):
                    self.assertFalse(any(row['spdx'].startswith(b) or row['spdx'] == b for b in bad))
                    self.assertNotIn('GPL', row['spdx'])

    def test_known_examples(self):
        expectations = {'twenty': 'excluido', 'remotion': 'excluido', 'airbyte': 'excluido',
                        'browser-use': 'libre', 'posthog': 'libre_nucleo',
                        'meilisearch': 'libre_nucleo', 'sops': 'libre_condicionado',
                        'splink': 'libre', 'nextjs': 'libre'}
        for sid, policy in expectations.items():
            with self.subTest(sid=sid):
                self.assertEqual(policy, summary(sid)['policy'])

    def test_unknown_project_rejected(self):
        for value in ('', 'not-registered', '../x', 5):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                summary(value)

    def test_tampering_is_rejected(self):
        original = json.loads(PATH.read_text())
        mutations = [
            lambda d: d['records'][0].update(policy='libre'),             # excluded flipped to allowed
            lambda d: d['records'][150].update(policy='excluido'),        # allowed count drops
            lambda d: d['records'][200].update(spdx='AGPL-3.0'),          # copyleft marked libre
            lambda d: d['records'][5].update(license_review='approved'),  # legal review asserted
            lambda d: d['records'][7].update(scanned_commit='main'),
            lambda d: d['records'].pop(),
            lambda d: d['records'][3].update(repository='attacker/x'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'licenses.json'
            target.write_text(json.dumps(original))
            self.assertEqual(322, len(fresh_policy(target)))
            for i, mutate in enumerate(mutations):
                changed = json.loads(json.dumps(original))
                mutate(changed)
                target.write_text(json.dumps(changed))
                with self.subTest(mutation=i), self.assertRaises(VerdugoError):
                    fresh_policy(target)

    def test_symlink_and_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            link = Path(temp) / 'link.json'
            link.symlink_to(PATH)
            with self.assertRaises(VerdugoError):
                fresh_policy(link)
            big = Path(temp) / 'big.json'
            big.write_text(' ' * 300000)
            with self.assertRaises(VerdugoError):
                fresh_policy(big)


class EngineGateTests(unittest.TestCase):
    def setUp(self):
        self.config = template('nexus')
        services = self.config['tenants']['nexus']['services']
        for sid in ('twenty', 'chatwoot'):
            services[sid].update(enabled=True, license_reviewed=True, version='contract-fixture-only')
        self.env = patch.dict(os.environ, {services[s]['token_env']: SECRET for s in ('twenty', 'chatwoot')})
        self.env.start()
        self.calls = []

        def transport(req, cfg):
            self.calls.append(req['public'])
            return {'data': {'people': {'edges': []}}, 'payload': [], 'meta': {}}
        self.engine = Engine(':memory:', self.config, transport=transport)

    def tearDown(self):
        self.engine.close()
        self.env.stop()

    def test_excluded_adapter_is_refused_before_any_call(self):
        command = {'service': 'twenty', 'operation': 'people.list', 'params': {}, 'key': 'policy-1'}
        with self.assertRaisesRegex(VerdugoError, 'Excluded by license policy \\(AGPL-3.0\\): twenty'):
            self.engine.execute(command, True)
        with self.assertRaises(VerdugoError):
            self.engine.plan(command)
        self.assertEqual([], self.calls)

    def test_exception_must_be_named_and_reasoned(self):
        cfg = self.config['tenants']['nexus']['services']['twenty']
        for value in (True, 'yes', {}, {'approved_by': 'x'}, {'approved_by': ' ', 'reason': 'r'},
                      {'approved_by': 'a', 'reason': 'r', 'auto': True}, {'approved_by': 'a' * 201, 'reason': 'r'}):
            cfg['license_policy_exception'] = value
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                check('twenty', cfg)
        cfg['license_policy_exception'] = {'approved_by': 'Josue', 'reason': 'Conciliar una escritura incierta'}
        self.assertEqual('Josue', check('twenty', cfg)['approved_by'])

    def test_permissive_adapter_is_not_affected(self):
        self.assertIsNone(check('chatwoot', self.config['tenants']['nexus']['services']['chatwoot']))
        self.engine.preflight('chatwoot', 'conversations.list')

    def test_template_never_preapproves_exceptions(self):
        services = template('nexus')['tenants']['nexus']['services']
        self.assertEqual(322, len(services))
        self.assertFalse(any('license_policy_exception' in c for c in services.values()))
        self.assertFalse(any(c['enabled'] for c in services.values()))

    def test_status_reports_policy_per_integration(self):
        status = self.engine.status()
        self.assertEqual(300, status['license_policy_allowed'])
        self.assertEqual(22, status['license_policy_excluded'])
        self.assertEqual(86, status['adapters_usable_under_policy'])
        row = next(r for r in status['integrations'] if r['id'] == 'twenty')
        self.assertEqual(('AGPL-3.0', 'excluido'), (row['license_detected'], row['license_policy']))
        self.assertEqual(0, status['live_verified'])


class InterfaceTests(unittest.TestCase):
    def test_mcp_tool_is_read_only(self):
        tool = next(t for t in tool_definitions() if t['name'] == 'verdugo_license_policy')
        self.assertTrue(tool['annotations']['readOnlyHint'])
        self.assertEqual('excluido', invoke(None, 'verdugo_license_policy', {'project_id': 'n8n'})['policy'])
        self.assertEqual(300, invoke(None, 'verdugo_license_policy', {})['allowed'])

    def test_cli_does_not_create_state_or_touch_network(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            for args in (['licenses'], ['licenses', 'splink']):
                proc = subprocess.run([sys.executable, '-m', 'verdugo', *args], cwd=temp, env=env,
                                      capture_output=True, text=True, timeout=10)
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIsInstance(json.loads(proc.stdout), dict)
            self.assertFalse((Path(temp) / '.state').exists())
        with patch('socket.socket', side_effect=AssertionError('network attempted')):
            self.assertEqual(300, summary()['allowed'])


if __name__ == '__main__':
    unittest.main()
