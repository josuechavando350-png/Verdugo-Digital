"""Fail-closed collection-shape verification for bounded provider reads.

Only these provider operations are covered. Schema matching does not verify
identity, completeness, authorization scope, or production readiness.
"""
from .common import VerdugoError

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


def check(service, operation, response):
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
