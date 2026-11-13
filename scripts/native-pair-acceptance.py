#!/usr/bin/env python3
"""Disposable real-service acceptance, NOT a production installer or a mock.

Installs official Mautic and Countly images in an isolated Docker network,
passes a synthetic lead from the existing Verdugo core into their real APIs,
requires persisted readback after restart, then destroys only this run's resources.
No user's credentials, subscriptions, production contacts or outbound mail are used.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGES = {
    "mysql": "mysql@sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b",
    "mongo": "mongo@sha256:9896df581dfd0718b7abe112f4c37598d0986c54060e4ec1384997e6503c8c71",
    "mautic": "mautic/mautic@sha256:cfab53971c036a1a1cf176b4c2663b2313d0f5d372edc99c23397ee6179f81d7",
    "countly_api": "countly/api@sha256:e2c643ee7818d043981403aa5b8ef52ddbda2c0f57a3f7e16c18d9bd6df4e3d8",
    "countly_frontend": "countly/frontend@sha256:5fadf37d6f0a33d4d2e2e4c7b656fea8f5c5766ff86acf144d31f03447ac33a0",
}

GROWTHBOOK_IMAGE = "growthbook/growthbook@sha256:74844e961f4fb65785ddb351bb2417a33a9cbcf0b1aa73774709aee986324afb"
# Only addresses discovered from this run's private Docker network are authorized.
NATIVE_ORIGINS: set[str] = set()
REDACT: set[str] = set()


class AcceptanceError(RuntimeError):
    """Only non-sensitive, bounded error codes are exposed in public evidence."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcceptanceError("redirect_refused")


