import json
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
