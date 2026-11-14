"""Fail-closed collection-shape verification for bounded provider reads.

Only these provider operations are covered. Schema matching does not verify
identity, completeness, authorization scope, or production readiness.
"""
from .common import VerdugoError
from . import marketing_reads, service_reads

SCHEMAS = {
    "novu": ("data",),
    "superset": ("result",),
    "supabase": (),
    "coolify": (),
    "keycloak": (),
    "unleash": ("projects",),
    "medusa": ("products",),
    "openfga": ("stores",),
}

# v0.12: summarize sensitive provider payloads rather than retaining data
# such as signing recipients, automation payloads or connection tags.
# These are bounded *first-page observations*, never complete exports.
METADATA_SCHEMAS = {
    "airbyte": ("workspaces.list", ("data",)),
    "infisical": ("projects.list", ("projects",)),
    "openmeter": ("meters.list", ()),
    "nango": ("connections.list", ("connections",)),
    "trigger": ("runs.list", ("data",)),
    "documenso": ("envelopes.list", ("data",)),
}

DOCUMENT_STATUSES = frozenset(("DRAFT", "PENDING", "COMPLETED",
                               "REJECTED", "CANCELLED"))
TRIGGER_STATUSES = frozenset(("QUEUED", "EXECUTING", "COMPLETED",
                             "FAILED", "CANCELED", "CANCELLED",
                             "WAITING", "DELAYED", "CRASHED",
                             "SYSTEM_FAILURE", "INTERRUPTED",
                             "PENDING", "TIMED_OUT"))


def _metadata_summary(service, operation, response):
    if service == "growthbook":
        if operation != "settings.read" or not isinstance(response, dict) or not isinstance(response.get("settings"), dict):
            raise VerdugoError("GrowthBook settings schema mismatch")
        return {
            "service": service, "operation": operation,
            "settings_response_observed": True,
            "raw_provider_payload_retained": False,
            "scope": "bounded_read_only", "live_verified": False,
        }
    expected_operation, path = METADATA_SCHEMAS[service]
    if operation != expected_operation:
        raise VerdugoError("Provider read operation mismatch")
    rows = response
    for key in path:
        if not isinstance(rows, dict) or key not in rows:
            raise VerdugoError("Provider collection schema mismatch")
        rows = rows[key]
    if not isinstance(rows, list) or len(rows) > 1000 or not all(isinstance(row, dict) for row in rows):
        raise VerdugoError("Provider read requires a bounded list of objects")
    status_counts = {}
    if service in ("trigger", "documenso"):
        allowed = TRIGGER_STATUSES if service == "trigger" else DOCUMENT_STATUSES
        for row in rows:
            status = row.get("status")
            label = status if type(status) is str and status in allowed else "OTHER"
            status_counts[label] = status_counts.get(label, 0) + 1
    return {
        "service": service, "operation": operation,
        "records_in_response": len(rows),
        "status_counts": status_counts,
        "scope": "one_provider_response_not_a_complete_export",
        "raw_provider_payload_retained": False,
        "live_verified": False,
    }


def check(service, operation, response, request=None):
    if service in marketing_reads.SPECS:
        return marketing_reads.check(service, operation, response, request)
    if service in service_reads.SPECS:
        return service_reads.check(service, operation, response, request)
    if service in METADATA_SCHEMAS or service == "growthbook":
        return _metadata_summary(service, operation, response)
    if service not in SCHEMAS:
        return response
    if not operation.endswith(".list"):
        raise VerdugoError("Unknown read contract operation")
    path = SCHEMAS[service]
    rows = response
    for key in path:
        if not isinstance(rows, dict) or key not in rows:
            raise VerdugoError("Provider response does not match reviewed collection shape")
        rows = rows[key]
    if not isinstance(rows, list) or len(rows) > 1000:
        raise VerdugoError("Provider response must contain a bounded list")
    if not all(isinstance(row, dict) for row in rows):
        raise VerdugoError("Provider collection entries must be objects")
    # This is a schema acceptance boundary, NOT a claim that rows are verified
    # customers, legitimate campaigns, billable receipts or complete exports.
    return response