def request(url: str, *, data=None, headers=None, form=False, expect_json=True):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "http" or (parsed.hostname != "127.0.0.1" and
            parsed.scheme + "://" + parsed.netloc not in NATIVE_ORIGINS)
            or parsed.username or parsed.password or parsed.fragment):
        raise AcceptanceError("acceptance_is_loopback_only")
    encoded = None
    merged = dict(headers or {})
    if data is not None:
        if form:
            encoded = urllib.parse.urlencode(data).encode()
            merged["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            encoded = json.dumps(data).encode()
            merged["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=encoded, headers=merged)
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(req, timeout=15) as response:
            body = response.read(1_048_577)
            if len(body) > 1_048_576:
                raise AcceptanceError("response_too_large")
            if not expect_json:
                return {"http_status": response.status, "body": body.decode("utf-8")}
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        raise AcceptanceError(f"http_status_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise AcceptanceError("http_unreachable") from None
    except (json.JSONDecodeError, UnicodeError):
        raise AcceptanceError("invalid_json_response") from None


def command(args: list[str], *, timeout=180, input_text=None) -> str:
    # Never log arguments: Docker's temporary credentials appear in some commands.
    try:
        p = subprocess.run(args, input=input_text, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        raise AcceptanceError("command_timeout_or_missing") from None
    if p.returncode:
        # Registry throttling is a transient download failure, not a provider failure.
        # Only retries of docker pull are permitted; never replay HTTP writes.
        if args[:2] == ["docker", "pull"] and any(
                message in p.stderr.lower() for message in
                ("toomanyrequests", "rate exceeded", "too many requests", "429 too many requests")):
            raise AcceptanceError("registry_rate_limited")
        detail = p.stderr[-1800:]
        for secret in sorted(REDACT, key=len, reverse=True):
            detail = detail.replace(secret, "[REDACTED]")
        # This is a disposable synthetic-only laboratory. Do not print full commands.
        print("NATIVE_COMMAND_ERROR=" + detail, flush=True)
        raise AcceptanceError("command_failed_" + args[0] + "_" + (args[1] if len(args)>1 else "") + "_" + str(p.returncode))
    return p.stdout.strip()


def pull_image(docker, ref, *, max_attempts=6, sleeper=time.sleep):
    """Retry only verified registry throttling; never return a fake image success."""
    if type(max_attempts) is not int or not 1 <= max_attempts <= 6:
        raise AcceptanceError("invalid_pull_attempt_limit")
    for index in range(max_attempts):
        try:
            return docker("pull", ref, timeout=300)
        except AcceptanceError as exc:
            if str(exc) != "registry_rate_limited" or index + 1 == max_attempts:
                raise
            delay = min(15 * (2 ** index), 180)
            print("NATIVE_REGISTRY_RETRY_DELAY_SECONDS=" + str(delay), flush=True)
            sleeper(delay)
    raise AcceptanceError("unreachable_pull_state")


def wait_until(fn, seconds=180):
    until = time.monotonic() + seconds
    last = "not_ready"
    while time.monotonic() < until:
        try:
            result = fn()
            if result:
                return result
        except (AcceptanceError, AssertionError) as exc:
            last = str(exc)
        time.sleep(2)
    raise AcceptanceError("readiness_timeout_" + last[:100])


def evidence_base(include_growthbook=False, include_rudderstack=False):
    return {
        "schema_version": 1,
        "scope": ("ephemeral_growthbook_mautic_rudderstack_countly_native_api_acceptance" if include_rudderstack
                  else "ephemeral_growthbook_mautic_countly_native_api_acceptance" if include_growthbook
                  else "ephemeral_mautic_countly_native_api_acceptance"),
        "rudderstack_requested": bool(include_rudderstack),
        "growthbook_requested": bool(include_growthbook),
        "commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "runtime": "official_upstream_docker_images",
        "synthetic_data": True,
        "mock_providers": False,
        "checks": {},
        "images": {},
        "verified_originals": [],
        "all_ten_integrated": False,
        "persistent_installation": False,
        "android_verified": False,
        "status": "not_run",
    }


def require_all_checks(report):
    needed = ("verdugo_persisted_lead", "mautic_created_and_read_back", "countly_recorded_and_read_back",
              "mautic_after_restart", "countly_after_restart", "verdugo_after_restart")
    if report.get("growthbook_requested") is True:
        needed += ("growthbook_feature_created_and_read_back", "growthbook_to_mautic_route",
                   "countly_route_read_back", "growthbook_after_restart", "countly_route_after_restart")
    if report.get("rudderstack_requested") is True:
        if report.get("growthbook_requested") is not True:
            raise AcceptanceError("rudderstack_profile_requires_growthbook")
        needed += ("rudderstack_gateway_accepted", "rudderstack_rejects_missing_auth",
                   "rudderstack_delivery_after_restart")
    if any(report["checks"].get(key) is not True for key in needed):
        raise AcceptanceError("incomplete_native_acceptance")
    report["verified_originals"] = (["growthbook", "mautic", "countly"]
                                    if report.get("growthbook_requested") is True else ["mautic", "countly"])
    if report.get("rudderstack_requested") is True:
        report["verified_originals"].insert(2, "rudderstack")
    report["status"] = "passed"


def mask_secret(value):
    if not isinstance(value, str) or not value:
        raise AcceptanceError("invalid_temporary_secret")
    REDACT.add(value)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print("::add-mask::" + value, flush=True)


def native_origin(info, network, port):
    """Resolve only an exact private network membership, including after a restart."""
    networks = info["NetworkSettings"]["Networks"]
    if set(networks) != {network}:
        raise AcceptanceError("unexpected_container_network")
    address = networks[network]["IPAddress"]
    ip = ipaddress.ip_address(address)
    if ip.version != 4 or not ip.is_private or ip.is_unspecified or ip.is_loopback:
        raise AcceptanceError("container_address_not_private")
    if type(port) is not int or not 0 < port < 65536:
        raise AcceptanceError("invalid_native_port")
    origin = f"http://{address}:{port}"
    NATIVE_ORIGINS.add(origin)
    return origin


def initialize_growthbook(base, password):
    """Use original account, authentication, API-key and feature REST endpoints."""
    wait_until(lambda: request(base + "/healthcheck") is not None)
    registered = request(base + "/auth/firsttime", data={
        "email": "operator@example.invalid", "name": "Verdugo Synthetic Laboratory",
        "password": password, "companyname": "Verdugo Native Acceptance"})
    if not isinstance(registered.get("token"), str):
        raise AcceptanceError("growthbook_registration_failed")
    mask_secret(registered["token"])
    login = request(base + "/auth/login", data={"email": "operator@example.invalid", "password": password})
    token = login.get("token")
    mask_secret(token)
    auth = {"Authorization": "Bearer " + token}
    user = request(base + "/user", headers=auth)
    organizations = user.get("organizations")
    if not isinstance(organizations, list) or len(organizations) != 1:
        raise AcceptanceError("growthbook_organization_readback_failed")
    auth["X-Organization"] = organizations[0]["id"]
    created = request(base + "/keys", data={"type": "admin", "description": "Synthetic acceptance only"}, headers=auth)
    key = created.get("key", {}).get("key")
    mask_secret(key)
    feature_id = "verdugo-unified-native-routing"
    route = "native-route-" + secrets.token_hex(8)
    rest_auth = {"Authorization": "Bearer " + key}
    value = request(base + "/api/v1/features", data={
        "id": feature_id, "valueType": "string", "defaultValue": route,
        "description": "Route shared with original Mautic and Countly",
        "owner": "operator@example.invalid", "project": registered.get("projectId", "")}, headers=rest_auth)
    if value.get("feature", {}).get("id") != feature_id:
        raise AcceptanceError("growthbook_feature_creation_failed")
    state = {"key": key, "feature_id": feature_id, "route": route}
    if read_growthbook_route(base, state) != route:
        raise AcceptanceError("growthbook_feature_readback_failed")
    return state


def read_growthbook_route(base, state):
    feature = request(base + "/api/v1/features/" + state["feature_id"],
                      headers={"Authorization": "Bearer " + state["key"]})
    route = feature.get("feature", {}).get("defaultValue")
    if route != state["route"]:
        raise AcceptanceError("growthbook_route_mismatch")
    return route


def contact_route(contact, expected):
    tags = contact.get("tags", [])
    if isinstance(tags, dict):
        tags = list(tags.values())
    values = [tag.get("tag") if isinstance(tag, dict) else tag for tag in tags]
    if expected not in values:
        raise AcceptanceError("mautic_growthbook_route_mismatch")
    return next(value for value in values if value == expected)


def private_writable_mount(source, root, destination):
    """Only disposable child directories; never mount arbitrary host state writable."""
    path, base = Path(source), Path(root).resolve()
    resolved = path.resolve()
    if (destination not in ('/mnt/efs', '/data') or path.is_symlink()
            or not path.is_dir() or resolved == base or not resolved.is_relative_to(base)):
        raise AcceptanceError('native_writable_mount_not_owned')
    return f'type=bind,src={resolved},dst={destination}'


def run_acceptance(report, *, include_growthbook=False, transport=None):
    if type(include_growthbook) is not bool or report.get("growthbook_requested", False) is not include_growthbook:
        raise AcceptanceError("native_profile_mismatch")
    if bool(report.get("rudderstack_requested", False)) is not (transport is not None):
        raise AcceptanceError("native_transport_profile_mismatch")
    if transport is not None and not include_growthbook:
        raise AcceptanceError("rudderstack_profile_requires_growthbook")
    if not shutil.which("docker"):
        raise AcceptanceError("docker_engine_unavailable")
    if platform.machine().lower() not in ("x86_64", "amd64"):
        raise AcceptanceError("this_acceptance_profile_requires_x86_64")
    if "com.termux" in os.environ.get("PREFIX", ""):
        raise AcceptanceError("native_docker_profile_not_termux")
    command(["docker", "info", "--format", "{{.OSType}}"])
    if not shutil.which("node"):
        raise AcceptanceError("node_unavailable")
    if not (ROOT / "lib/control-plane.mjs").is_file():
        raise AcceptanceError("verdugo_core_missing")

    prefix = "vd-native-" + secrets.token_hex(5)
    network = prefix + "-net"
    names = {}
    started = []
    core = None
    network_created = False
    private = tempfile.TemporaryDirectory(prefix="verdugo-acceptance-")
    temp = Path(private.name)
    stage = "pull_images"

    def log(label):
        nonlocal stage
        stage = label
        print("NATIVE_ACCEPTANCE_STAGE=" + label, flush=True)

    def docker(*args, **kwargs):
        return command(["docker", *args], **kwargs)

    def start(name, image_id, *, env=None, alias=None, port=None, args=(), mounts=(), writable_dirs=()):
        cname = prefix + "-" + name
        cmd = ["run", "-d", "--name", cname, "--network", network,
               "--label", "verdugo.acceptance=" + prefix, "--memory", "1536m"]
        if alias:
            cmd += ["--network-alias", alias]
        for key, value in (env or {}).items():
            cmd += ["-e", f"{key}={value}"]
        for source, destination in mounts:
            resolved = Path(source).resolve()
            if not resolved.is_relative_to(temp.resolve()) or not resolved.is_file():
                raise AcceptanceError("native_mount_must_be_private_lab_file")
            cmd += ["--mount", f"type=bind,src={resolved},dst={destination},readonly"]
        for source, destination in writable_dirs:
            cmd += ['--mount', private_writable_mount(source, temp, destination)]
        # Register names before starting so even partially-created containers are removed.
        started.append(cname)
        log("start_" + name)
        docker(*cmd, image_id, *args)
        names[name] = cname
        if port:
            # Internal-only Docker networks intentionally have no published host ports.
            # On a native Linux runner the host reaches the isolated bridge IP directly.
            info = json.loads(docker("inspect", cname))[0]
            return native_origin(info, network, port)
        return None

    def start_core(port, token):
        env = {**os.environ, "PORT": str(port), "BIND_ADDRESS": "127.0.0.1",
               "VERDUGO_CONTROL_TOKEN": token, "VERDUGO_WORKSPACE": "native-acceptance",
               "VERDUGO_STATE_DB": str(temp / "growth.sqlite")}
        env.pop("VERDUGO_CONNECTIONS_JSON", None)
        env.pop("VERDUGO_ENDPOINTS_JSON", None)
        return subprocess.Popen(["node", str(ROOT / "lib/control-plane.mjs")], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_core():
        nonlocal core
        if core is not None:
            core.terminate()
            try:
                core.wait(timeout=10)
            except subprocess.TimeoutExpired:
                core.kill()
                core.wait(timeout=5)
            core = None

    try:
        refs = {}
        images = dict(IMAGES)
        if include_growthbook:
            images["growthbook"] = GROWTHBOOK_IMAGE
        if transport is not None:
            images.update(transport.images)
        for name, ref in images.items():
            log("pull_" + name)
            pull_image(docker, ref)
            image = json.loads(docker("image", "inspect", ref))[0]
            refs[name] = image["Id"]
            report["images"][name] = {"requested_ref": ref, "image_id": image["Id"],
                                     "repo_digests": image.get("RepoDigests", [])}
        # All service traffic is confined after image pulls. No outgoing SMTP is possible.
        docker("network", "create", "--internal", network)
        network_created = True
        db_password = "Vd!" + secrets.token_hex(24)
        admin_password = "Vd!" + secrets.token_hex(24)
        countly_key = secrets.token_hex(32)
        control_token = secrets.token_hex(32)
        basic = "Basic " + base64.b64encode(("vdadmin:" + admin_password).encode()).decode()
        REDACT.update((db_password, admin_password, countly_key, control_token, basic))
        for secret in REDACT:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print("::add-mask::" + secret, flush=True)

        log("start_databases")
        start("mysql", refs["mysql"], alias="mysql", env={
            "MYSQL_ROOT_PASSWORD": db_password, "MYSQL_DATABASE": "mautic",
            "MYSQL_USER": "mautic", "MYSQL_PASSWORD": db_password})
        start("mongo", refs["mongo"], alias="mongodb")
        wait_until(lambda: docker("exec", names["mysql"], "mysqladmin", "ping", "-h127.0.0.1",
                                  "-uroot", "-p" + db_password, timeout=10))
        wait_until(lambda: docker("exec", names["mongo"], "mongosh", "--quiet", "--eval",
                                  "if(!db.adminCommand({ping:1}).ok)quit(1);print('ready')", timeout=10))
        # Bootstrap only an ephemeral Countly API administrator, not application event records.
        seed = "db=db.getSiblingDB('countly');db.members.insertOne(" + json.dumps({
            "username": "vdadmin", "full_name": "Acceptance Only", "email": "ci@example.invalid",
            "password": secrets.token_hex(64), "api_key": countly_key,
            "global_admin": True, "admin_of": [], "user_of": [], "is_enabled": True
        }) + ");print('seeded')"
        docker("exec", names["mongo"], "mongosh", "--quiet", "--eval", seed)

        log("start_original_applications")
        mautic_url = start("mautic", refs["mautic"], port=80, env={
            "MAUTIC_DB_HOST": "mysql", "MAUTIC_DB_PORT": "3306", "MAUTIC_DB_USER": "mautic",
            "MAUTIC_DB_PASSWORD": db_password, "MAUTIC_DB_DATABASE": "mautic",
            "DOCKER_MAUTIC_ROLE": "mautic_web", "DOCKER_MAUTIC_LOAD_TEST_DATA": "false"})
        countly_env = {"COUNTLY_CONFIG_HOSTNAME": "countly.example.invalid",
                       "COUNTLY_CONFIG__MONGODB_HOST": "mongodb",
                       "COUNTLY_CONFIG_API_API_WORKERS": "1",
                       "COUNTLY_PLUGINS": "web,plugins,logger,systemlogs",
                       "NODE_OPTIONS": "--max-old-space-size=768 --no-node-snapshot"}
        countly_url = start("countly-api", refs["countly_api"], alias="countly.native.invalid", port=3001, env=countly_env)
        start("countly-frontend", refs["countly_frontend"], port=6001, env=countly_env)
        growthbook_url = None
        growthbook_state = None
        route_from_growthbook = None
        if include_growthbook:
            jwt_secret, encryption_key = secrets.token_hex(32), secrets.token_hex(32)
            mask_secret(jwt_secret)
            mask_secret(encryption_key)
            growthbook_url = start("growthbook", refs["growthbook"], port=3100, env={
                "MONGODB_URI": "mongodb://mongodb:27017/growthbook",
                "JWT_SECRET": jwt_secret, "ENCRYPTION_KEY": encryption_key,
                "APP_ORIGIN": "http://localhost:13000", "API_HOST": "http://localhost:13100",
                "DISABLE_TELEMETRY": "true", "EMAIL_ENABLED": "false"})

        log("initialize_mautic")
        wait_until(lambda: docker("exec", names["mautic"], "test", "-f", "/var/www/html/config/local.php", timeout=10) or True)
        install_output = docker("exec", "-u", "www-data", names["mautic"], "php", "/var/www/html/bin/console", "mautic:install",
               mautic_url, "--db_driver=pdo_mysql", "--db_host=mysql", "--db_port=3306",
               "--db_name=mautic", "--db_user=mautic", "--db_password=" + db_password,
               "--admin_username=vdadmin", "--admin_email=ci@example.invalid",
               "--admin_firstname=Native", "--admin_lastname=Acceptance",
               "--admin_password=" + admin_password, "--no-interaction", "--force", timeout=300)
        if "Install complete" not in install_output:
            raise AcceptanceError("mautic_installation_not_completed")
        patch = ("$f='/var/www/html/config/local.php';require $f;"
                 "$parameters['api_enabled']=true;$parameters['api_enable_basic_auth']=true;"
                 "$parameters['mailer_dsn']='null://null';"
                 "file_put_contents($f,'<?php'.PHP_EOL.'$parameters = '.var_export($parameters,true).';'.PHP_EOL);")
        docker("exec", "-u", "www-data", names["mautic"], "php", "-r", patch)
        docker("exec", "-u", "www-data", names["mautic"], "php", "/var/www/html/bin/console", "cache:clear", "--env=prod", timeout=180)
        auth = {"Authorization": basic}
        wait_until(lambda: request(mautic_url + "/api/contacts?limit=1", headers=auth))

        log("initialize_countly_app")
        countly_admin_query = urllib.parse.urlencode({"api_key": countly_key})
        wait_until(lambda: request(countly_url + "/o/apps/all?" + countly_admin_query) is not None)
        app = request(countly_url + "/i/apps/create", data={"api_key": countly_key,
            "args": json.dumps({"name": "Verdugo Native Acceptance", "timezone": "Africa/Abidjan", "type": "web"})}, form=True)
        if not isinstance(app.get("key"), str) or not isinstance(app.get("_id"), str):
            raise AcceptanceError("countly_app_creation_invalid")
        REDACT.add(app["key"])
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::add-mask::" + app["key"], flush=True)

        if transport is not None:
            log("initialize_authentic_rudderstack_transport")
            transport.install(start=start, docker=docker, refs=refs, temp=temp, network=network, report=report,
                              countly_origin="http://countly.native.invalid:3001",
                              countly_app={**app, "admin_key": countly_key})

        if include_growthbook:
            log("initialize_growthbook_native_route")
            growthbook_state = initialize_growthbook(growthbook_url, admin_password)
            route_from_growthbook = read_growthbook_route(growthbook_url, growthbook_state)
            report["checks"]["growthbook_feature_created_and_read_back"] = True

        log("verdugo_to_mautic_to_countly")
        import socket
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            core_port = sock.getsockname()[1]
        core_url = f"http://127.0.0.1:{core_port}"
        core_auth = {"Authorization": "Bearer " + control_token}
        core = start_core(core_port, control_token)
        wait_until(lambda: request(core_url + "/healthz"), seconds=30)
        lead_id, event_id = str(uuid.uuid4()), str(uuid.uuid4())
        email = "acceptance-" + uuid.uuid4().hex + "@example.invalid"
        event = {"id": event_id, "type": "lead.created", "lead_id": lead_id,
                 "data": {"name": "Synthetic Acceptance", "email": email,
                          "source": "native-ci", "analytics": True, "marketing": True}}
        request(core_url + "/v1/events", data=event, headers=core_auth)
        leads = request(core_url + "/v1/leads", headers=core_auth)["leads"]
        lead = next((x for x in leads if x["id"] == lead_id), None)
        if not lead or lead["email"] != email:
            raise AcceptanceError("verdugo_lead_readback_mismatch")
        report["checks"]["verdugo_persisted_lead"] = True
        # The outgoing data comes from the real Verdugo API readback, not a second fixture.
        contact_data = {"firstname": lead["name"], "email": lead["email"]}
        if include_growthbook:
            contact_data["tags"] = [route_from_growthbook]
        contact = request(mautic_url + "/api/contacts/new", headers=auth, data=contact_data)["contact"]
        contact_id = contact.get("id")
        if not isinstance(contact_id, int) or contact_id < 1:
            raise AcceptanceError("mautic_invalid_contact_id")

        def read_contact():
            value = request(mautic_url + f"/api/contacts/{contact_id}", headers=auth)["contact"]
            if value.get("id") != contact_id or value.get("fields", {}).get("all", {}).get("email") != email:
                return False
            if include_growthbook:
                contact_route(value, route_from_growthbook)
            return value

        persisted_contact = wait_until(read_contact, seconds=30)
        report["checks"]["mautic_created_and_read_back"] = True
        route_from_mautic = None
        if include_growthbook:
            route_from_mautic = contact_route(persisted_contact, route_from_growthbook)
            report["checks"]["growthbook_to_mautic_route"] = True
        event_key = "vd_native_" + hashlib.sha256(event_id.encode()).hexdigest()[:24]
        segmentation = {"source": "mautic", "contact": str(contact_id)}
        if include_growthbook:
            segmentation["route"] = route_from_mautic
        params = {"app_key": app["key"], "device_id": hashlib.sha256(lead_id.encode()).hexdigest(),
                  "events": json.dumps([{"key": event_key, "count": 1, "segmentation": segmentation}])}
        # The four-original profile has NO direct Countly ingestion fallback.
        ingested = (transport.deliver(params, event_id) if transport is not None
                    else request(countly_url + "/i", data=params, form=True))
        if ingested.get("result") != "Success":
            raise AcceptanceError("countly_ingestion_not_accepted")
        read_query = urllib.parse.urlencode({"api_key": countly_key, "app_id": app["_id"]})

        def read_countly():
            value = request(countly_url + "/o/analytics/events?" + read_query)
            rows = value.get("all")
            if not isinstance(rows, list):
                return False
            row = next((x for x in rows if x.get("_id") == event_key), None)
            return row is not None and row.get("c") == 1

        def read_countly_route():
            query = urllib.parse.urlencode({"api_key": countly_key, "app_id": app["_id"],
                "method": "events", "event": event_key, "segmentation": "route"})
            value = request(countly_url + "/o?" + query)
            routes = value.get("meta", {}).get("route", [])
            return isinstance(routes, list) and route_from_mautic in routes

        wait_until(read_countly, seconds=120)
        report["checks"]["countly_recorded_and_read_back"] = True
        if include_growthbook:
            wait_until(read_countly_route, seconds=120)
            report["checks"]["countly_route_read_back"] = True
        log("restart_and_verify_persistence")
        restart_names = [names["mautic"], names["countly-api"]]
        if include_growthbook:
            restart_names.append(names["growthbook"])
        docker("restart", *restart_names, timeout=180)
        if transport is not None:
            # Stop the consuming application before its database and restart dependencies first.
            # This retains all data and still requires a fresh end-to-end delivery afterwards.
            transport.restart()
        # Bridge addresses can change: never authenticate against a stale origin.
        NATIVE_ORIGINS.clear()
        mautic_url = native_origin(json.loads(docker("inspect", names["mautic"]))[0], network, 80)
        countly_url = native_origin(json.loads(docker("inspect", names["countly-api"]))[0], network, 3001)
        if include_growthbook:
            growthbook_url = native_origin(json.loads(docker("inspect", names["growthbook"]))[0], network, 3100)
        stop_core()
        core = start_core(core_port, control_token)
        wait_until(read_contact)
        report["checks"]["mautic_after_restart"] = True
        wait_until(read_countly)
        report["checks"]["countly_after_restart"] = True
        if include_growthbook:
            wait_until(lambda: read_growthbook_route(growthbook_url, growthbook_state) == route_from_growthbook)
            report["checks"]["growthbook_after_restart"] = True
            wait_until(read_countly_route)
            report["checks"]["countly_route_after_restart"] = True
        wait_until(lambda: request(core_url + "/healthz"), seconds=30)
        replay = request(core_url + "/v1/events", data=event, headers=core_auth)
        persisted = request(core_url + "/v1/leads", headers=core_auth)["leads"]
        if replay.get("replayed") is not True or len([x for x in persisted if x["id"] == lead_id]) != 1:
            raise AcceptanceError("verdugo_restart_replay_failed")
        report["checks"]["verdugo_after_restart"] = True
        if transport is not None:
            log("verify_rudderstack_delivery_after_restart")
            transport.verify_after_restart(countly_origin=countly_url, route=route_from_mautic)
        require_all_checks(report)
        report["proof"] = {"canonical_event_sha256": hashlib.sha256(event_id.encode()).hexdigest(),
                           "mautic_contact_id": contact_id, "countly_event_count": 1}
        if include_growthbook:
            report["proof"].update(growthbook_feature_id=growthbook_state["feature_id"],
                                   route_read_back_in_all_three=route_from_mautic)
    except Exception:
        report["failed_stage"] = stage
        report["containers_at_failure"] = {}
        for name in started:
            try:
                info = json.loads(docker("inspect", name))[0]["State"]
                report["containers_at_failure"][name.split(prefix + "-")[-1]] = {
                    "status": info.get("Status"), "exit_code": info.get("ExitCode"),
                    "oom_killed": info.get("OOMKilled"),
                }
                logs = command(["docker", "logs", "--tail", "40", name], timeout=10)
                for secret in sorted(REDACT, key=len, reverse=True):
                    logs = logs.replace(secret, "[REDACTED]")
                print("NATIVE_CONTAINER_LOG=" + name + "\n" + logs[-4000:], flush=True)
            except Exception:
                pass
        raise
    finally:
        stop_core()
        cleanup_ok = True
        for name in reversed(started):
            try:
                docker("rm", "-f", "-v", name, timeout=30)
            except AcceptanceError:
                cleanup_ok = False
        if network_created:
            try:
                docker("network", "rm", network, timeout=30)
            except AcceptanceError:
                cleanup_ok = False
        private.cleanup()
        NATIVE_ORIGINS.clear()
        REDACT.clear()
        report["resources_removed"] = cleanup_ok
        if report["status"] == "passed" and not cleanup_ok:
            report["status"] = "cleanup_failed"
            raise AcceptanceError("native_resource_cleanup_failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="native-acceptance.json")
    parser.add_argument("--include-growthbook", action="store_true",
                        help="Require the real GrowthBook -> Mautic -> Countly route flow")
    parser.add_argument("--include-rudderstack", action="store_true",
                        help="Require authentic RudderStack delivery into Countly; implies GrowthBook")
    args = parser.parse_args()
    args.include_growthbook = args.include_growthbook or args.include_rudderstack
    report = evidence_base(args.include_growthbook, args.include_rudderstack)
    transport = None
    if args.include_rudderstack:
        import sys
        from native_rudderstack import RudderStackTransport
        transport = RudderStackTransport(sys.modules[__name__])
    try:
        run_acceptance(report, include_growthbook=args.include_growthbook, transport=transport)
        code = 0
    except AcceptanceError as exc:
        report.update(status="blocked_or_failed", error=str(exc))
        code = 2
    except Exception as exc:
        report.update(status="failed", error="unexpected_" + type(exc).__name__)
        code = 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
