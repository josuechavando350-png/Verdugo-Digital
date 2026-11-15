"""Original Python Playwright request-context state; no browser or HTTP requests."""
import hashlib
import json
import os
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

VERSION = '1.65.1.dev12+g86a5f5a81010b1dbd155263e99782442b61d0cb2'
SPECS = {'playwright-python': ('cookies.check', 'playwright', VERSION)}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-browserstate666.json'
GUARD = Path(__file__).with_name('_offline_node_guard.cjs')


def home():
    return checked(Path(runtime_profile.interpreter('playwright-python')).parent.parent, directory=True)


def verify_artifacts(root, record):
    digest = hashlib.sha256(str(root).encode() + CONTRACT.read_bytes())
    for name, expected in record['installed_artifacts'].items():
        raw = checked(root / name, budget=256 * 1024 * 1024).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise VerdugoError('Original Python Playwright source or driver artifact changed')
        digest.update(bytes.fromhex(actual))
    digest.update(checked(root / 'bin/python', budget=64 * 1024 * 1024).read_bytes())
    digest.update(checked(root / 'pyvenv.cfg', budget=16384).read_bytes())
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        record = json.loads(CONTRACT.read_text())
        binding = verify_artifacts(home(), record)
        versions = runtime_profile.versions(service, ['playwright', 'greenlet'])
        if versions != {'playwright': version, 'greenlet': record['greenlet_version']}:
            raise VerdugoError('Python Playwright distribution versions changed')
        present = True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        binding = None
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed request-state operation')
    fields(p, ('dataset', 'cookies'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic cookie flags are supported')
    if not isinstance(p['cookies'], list) or not 1 <= len(p['cookies']) <= 16:
        raise VerdugoError('One to sixteen synthetic cookie rows required')
    for row in p['cookies']:
        fields(row, ('slot', 'secure', 'http_only', 'same_site', 'lifetime'))
        integer(row['slot'], 0, 7)
        if type(row['secure']) is not bool or type(row['http_only']) is not bool:
            raise VerdugoError('Explicit cookie booleans required')
        if row['same_site'] not in ('Strict', 'Lax', 'None') or row['lifetime'] not in ('session', 'expired'):
            raise VerdugoError('Only fixed SameSite and lifetime enums supported')


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original Python Playwright build unavailable')
    # Set by the fixed Engine worker, never by a tool payload. The Node guard
    # blocks network/process APIs; CI additionally removes OS networking.
    if os.environ.get('NODE_OPTIONS') != '--require ' + str(GUARD):
        raise VerdugoError('Fixed Node offline guard is required')
    from playwright.sync_api import sync_playwright

    cookies = [{'name': 'synthetic_' + str(r['slot']), 'value': 'fixed-demo-value',
                'domain': 'example.invalid', 'path': '/',
                'expires': -1 if r['lifetime'] == 'session' else 1,
                'secure': r['secure'], 'httpOnly': r['http_only'], 'sameSite': r['same_site']}
               for r in p['cookies']]
    with sync_playwright() as sdk:
        first = sdk.request.new_context(storage_state={'cookies': cookies, 'origins': []}, timeout=1000)
        try:
            state = first.storage_state()
            second = sdk.request.new_context(timeout=1000)
            try:
                isolated = second.storage_state()
                if isolated['cookies'] or isolated['origins']:
                    raise VerdugoError('Original request contexts leaked state')
            finally:
                second.dispose()
        finally:
            first.dispose()
    retained = state['cookies']
    if state['origins'] or len(retained) > len(cookies):
        raise VerdugoError('Unexpected original cookie state')
    record = json.loads(CONTRACT.read_text())
    # These counts describe the request-context cookie jar, not Chromium cookie
    # enforcement or an independent browser-security certification.
    return {'submitted_cookie_count': len(cookies), 'retained_cookie_count': len(retained),
        'discarded_or_replaced_count': len(cookies) - len(retained),
        'secure_cookie_count': sum(c['secure'] for c in retained),
        'http_only_cookie_count': sum(c['httpOnly'] for c in retained),
        'same_site_counts': {kind: sum(c['sameSite'] == kind for c in retained)
                             for kind in ('Strict', 'Lax', 'None')},
        'nonsecure_same_site_none_count': sum(not c['secure'] and c['sameSite'] == 'None' for c in retained),
        'fresh_context_isolated': True, 'sdk_contexts_disposed': True,
        'http_requests_made': 0, 'browsers_launched': 0, 'raw_cookies_persisted': False,
        'original_sdk': service, 'sdk_version': VERSION, 'source_commit': record['commit'],
        'driver_source_commit': record['driver']['commit'],
        'source_python_files_verified': record['source_python_files_verified'],
        'compiled_driver_artifacts_verified': True, 'browser_security_certified': False,
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0}
