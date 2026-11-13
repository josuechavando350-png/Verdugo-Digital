"""Only unit tests for acceptance safeguards; NOT proof of installed upstream apps."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

SOURCE = Path(__file__).resolve().parents[1] / "scripts/native-pair-acceptance.py"
spec = importlib.util.spec_from_file_location("native_acceptance", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeAcceptanceGuardTests(unittest.TestCase):
    def test_not_run_never_claims_ten_originals(self):
        report = native.evidence_base()
        self.assertEqual(report["status"], "not_run")
        self.assertEqual(report["verified_originals"], [])
        self.assertFalse(report["all_ten_integrated"])
        self.assertFalse(report["persistent_installation"])
        self.assertFalse(report["android_verified"])

    def test_missing_docker_is_blocker_not_success(self):
        report = native.evidence_base()
        with patch.object(native.shutil, "which", return_value=None):
            with self.assertRaisesRegex(native.AcceptanceError, "docker_engine_unavailable"):
                native.run_acceptance(report)
        self.assertEqual(report["verified_originals"], [])

    def test_complete_native_checks_are_required(self):
        report = native.evidence_base()
        with self.assertRaisesRegex(native.AcceptanceError, "incomplete_native_acceptance"):
            native.require_all_checks(report)
        report["checks"] = dict.fromkeys([
            "verdugo_persisted_lead", "mautic_created_and_read_back", "countly_recorded_and_read_back",
            "mautic_after_restart", "countly_after_restart", "verdugo_after_restart"], True)
        native.require_all_checks(report)
        self.assertEqual(report["verified_originals"], ["mautic", "countly"])
        self.assertFalse(report["all_ten_integrated"])
        self.assertFalse(report["persistent_installation"])
        self.assertFalse(report["android_verified"])

    def test_even_one_unverified_readback_prevents_pass(self):
        report = native.evidence_base()
        report["checks"] = dict.fromkeys([
            "verdugo_persisted_lead", "mautic_created_and_read_back", "countly_recorded_and_read_back",
            "mautic_after_restart", "countly_after_restart", "verdugo_after_restart"], True)
        report["checks"]["countly_after_restart"] = False
        with self.assertRaisesRegex(native.AcceptanceError, "incomplete_native_acceptance"):
            native.require_all_checks(report)

    def test_non_loopback_targets_rejected_before_network(self):
        for url in ["https://example.com", "http://localhost:3001", "http://10.0.0.1", "file:///etc/passwd"]:
            with self.subTest(url=url):
                with self.assertRaisesRegex(native.AcceptanceError, "acceptance_is_loopback_only"):
                    native.request(url)

    def test_redirect_never_forwards_credentials(self):
        with self.assertRaisesRegex(native.AcceptanceError, "redirect_refused"):
            native.NoRedirect().redirect_request(None, None, 302, "", {}, "http://other.invalid")

    def test_public_report_has_no_credentials(self):
        import json
        report = json.dumps(native.evidence_base())
        for name in ["password", "api_key", "Authorization", "control_token"]:
            self.assertNotIn(name, report)

    def test_image_refs_are_immutable_digests(self):
        for image in native.IMAGES.values():
            self.assertRegex(image, r"^[a-z0-9/_-]+@sha256:[a-f0-9]{64}$")

    def test_approved_native_origin_is_exact_not_a_network_wildcard(self):
        native.NATIVE_ORIGINS.add("http://172.28.0.3:3001")
        try:
            for url in ["http://172.28.0.4:3001", "http://172.28.0.3:80", "http://172.28.0.3:3001@evil.invalid"]:
                with self.assertRaises(native.AcceptanceError):
                    native.request(url)
        finally:
            native.NATIVE_ORIGINS.clear()

    def test_command_failure_redacts_temporary_credentials(self):
        import contextlib
        import io
        native.REDACT.add("secret-for-unit-test-only")
        try:
            result = Mock(returncode=1, stderr="db failed: secret-for-unit-test-only", stdout="")
            output = io.StringIO()
            with patch.object(native.subprocess, "run", return_value=result):
                with contextlib.redirect_stdout(output):
                    with self.assertRaises(native.AcceptanceError):
                        native.command(["docker", "exec", "x"])
            self.assertNotIn("secret-for-unit-test-only", output.getvalue())
            self.assertIn("[REDACTED]", output.getvalue())
        finally:
            native.REDACT.clear()

    def test_only_two_upstream_products_in_profile(self):
        self.assertEqual(set(native.IMAGES), {"mysql", "mongo", "mautic", "countly_api", "countly_frontend"})
        self.assertNotIn("posthog", native.IMAGES)


if __name__ == "__main__":
    unittest.main()
