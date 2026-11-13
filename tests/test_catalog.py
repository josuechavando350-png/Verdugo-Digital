import configparser
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "posthog", "growthbook", "erxes", "mautic", "dittofeed",
    "rudderstack", "openreplay", "twenty", "countly", "formbricks",
}

class CatalogContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = json.loads((ROOT / "stack/catalog.json").read_text(encoding="utf-8"))["projects"]

    def test_exactly_ten_known_projects(self):
        self.assertEqual(len(self.items), 10)
        self.assertEqual({item["id"] for item in self.items}, EXPECTED)

    def test_unique_upstream_urls_and_no_false_certification(self):
        urls = [item["upstream_url"] for item in self.items]
        self.assertEqual(len(urls), len(set(urls)))
        for item in self.items:
            with self.subTest(project=item["id"]):
                self.assertEqual(item["upstream_url"], "https://github.com/" + item["repository"])
                self.assertEqual(item["status"], "catalogued")
                for key in ("installed", "connected", "live_test_passed", "production_certified"):
                    self.assertIs(item[key], False)

    def test_submodule_manifest_matches_catalog(self):
        parser = configparser.ConfigParser()
        self.assertTrue(parser.read(ROOT / ".gitmodules", encoding="utf-8"))
        self.assertEqual(len(parser.sections()), 10)
        for item in self.items:
            section = 'submodule "upstream/' + item["id"] + '"'
            self.assertIn(section, parser.sections())
            self.assertEqual(parser[section]["path"], "upstream/" + item["id"])
            self.assertEqual(parser[section]["url"], item["upstream_url"] + ".git")

    @unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "Git checkout required")
    def test_ten_pinned_gitlinks_exist_in_commit(self):
        result = subprocess.run(
            ["git", "ls-tree", "HEAD:upstream"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        entries = {}
        for line in result.stdout.splitlines():
            metadata, name = line.split("\t", 1)
            mode, kind, sha = metadata.split()
            self.assertEqual((mode, kind), ("160000", "commit"))
            self.assertRegex(sha, r"^[0-9a-f]{40}$")
            entries[name] = sha
        self.assertEqual(set(entries), EXPECTED)
