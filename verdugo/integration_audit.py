"""Reconcile the 666 target with identities, implemented code and scoped reviews.

This is an offline evidence index. A root license, adapter, successful fixture or
preparation review never establishes approval of the full distributable product.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from .common import VerdugoError
from . import connections, license_policy
from .registry666 import read_registry

ROOT = Path(__file__).resolve().parents[1]
# Ordered 39 IDs implemented at 4dbd055, joined with LF and no trailing LF.
# Future adapters must never be substituted into this historical baseline.
BASELINE_IDS_SHA256 = 'fd397fe906a3bfd6d00311f032e07ecc40e2b771763bf20e944497202460ce67'
REVIEWS = (
    'contracts-executive-blockers666.json', 'review-runtime-next666.json',
    'review-memory-next666.json', 'review-logic-next666.json',
    'review-reasoning-next666.json', 'review-end80-next666.json', 'review-numeric-next666.json',
    'review-license-decision666.json',
    'review-candle-dependencies666.json',
    'review-clingo-dependencies666.json',
)


def read_json(path, limit=4*1024*1024):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
            raise VerdugoError('Integration evidence must be a bounded regular file')
        raw = path.read_bytes()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise VerdugoError('Integration evidence is unreadable') from exc


def continuation_batches(resume, queue, implemented):
    """Keep A/B membership fixed while deriving completion from actual code."""
    rebatch = resume.get('rebatch')
    if (resume.get('schema') != 'verdugo.resume666.v2' or not isinstance(rebatch, dict)
            or rebatch.get('baseline_commit') != '4dbd05535e35208a1f9fb8e92a1d3da433b76c34'
            or rebatch.get('outside_batches_pending') != ['meta-ads']):
        raise VerdugoError('Invalid A/B continuation baseline')
    previous, groups = rebatch.get('previously_implemented'), rebatch.get('batches')
    if (not isinstance(previous, list) or len(previous) != 39
            or any(not isinstance(sid, str) for sid in previous)
            or hashlib.sha256('\n'.join(previous).encode()).hexdigest() != BASELINE_IDS_SHA256
            or len(set(previous)) != 39 or not set(previous) <= implemented
            or not set(resume['previously_implemented']) <= set(previous)
            or previous != [r['id'] for r in queue if r['id'] in previous]
            or any(r['batch'] != 1 for r in queue if r['id'] in previous)
            or not isinstance(groups, list) or len(groups) != 2):
        raise VerdugoError('Invalid A/B previously implemented identities')
    expected = [sid for group in resume['subbatches'] for sid in group['ids']
                if sid not in previous] + [r['id'] for r in queue if r['batch'] == 2]
    if len(expected) != 327 or len(set(expected)) != 327:
        raise VerdugoError('Invalid A/B pending sequence')
    batches, offset = [], 0
    for group, name, size in zip(groups, ('A', 'B'), (164, 163)):
        if (not isinstance(group, dict) or group.get('name') != name
                or type(group.get('size')) is not int or group['size'] != size
                or group.get('ids') != expected[offset:offset+size]):
            raise VerdugoError('A/B continuation changes membership, size or order')
        done = [sid for sid in group['ids'] if sid in implemented]
        batches.append({'name': name, 'size': size, 'implemented': len(done),
                        'pending': size-len(done), 'implemented_ids': done})
        offset += size
    return batches


def summary():
    registry = read_registry()
    policy = license_policy.read_policy()
    table, _ = connections.read_map()
    states = {sid: connections.state(sid) for sid in table}
    implemented = {sid for sid, state in states.items() if state == 'conectado'}
    new = {r['id'] for r in registry['records']}
    queue = registry['work_queue']
    resume, _ = read_json(ROOT/'sources/resume-666.json')
    previous = resume.get('previously_implemented')
    groups = resume.get('subbatches')
    if not isinstance(previous, list) or not isinstance(groups, list) or len(groups) != 2:
        raise VerdugoError('Invalid continuation membership')
    membership = list(previous)
    subbatches = []
    for index, (group, size) in enumerate(zip(groups, (80, 81)), 1):
        if (not isinstance(group, dict) or group.get('number') != index or group.get('size') != size
                or not isinstance(group.get('ids'), list) or len(group['ids']) != size
                or any(not isinstance(s, str) for s in group['ids'])):
            raise VerdugoError('Invalid continuation batch')
        membership.extend(group['ids'])
        done = [sid for sid in group['ids'] if sid in implemented]
        subbatches.append({'number': index, 'size': size, 'implemented': len(done),
                          'pending': size-len(done), 'implemented_ids': done})
    if (any(not isinstance(s, str) for s in previous) or len(membership) != len(set(membership))
            or set(membership) != {r['id'] for r in queue if r['batch'] == 1}):
        raise VerdugoError('Continuation double-counts or loses an original batch identity')
    # The historical 80/81 groups retain their original relative queue order.
    historical_order = [sid for group in groups for sid in group['ids']]
    if historical_order != [r['id'] for r in queue if r['batch'] == 1 and r['id'] not in previous]:
        raise VerdugoError('Historical continuation order differs from work_queue')
    batches = continuation_batches(resume, queue, implemented)
    findings = []
    for name in REVIEWS:
        document, digest = read_json(ROOT/'sources'/name)
        rows = document.get('records') if isinstance(document, dict) else None
        if not isinstance(rows, list):
            raise VerdugoError('Invalid preparation review')
        for row in rows:
            if not isinstance(row, dict) or row.get('id') not in new:
                raise VerdugoError('Review names an unregistered identity')
            status = row.get('status', row.get('state'))
            if not isinstance(status, str) or not status or len(status) > 100:
                raise VerdugoError('Review status is missing')
            findings.append({'id': row['id'], 'review_status': status,
                             'adapter_implemented': row['id'] in implemented,
                             'evidence_path': 'sources/'+name, 'evidence_sha256': digest})
    # Preserve the exact scope of the inherited certifi finding. Confirm it is
    # still present in each named constraints file instead of reusing a stale count.
    review, digest = read_json(ROOT/'sources/review-runtime-next666.json')
    existing = review['existing_profile_review_needed']
    impacted = []
    for name in existing['constraint_files']:
        if not isinstance(name, str) or not name.startswith('requirements/') or '..' in name.split('/'):
            raise VerdugoError('Invalid reviewed profile path')
        path = ROOT/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
            raise VerdugoError('Reviewed constraints unavailable')
        raw = path.read_bytes()
        if existing['dependency']+'=='+existing['version'] in raw.decode().splitlines():
            impacted.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest()})
    counts = Counter(states.values())
    allowed = sum(r['policy'] != 'excluido' for r in policy.values())
    return {
        'target': 666, 'registered_identities': len(table), 'unique_github_identities': len(table),
        'identity_check': 'numeric_GitHub_identity_and_canonical_name',
        'duplicate_identities': 0, 'historical_aliases_removed': 5,
        'semantic_overlap_review': 'not_certified_by_identity_check',
        'root_policy_allowed': allowed, 'root_policy_excluded': counts['excluido'],
        'implemented_adapters': counts['conectado'], 'construction_components': counts['pieza_de_construccion'],
        'pending_adapters': counts['pendiente'], 'new_implemented': len(new & implemented),
        'original_batches': [{'number': n, 'size': 183,
            'implemented': sum(r['id'] in implemented for r in queue if r['batch'] == n),
            'pending': sum(r['id'] not in implemented for r in queue if r['batch'] == n)} for n in (1, 2)],
        'subbatches': subbatches, 'batches': batches,
        'implemented_before_rebatch': 39,
        'outside_batches_pending': ['meta-ads'] if states['meta-ads'] == 'pendiente' else [],
        'review_findings': findings,
        'existing_profile_review': {'dependency': existing['dependency'], 'version': existing['version'],
            'review_status': 'dependency_license_scope_unresolved', 'profiles': impacted,
            'evidence_path': 'sources/review-runtime-next666.json', 'evidence_sha256': digest},
        'all_666_integrated': False, 'distribution_license_closure_verified': False,
        'live_verified': 0, 'production_certified': False,
        'note': 'Root permission, adapter implementation, dependency closure and deployment are separate. '
                'Preparation reviews and synthetic tests do not complete an integration. '
                'Distinct repositories can still offer overlapping functions.',
    }
