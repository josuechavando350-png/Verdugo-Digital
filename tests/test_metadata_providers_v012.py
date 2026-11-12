"""Seven bounded metadata provider adapters: route, privacy, control and wire tests.

All upstream bodies below are synthetic. No production integration is certified.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from verdugo.__main__ import template
from verdugo.adapters import SPECS, build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.read_contracts import check
from verdugo.transport import send

ROUTES = {
    "airbyte": ("workspaces.list", "/v1/workspaces"),
    "infisical": ("projects.list", "/api/v1/projects"),
    "growthbook": ("settings.read", "/api/v1/settings"),
    "openmeter": ("meters.list", "/api/v1/meters"),
    "nango": ("connections.list", "/connections"),
    "trigger": ("runs.list", "/api/v1/runs"),
    "documenso": ("envelopes.list", "/api/v2/envelope"),
}
CREDENTIAL = "synthetic-metadata-token"
SIGNING_TOKEN = "api_synthetic-documenso-token"
PRIVATE = "private@example.invalid"


def fixture(service):
    sensitive = {"internal": PRIVATE, "access_token": "not-for-sqlite"}
    if service == "airbyte":
        return {"data": [{"workspaceId": "abc123", "configuration": sensitive}], "next": ""}
    if service == "infisical":
        return {"projects": [{"id": "project-1", "metadata": sensitive}]}
    if service == "growthbook":
        return {"settings": {"organization": "example", "private": sensitive}}
    if service == "openmeter":
        return [{"id": "meter-1", "details": sensitive}]
    if service == "nango":
        return {"connections": [{"id": 10, "tags": {"end_user_email": PRIVATE},
                                 "credentials": sensitive}]}
    if service == "trigger":
        return {"data": [{"status": "COMPLETED", "payload": sensitive},
                         {"status": "FAILED", "error": PRIVATE}]}
    return {"data": [{"status": "PENDING", "recipients": [
        {"name": PRIVATE, "email": PRIVATE}]}], "count": 81, "totalPages": 81}


class MetadataProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "state.sqlite3"
        self.config = template("nexus")
        env = {}
        for service in ROUTES:
            cfg = self.config["tenants"]["nexus"]["services"][service]
            cfg.update(enabled=True, license_reviewed=True, version="contract-fixture-only")
            env[cfg["token_env"]] = SIGNING_TOKEN if service == "documenso" else CREDENTIAL
        self.patch = patch.dict(os.environ, env)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def command(self, service, params=None, key=None):
        return {"service": service, "operation": ROUTES[service][0],
                "params": {} if params is None else params,
                "key": key or "provider-" + service}

    def build(self, service, params=None):
        return build(service, ROUTES[service][0], {} if params is None else params,
                     self.config["tenants"]["nexus"]["services"][service])

    def test_exact_fixed_routes_only_no_remote_writes(self):
        for service, (operation, path) in ROUTES.items():
            with self.subTest(service=service):
                self.assertEqual({operation: ("GET", path)}, SPECS[service])
                request = self.build(service)
                self.assertEqual("GET", request["public"]["method"])
                self.assertEqual(path, urlsplit(request["public"]["url"]).path)
                self.assertFalse(request["mutates"])
                self.assertIsNone(request["public"]["body"])
                self.assertNotIn(CREDENTIAL, json.dumps(request["public"]))
                expected = (
                    {"limit": ["20"], "offset": ["0"]} if service == "airbyte" else
                    {"page": ["1"], "perPage": ["20"]} if service == "documenso" else
                    {"limit": ["20"]} if service == "trigger" else {})
                self.assertEqual(expected, parse_qs(urlsplit(request["public"]["url"]).query))
                with self.assertRaises(VerdugoError):
                    build(service, "admin.delete", {}, self.config["tenants"]["nexus"]["services"][service])

    def test_bearer_and_literal_documenso_auth(self):
        for service in ROUTES:
            with self.subTest(service=service):
                expected = (SIGNING_TOKEN if service == "documenso" else
                            "Bearer " + CREDENTIAL)
                self.assertEqual(expected, self.build(service)["headers"]["Authorization"])
        cfg = self.config["tenants"]["nexus"]["services"]["documenso"]
        with patch.dict(os.environ, {cfg["token_env"]: "not-an-api-token"}):
            with self.assertRaises(VerdugoError):
                self.build("documenso")

    def test_explicit_api_surfaces_and_bounded_pagination(self):
        for service, correct in (("airbyte", "cloud_v1"), ("openmeter", "oss_v1")):
            cfg = self.config["tenants"]["nexus"]["services"][service]
            self.assertEqual(correct, cfg["api_surface"])
            cfg["api_surface"] = "not-reviewed"
            with self.assertRaises(VerdugoError):
                self.build(service)
            cfg["api_surface"] = correct
        for service in ROUTES:
            for params in ({"page": 0}, {"page": True}, {"page": "2"},
                           {"page": 1001}, {"url": "https://evil.invalid"},
                           {"authorization": "x"}, {"headers": {}},
                           {"query": "DROP TABLE"}, {"limit": 100000}):
                with self.subTest(service=service, params=params), self.assertRaises(VerdugoError):
                    self.build(service, params)
            if service in ("airbyte", "documenso"):
                second = self.build(service, {"page": 2})
                query = parse_qs(urlsplit(second["public"]["url"]).query)
                self.assertEqual("20", query["offset"][0] if service == "airbyte" else query["perPage"][0])
                if service == "documenso":
                    self.assertEqual(["2"], query["page"])
            else:
                with self.assertRaises(VerdugoError):
                    self.build(service, {"page": 2})

    def test_private_raw_payloads_never_returned_to_engine(self):
        for service in ROUTES:
            data = check(service, ROUTES[service][0], fixture(service))
            encoded = json.dumps(data)
            self.assertNotIn(PRIVATE, encoded)
            self.assertNotIn("not-for-sqlite", encoded)
            self.assertFalse(data["raw_provider_payload_retained"])
            self.assertFalse(data["live_verified"])
            if service == "growthbook":
                self.assertTrue(data["settings_response_observed"])
            else:
                count = 2 if service == "trigger" else 1
                self.assertEqual(count, data["records_in_response"])
        trigger = check("trigger", "runs.list", fixture("trigger"))
        self.assertEqual({"COMPLETED": 1, "FAILED": 1}, trigger["status_counts"])
        doc = check("documenso", "envelopes.list", fixture("documenso"))
        self.assertEqual({"PENDING": 1}, doc["status_counts"])

    def test_invalid_provider_schema_fails_closed(self):
        for service in ROUTES:
            invalid_cases = (None, {"items": [PRIVATE]}, {"data": "not-list"},
                             [1], {"data": [True]}, "text")
            if service != "openmeter":
                invalid_cases = (*invalid_cases, [])
            for invalid in invalid_cases:
                with self.subTest(service=service, invalid=repr(invalid)), self.assertRaises(VerdugoError):
                    check(service, ROUTES[service][0], invalid)
            with self.assertRaises(VerdugoError):
                check(service, "unknown.operation", fixture(service))
        for service in ("trigger", "documenso"):
            data = fixture(service)
            data["data"][0]["status"] = PRIVATE
            result = check(service, ROUTES[service][0], data)
            self.assertIn("OTHER", result["status_counts"])
            self.assertNotIn(PRIVATE, json.dumps(result))
        with self.assertRaises(VerdugoError):
            check("growthbook", "settings.read", {"settings": []})

    def test_gates_and_preview_never_call_network(self):
        engine = Engine(":memory:", self.config, transport=lambda *_: self.fail("network attempted"))
        try:
            for service in ROUTES:
                self.assertEqual("planned", engine.execute(self.command(service))["state"])
                cfg = self.config["tenants"]["nexus"]["services"][service]
                cfg["license_reviewed"] = False
                with self.assertRaises(VerdugoError):
                    engine.plan(self.command(service))
                cfg["license_reviewed"] = True
                cfg["enabled"] = False
                with self.assertRaises(VerdugoError):
                    engine.plan(self.command(service))
                cfg["enabled"] = True
        finally:
            engine.close()

    def test_loopback_http_no_pii_persisted_and_replay_after_reopen(self):
        paths = {p: service for service, (_, p) in ROUTES.items()}
        called = []
        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                service = paths.get(urlsplit(self.path).path)
                called.append((service, self.path, self.headers.get("Authorization")))
                data = json.dumps(fixture(service)).encode() if service else b"{}"
                self.send_response(200 if service else 404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        srv = HTTPServer(("127.0.0.1", 0), Provider)
        worker = threading.Thread(target=srv.serve_forever, daemon=True)
        worker.start()
        try:
            for service in ROUTES:
                self.config["tenants"]["nexus"]["services"][service].update(
                    base_url="http://127.0.0.1:" + str(srv.server_port),
                    allow_local_http=True)
            engine = Engine(self.state, self.config, transport=send)
            try:
                for service in ROUTES:
                    response = engine.execute(self.command(service), True)
                    self.assertEqual("succeeded", response["state"], service)
                    self.assertFalse(response["result"]["raw_provider_payload_retained"])
                    self.assertNotIn(PRIVATE, json.dumps(response))
                    self.assertNotIn("not-for-sqlite", json.dumps(response))
            finally:
                engine.close()
            self.assertEqual(len(ROUTES), len(called))
            self.assertNotIn(PRIVATE, self.state.read_bytes().decode("utf-8", errors="ignore"))
            engine = Engine(self.state, self.config, transport=send)
            try:
                for service in ROUTES:
                    response = engine.execute(self.command(service), True)
                    self.assertEqual("succeeded", response["state"])
                    self.assertTrue(response["replayed"])
            finally:
                engine.close()
            self.assertEqual(len(ROUTES), len(called))
        finally:
            srv.shutdown()
            srv.server_close()
            worker.join(3)


if __name__ == "__main__":
    unittest.main()
