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
import contextlib
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
# Only addresses discovered from this run's private Docker network are authorized.
NATIVE_ORIGINS: set[str] = set()
REDACT: set[str] = set()


class AcceptanceError(RuntimeError):
    """Only non-sensitive, bounded error codes are exposed in public evidence."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcceptanceError("redirect_refused")


def request(url: str, *, data=None, headers=None, form=False):
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
        detail = p.stderr[-1800:]
        for secret in sorted(REDACT, key=len, reverse=True):
            detail = detail.replace(secret, "[REDACTED]")
        # This is a disposable synthetic-only laboratory. Do not print full commands.
        print("NATIVE_COMMAND_ERROR=" + detail, flush=True)
        raise AcceptanceError("command_failed_" + args[0] + "_" + (args[1] if len(args)>1 else "") + "_" + str(p.returncode))
    return p.stdout.strip()


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


def evidence_base():
    return {
        "schema_version": 1,
        "scope": "ephemeral_mautic_countly_native_api_acceptance",
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
    if any(report["checks"].get(key) is not True for key in needed):
        raise AcceptanceError("incomplete_native_acceptance")
    report["verified_originals"] = ["mautic", "countly"]
    report["status"] = "passed"


def run_acceptance(report):
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

    def start(name, image_id, *, env=None, alias=None, port=None, args=()):
        cname = prefix + "-" + name
        cmd = ["run", "-d", "--name", cname, "--network", network,
               "--label", "verdugo.acceptance=" + prefix, "--memory", "1536m"]
        if alias:
            cmd += ["--network-alias", alias]
        for key, value in (env or {}).items():
            cmd += ["-e", f"{key}={value}"]
        # Register names before starting so even partially-created containers are removed.
        started.append(cname)
        log("start_" + name)
        docker(*cmd, image_id, *args)
        names[name] = cname
        if port:
            # Internal-only Docker networks intentionally have no published host ports.
            # On a native Linux runner the host reaches the isolated bridge IP directly.
            info = json.loads(docker("inspect", cname))[0]
            networks = info["NetworkSettings"]["Networks"]
            if set(networks) != {network}:
                raise AcceptanceError("unexpected_container_network")
            address = networks[network]["IPAddress"]
            if not ipaddress.ip_address(address).is_private:
                raise AcceptanceError("container_address_not_private")
            origin = f"http://{address}:{port}"
            NATIVE_ORIGINS.add(origin)
            return origin
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
        for name, ref in IMAGES.items():
            log("pull_" + name)
            docker("pull", ref, timeout=300)
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
        countly_url = start("countly-api", refs["countly_api"], port=3001, env=countly_env)
        start("countly-frontend", refs["countly_frontend"], port=6001, env=countly_env)

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
        contact = request(mautic_url + "/api/contacts/new", headers=auth,
                          data={"firstname": lead["name"], "email": lead["email"]})["contact"]
        contact_id = contact.get("id")
        if not isinstance(contact_id, int) or contact_id < 1:
            raise AcceptanceError("mautic_invalid_contact_id")

        def read_contact():
            value = request(mautic_url + f"/api/contacts/{contact_id}", headers=auth)["contact"]
            return value.get("id") == contact_id and value.get("fields", {}).get("all", {}).get("email") == email

        wait_until(read_contact, seconds=30)
        report["checks"]["mautic_created_and_read_back"] = True
        event_key = "vd_native_" + hashlib.sha256(event_id.encode()).hexdigest()[:24]
        params = {"app_key": app["key"], "device_id": hashlib.sha256(lead_id.encode()).hexdigest(),
                  "events": json.dumps([{"key": event_key, "count": 1,
                      "segmentation": {"source": "mautic", "contact": str(contact_id)}}])}
        ingested = request(countly_url + "/i", data=params, form=True)
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

        wait_until(read_countly, seconds=120)
        report["checks"]["countly_recorded_and_read_back"] = True
        log("restart_and_verify_persistence")
        docker("restart", names["mautic"], names["countly-api"], timeout=90)
        stop_core()
        core = start_core(core_port, control_token)
        wait_until(read_contact)
        report["checks"]["mautic_after_restart"] = True
        wait_until(read_countly)
        report["checks"]["countly_after_restart"] = True
        wait_until(lambda: request(core_url + "/healthz"), seconds=30)
        replay = request(core_url + "/v1/events", data=event, headers=core_auth)
        persisted = request(core_url + "/v1/leads", headers=core_auth)["leads"]
        if replay.get("replayed") is not True or len([x for x in persisted if x["id"] == lead_id]) != 1:
            raise AcceptanceError("verdugo_restart_replay_failed")
        report["checks"]["verdugo_after_restart"] = True
        require_all_checks(report)
        report["proof"] = {"canonical_event_sha256": hashlib.sha256(event_id.encode()).hexdigest(),
                           "mautic_contact_id": contact_id, "countly_event_count": 1}
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
    args = parser.parse_args()
    report = evidence_base()
    try:
        run_acceptance(report)
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
