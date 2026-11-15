"""Pinned, read-only upstream GitHub source evidence for the 322 catalogue entries.

A source commit is not a deployed service, a compatible API, a license grant,
or a working integration. No remote source code is imported or executed here.
"""
import json
import re
from pathlib import Path

from .adapters import SPECS
from .local_runtime import SPECS as LOCAL_SPECS
from .catalog import catalog
from .common import VerdugoError
from . import license_policy

PARTS = Path(__file__).resolve().parents[1] / "sources" / "parts"
SHA = re.compile(r"^[0-9a-f]{40}$")
REGISTERED = 322
PART_NAMES = [f"{n:02d}.json" for n in range(1, (REGISTERED + 9) // 10 + 1)]


def read_sources(directory=None):
    """Fail closed on missing, extra, altered, or unpinned catalogue entries."""
    directory = Path(directory) if directory is not None else PARTS
    try:
        names = sorted(p.name for p in directory.iterdir() if p.suffix == ".json")
    except OSError as exc:
        raise VerdugoError("Source evidence directory is unreadable") from exc
    if names != PART_NAMES:
        raise VerdugoError("Source evidence requires exactly 33 numbered JSON parts")
    approved = catalog()
    if len(approved) != REGISTERED:
        raise VerdugoError("Approved catalogue does not contain exactly 322 projects")
    records = []
    for part_number, name in enumerate(PART_NAMES):
        path = directory / name
        try:
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
                raise VerdugoError("Source evidence part is not a bounded regular file")
            block = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise VerdugoError("Source evidence part is unreadable or invalid JSON") from exc
        size = min(10, REGISTERED - part_number * 10)
        if not isinstance(block, list) or len(block) != size:
            raise VerdugoError("Source evidence part must contain exactly 10 records (the last part holds the rest)")
        for index, row in enumerate(block):
            expected = approved[part_number * 10 + index]
            if not isinstance(row, dict):
                raise VerdugoError("Source evidence record must be an object")
            if (type(row.get("number")) is not int or
                    row["number"] != expected["number"] or
                    row.get("id") != expected["id"] or
                    row.get("repository") != expected["repository"]):
                raise VerdugoError("Source evidence does not match the approved catalogue")
            if row.get("source_status") != "pinned" or not isinstance(row.get("commit_sha"), str) or not SHA.fullmatch(row["commit_sha"]):
                raise VerdugoError("Source evidence requires a 40-hex commit pin")
            if row.get("license_review") != "pending":
                raise VerdugoError("License review cannot be asserted by source pinning")
            records.append(row)
    if len({r["id"] for r in records}) != REGISTERED or len({r["repository"].casefold() for r in records}) != REGISTERED:
        raise VerdugoError("Source evidence contains duplicate projects")
    return records


def report(project_id=None):
    """Describe source and adapter readiness without asserting runtime success."""
    rows = read_sources()
    if project_id is not None:
        if not isinstance(project_id, str):
            raise VerdugoError("project_id must be a registered source ID")
        row = next((r for r in rows if r["id"] == project_id), None)
        if row is None:
            raise VerdugoError("Unknown registered source ID")
        return {
            "project_id": row["id"],
            "repository": row["repository"],
            "source_commit_sha": row["commit_sha"],
            "source_status": "pinned",
            "source_url": "https://github.com/" + row["repository"] + "/tree/" + row["commit_sha"],
            "license_review": "pending",
            "license_detected": license_policy.record(row["id"])["spdx"],
            "license_policy": license_policy.record(row["id"])["policy"],
            "http_api_recipe_available": row["id"] in SPECS,
            "local_recipe_available": row["id"] in LOCAL_SPECS,
            "implemented_local_actions": [LOCAL_SPECS[row["id"]][0]] if row["id"] in LOCAL_SPECS else [],
            "implemented_http_actions": sorted(SPECS.get(row["id"], {})),
            "live_verified": False,
            "ready_for_production": False,
            "external_calls_made": False,
        }
    return {
        "name": "Verdugo Digital / Nexus GitHub source evidence",
        "registered": len(rows),
        "source_pinned": sum(r["source_status"] == "pinned" for r in rows),
        "source_not_pinned": 0,
        "license_review_pending": sum(r["license_review"] == "pending" for r in rows),
        "license_policy_allowed": license_policy.summary()["allowed"],
        "license_policy_excluded": len(license_policy.EXCLUDED),
        "http_adapters_implemented": sum(r["id"] in SPECS for r in rows),
        "http_actions_implemented": sum(len(v) for v in SPECS.values()),
        "without_http_adapter": sum(r["id"] not in SPECS for r in rows),
        "local_adapters_implemented": len(LOCAL_SPECS),
        "without_any_adapter": sum(r["id"] not in SPECS and r["id"] not in LOCAL_SPECS for r in rows),
        "live_verified": 0,
        "production_ready": 0,
        "external_calls_made": False,
        "note": "Pinned GitHub commits are source references, not vendored code or operational integrations. All upstream licenses and real provider contracts remain unapproved.",
    }
