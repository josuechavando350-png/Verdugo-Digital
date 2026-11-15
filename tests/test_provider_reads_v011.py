"""Contract-level tests for eight bounded read-only provider adapters.

The loopback provider below is synthetic. Passing these tests does NOT
certify any vendor installation, account or live third-party service.
"""
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
import tempfile
import threading
import unittest
from unittest.mock import patch

from verdugo.license_policy import EXCLUDED
POLICY_EXCEPTION = {'approved_by': 'contract-fixture', 'reason': 'Synthetic contract test of an adapter excluded by license policy.'}
from verdugo.__main__ import template
from verdugo.adapters import SPECS, build
from verdugo.common import VerdugoError
from verdugo.engine import Engine
from verdugo.transport import send

ROUTES = {
    "novu": ("workflows.list", "/v2/workflows"),
    "superset": ("dashboards.list", "/api/v1/dashboard/"),
    "supabase": ("projects.list", "/v1/projects"),
    "coolify": ("servers.list", "/api/v1/servers"),
    "keycloak": ("realms.list", "/admin/realms"),
    "unleash": ("projects.list", "/api/admin/projects"),
    "medusa": ("products.list", "/admin/products"),
    "openfga": ("stores.list", "/stores"),
}
TOKEN = "synthetic-secret-token-never-real"


class ReadProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.config = template("nexus")
        self.env = {}
        for sid in ROUTES:
            cfg = self.config["tenants"]["nexus"]["services"][sid]
            cfg.update(enabled=True, license_reviewed=True,
                       version="contract-fixture-only",
                       base_url="https://example.invalid")
            if sid in EXCLUDED:
                cfg["license_policy_exception"] = dict(POLICY_EXCEPTION)
            self.env[cfg["token_env"]] = TOKEN
        self.keys = patch.dict(os.environ, self.env)
        self.keys.start()

    def tearDown(self):
        self.keys.stop()
        self.tmp.cleanup()

    def command(self, sid, key=None, params=None):
        return dict(service=sid, operation=ROUTES[sid][0],
                    params={} if params is None else params,
                    key=key or "read-" + sid)

    def test_routes_are_exact_get_only_and_services_registered(self):
        for sid, (op, path) in ROUTES.items():
            with self.subTest(service=sid):
                self.assertEqual({op: ("GET", path)}, SPECS[sid])
                req = build(sid, op, {}, self.config["tenants"]["nexus"]["services"][sid])
                self.assertEqual("GET", req["public"]["method"])
                self.assertEqual(path, urlsplit(req["public"]["url"]).path)
                expected_query = ({"limit": ["50"], "offset": ["0"]}
                                  if sid == "medusa" else {})
                self.assertEqual(expected_query,
                                 parse_qs(urlsplit(req["public"]["url"]).query))
                self.assertFalse(req["mutates"])
                self.assertIsNone(req["public"]["body"])
                self.assertNotIn(TOKEN, json.dumps(req["public"]))

    def test_authentication_modes(self):
        for sid, (op, _) in ROUTES.items():
            req = build(sid, op, {}, self.config["tenants"]["nexus"]["services"][sid])
            expected = (TOKEN if sid == "unleash" else
                        "ApiKey " + TOKEN if sid == "novu" else
                        "Basic " + TOKEN if sid == "medusa" else
                        "Bearer " + TOKEN)
            self.assertEqual(expected, req["headers"]["Authorization"])
        cfg = self.config["tenants"]["nexus"]["services"]["medusa"]
        cfg["auth_mode"] = "jwt_bearer"
        jwt = build("medusa", ROUTES["medusa"][0], {}, cfg)
        self.assertEqual("Bearer " + TOKEN, jwt["headers"]["Authorization"])
        cfg["auth_mode"] = "unsupported"
        with self.assertRaises(VerdugoError):
            build("medusa", ROUTES["medusa"][0], {}, cfg)

    def test_bounded_pagination_and_no_injected_urls_or_headers(self):
        for sid, (op, _) in ROUTES.items():
            cfg = self.config["tenants"]["nexus"]["services"][sid]
            for params in (
                {"page": 0}, {"page": -1}, {"page": 1001},
                {"page": True}, {"page": "2"}, {"url": "https://evil.invalid"},
                {"headers": {"Authorization": "other"}}, {"token": "raw"},
                {"tenant": "other"}, {"limit": 999999}, {"query": "DELETE"},
            ):
                with self.subTest(sid=sid, params=params), self.assertRaises(VerdugoError):
                    build(sid, op, params, cfg)
            if sid == "medusa":
                second = build(sid, op, {"page": 2}, cfg)
                self.assertEqual({"limit": ["50"], "offset": ["50"]},
                                 parse_qs(urlsplit(second["public"]["url"]).query))
            else:
                with self.assertRaises(VerdugoError):
                    build(sid, op, {"page": 2}, cfg)

    def test_disabled_credentials_and_license_gates(self):
        for sid in ROUTES:
            cfg = self.config["tenants"]["nexus"]["services"][sid]
            with patch.dict(os.environ, {}, clear=True):
                with self.subTest(sid=sid), self.assertRaises(VerdugoError):
                    build(sid, ROUTES[sid][0], {}, cfg)
            cfg["license_reviewed"] = False
            engine = Engine(":memory:", self.config)
            try:
                with self.assertRaises(VerdugoError):
                    engine.plan(self.command(sid))
            finally:
                engine.close()
            cfg["license_reviewed"] = True
            cfg["enabled"] = False
            engine = Engine(":memory:", self.config)
            try:
                with self.assertRaises(VerdugoError):
                    engine.plan(self.command(sid))
            finally:
                engine.close()
            cfg["enabled"] = True

    def test_real_http_loopback_and_persistent_exactly_once_replay(self):
        incoming = []
        paths = {path: sid for sid, (_, path) in ROUTES.items()}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                sid = paths.get(urlsplit(self.path).path)
                incoming.append((sid, self.path, self.headers.get("Authorization")))
                row = {"id": sid, "kind": "synthetic"}
                if sid == "novu": payload = {"data": [row]}
                elif sid == "superset": payload = {"result": [row], "count": 1}
                elif sid == "unleash": payload = {"projects": [row]}
                elif sid == "medusa": payload = {"products": [row], "count": 1}
                elif sid == "openfga": payload = {"stores": [row]}
                else: payload = [row]
                body = json.dumps(payload).encode()
                self.send_response(200 if sid else 404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            for sid in ROUTES:
                self.config["tenants"]["nexus"]["services"][sid].update(
                    base_url="http://127.0.0.1:" + str(server.server_port),
                    allow_local_http=True)
            engine = Engine(self.path, self.config, transport=send)
            try:
                for sid in ROUTES:
                    cmd = self.command(sid)
                    self.assertEqual("planned", engine.execute(cmd)["state"])
                    outcome = engine.execute(cmd, True)
                    self.assertEqual("succeeded", outcome["state"], sid)
                    self.assertFalse(outcome["replayed"])
                    value = outcome["result"]
                    path = {"novu": "data", "superset": "result",
                            "unleash": "projects", "medusa": "products",
                            "openfga": "stores"}.get(sid)
                    items = value[path] if path else value
                    self.assertEqual("synthetic", items[0]["kind"])
                    self.assertEqual("succeeded", engine.execute(cmd, True)["state"])
                    self.assertFalse(engine.status()["integrations"][0]["live_verified"])
            finally:
                engine.close()
            self.assertEqual(8, len(incoming))
            engine = Engine(self.path, self.config, transport=send)
            try:
                for sid in ROUTES:
                    self.assertTrue(engine.execute(self.command(sid), True)["replayed"])
            finally:
                engine.close()
            self.assertEqual(8, len(incoming))
            for sid, path, received in incoming:
                self.assertEqual(path, ROUTES[sid][1] if sid != "medusa" else
                                 "/admin/products?limit=50&offset=0")
                self.assertEqual(
                    TOKEN if sid == "unleash" else
                        "ApiKey " + TOKEN if sid == "novu" else
                    "Basic " + TOKEN if sid == "medusa" else "Bearer " + TOKEN,
                    received)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(3)

    def test_malformed_collection_responses_are_failed_not_success(self):
        from verdugo.read_contracts import check
        bad = ({}, {"items": []}, {"projects": "not-a-list"},
               ["unexpected"], [{"ok": False}, "not-an-object"])
        for sid in ROUTES:
            expected_key = {"novu": "data", "superset": "result",
                            "unleash": "projects", "medusa": "products",
                            "openfga": "stores"}.get(sid)
            for bad_rows in (42, "text", [1], [{"ok": True}, None]):
                doc = {expected_key: bad_rows} if expected_key else bad_rows
                with self.subTest(sid=sid, doc=doc), self.assertRaises(VerdugoError):
                    check(sid, ROUTES[sid][0], doc)
        for sid in ROUTES:
            if sid in ("novu", "superset", "unleash", "medusa", "openfga"):
                with self.assertRaises(VerdugoError):
                    check(sid, ROUTES[sid][0], {"items": []})
        engine = Engine(":memory:", self.config,
                        transport=lambda *_: {"unrecognized": "not-a-collection"})
        try:
            for sid in ROUTES:
                state = engine.execute(self.command(sid), True)
                self.assertEqual("failed", state["state"], sid)
        finally:
            engine.close()

    def test_no_automatic_external_effects_in_preview(self):
        engine = Engine(":memory:", self.config,
                        transport=lambda *_: self.fail("preview made network call"))
        try:
            for sid in ROUTES:
                self.assertEqual("planned", engine.execute(self.command(sid))["state"])
        finally:
            engine.close()


if __name__ == "__main__":
    unittest.main()
