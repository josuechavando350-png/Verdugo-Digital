"""Regression tests for the immutable source-evidence boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdugo.adapters import SPECS
from verdugo.catalog import catalog
from verdugo.common import VerdugoError
from verdugo.source_evidence import PARTS, PART_NAMES, read_sources, report
from verdugo.mcp import invoke, tool_definitions


class SourceEvidenceTests(unittest.TestCase):
    def test_exact_match_to_100_approved_sources(self):
        entries = read_sources()
        approved = catalog()
        self.assertEqual(100, len(entries))
        self.assertEqual([r["repository"] for r in approved],
                         [r["repository"] for r in entries])
        self.assertTrue(all(len(r["commit_sha"]) == 40 for r in entries))
        self.assertEqual(100, len({r["commit_sha"] + r["repository"] for r in entries}))

    def test_summary_is_explicit_about_non_deployment(self):
        value = report()
        self.assertEqual(100, value["registered"])
        self.assertEqual(100, value["source_pinned"])
        self.assertEqual(100, value["license_review_pending"])
        self.assertEqual(len(SPECS), value["http_adapters_implemented"])
        self.assertEqual(0, value["live_verified"])
        self.assertEqual(0, value["production_ready"])
        self.assertFalse(value["external_calls_made"])

    def test_single_source_has_read_only_commit_url(self):
        value = report("twenty")
        self.assertEqual("twenty", value["project_id"])
        self.assertIn(value["source_commit_sha"], value["source_url"])
        self.assertTrue(value["http_api_recipe_available"])
        self.assertFalse(value["ready_for_production"])
        self.assertEqual("pending", value["license_review"])

    def test_unimplemented_source_is_not_a_runtime_adapter(self):
        result = report("whisper")
        self.assertFalse(result["http_api_recipe_available"])
        self.assertEqual([], result["implemented_http_actions"])
        self.assertFalse(result["live_verified"])

    def test_unknown_source_rejected(self):
        for value in ("", "unapproved-project", "../catalog.py", 123):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                report(value)

    def test_manifest_is_strict_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for name in PART_NAMES:
                shutil.copyfile(PARTS / name, target / name)
            self.assertEqual(100, len(read_sources(target)))
            first = target / "01.json"
            original = json.loads(first.read_text())
            for field, new_value in (
                ("commit_sha", "floating-main"),
                ("repository", "attacker/other"),
                ("number", 999),
                ("license_review", "reviewed"),
            ):
                changed = json.loads(json.dumps(original))
                changed[0][field] = new_value
                first.write_text(json.dumps(changed))
                with self.subTest(field=field), self.assertRaises(VerdugoError):
                    read_sources(target)
            first.write_text(json.dumps(original))
            (target / "10.json").unlink()
            with self.assertRaises(VerdugoError):
                read_sources(target)

    def test_extra_manifest_part_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for name in PART_NAMES:
                shutil.copyfile(PARTS / name, target / name)
            (target / "11.json").write_text("[]")
            with self.assertRaises(VerdugoError):
                read_sources(target)

    def test_source_query_does_not_touch_network(self):
        with patch("socket.socket", side_effect=AssertionError("network attempted")):
            self.assertEqual(100, report()["source_pinned"])
            self.assertTrue(report("restic")["source_commit_sha"])

    def test_cli_commands_do_not_create_state(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            for args in (["sources"], ["source-inspect", "restic"]):
                proc = subprocess.run(
                    [sys.executable, "-m", "verdugo", *args],
                    cwd=root, capture_output=True, text=True, timeout=10)
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIsInstance(json.loads(proc.stdout), dict)
            self.assertFalse((root / ".state" / "verdugo.sqlite3").exists())

    def test_mcp_tool_readonly_and_no_external_calls(self):
        tool = next(t for t in tool_definitions()
                    if t["name"] == "verdugo_source_evidence")
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        value = invoke(None, "verdugo_source_evidence", {"project_id": "restic"})
        self.assertEqual(40, len(value["source_commit_sha"]))
        self.assertFalse(value["external_calls_made"])


if __name__ == "__main__":
    unittest.main()
