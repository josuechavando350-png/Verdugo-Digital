"""Offline identity and license evidence for the 366-project expansion.

No upstream code is loaded, no model weights are approved and no integration
state is inferred from this registration. All evidence is bounded and hashed.
"""
import hashlib
import json
import re
from pathlib import Path

from .catalog import catalog
from .common import VerdugoError

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'sources' / 'registry-666.json'
TEXTS = ROOT / 'sources' / 'license-texts'
SHA = re.compile(r'^[0-9a-f]{40}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')
BASE_COUNT = 322
REGISTERED = 688
ALLOWED = 666


def _regular(path, maximum):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
            raise VerdugoError('Registry evidence must be a bounded regular file')
        return path.read_bytes()
    except OSError as exc:
        raise VerdugoError('Registry evidence is unreadable') from exc


def _license(item, repository, commit, texts):
    if not isinstance(item, dict):
        raise VerdugoError('Invalid license evidence')
    sha, blob, path = item.get('sha256'), item.get('blob_sha'), item.get('path')
    if not isinstance(sha, str) or not SHA256.fullmatch(sha) or \
            not isinstance(blob, str) or not SHA.fullmatch(blob) or \
            not isinstance(path, str) or not path or path.startswith('/') or \
            '\\' in path or any(p in ('', '.', '..') for p in path.split('/')):
        raise VerdugoError('Invalid license path or digest')
    if item.get('repository') != repository or item.get('commit_sha') != commit or \
            item.get('local_path') != f'sources/license-texts/{sha}.txt' or \
            item.get('source_url') != f'https://github.com/{repository}/blob/{commit}/{path}':
        raise VerdugoError('License evidence is not bound to its source')
    data = _regular(texts / (sha + '.txt'), 65536)
    if hashlib.sha256(data).hexdigest() != sha or \
            hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != blob:
        raise VerdugoError('Original license bytes do not match the recorded hashes')


def read_registry(path=None, texts=None):
    path = Path(path) if path is not None else PATH
    texts = Path(texts) if texts is not None else TEXTS
    if texts.is_symlink() or not texts.is_dir():
        raise VerdugoError('License text directory must be a real directory')
    try:
        document = json.loads(_regular(path, 1048576))
    except (UnicodeError, ValueError) as exc:
        raise VerdugoError('Invalid registry JSON') from exc
    if not isinstance(document, dict) or document.get('schema_version') != 1 or \
            (document.get('registered'), document.get('allowed'), document.get('new_entries')) != (688, 666, 366):
        raise VerdugoError('Invalid expansion counts')
    rows, identities, queue = (document.get(k) for k in ('records', 'base_identities', 'work_queue'))
    if not isinstance(rows, list) or len(rows) != 366 or \
            not isinstance(identities, list) or len(identities) != BASE_COUNT or \
            not isinstance(queue, list) or len(queue) != 366:
        raise VerdugoError('Registry must cover the base and both 183-project batches')
    approved = catalog()
    if len(approved) != REGISTERED:
        raise VerdugoError('Unexpected catalogue size')
    expected_numbers = {r['id']: r['number'] for r in approved}
    new_ids = {r.get('id') for r in rows if isinstance(r, dict)}
    github_ids, names = set(), set()
    for actual, expected in zip(identities + rows, approved):
        if not isinstance(actual, dict) or actual.get('id') != expected['id'] or \
                actual.get('repository') != expected['repository']:
            raise VerdugoError('Registry identity differs from the catalogue')
        gid = actual.get('github_id', actual.get('repository_id'))
        name = actual.get('canonical', actual.get('repository'))
        if type(gid) is not int or gid < 1 or gid in github_ids or \
                not isinstance(name, str) or name.casefold() in names:
            raise VerdugoError('Duplicate or invalid canonical GitHub identity')
        github_ids.add(gid)
        names.add(name.casefold())
    for row in rows:
        if row.get('number') != expected_numbers[row['id']] or \
                not isinstance(row.get('commit_sha'), str) or not SHA.fullmatch(row['commit_sha']):
            raise VerdugoError('Invalid registry commit or position')
        evidence = row.get('license_evidence')
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 4:
            raise VerdugoError('Every new entry needs original license evidence')
        for item in evidence:
            _license(item, row['repository'], row['commit_sha'], texts)
    seen = set()
    for position, row in enumerate(queue, 1):
        if not isinstance(row, dict) or row.get('id') not in new_ids or \
                row['id'] in seen or row.get('position') != position or \
                row.get('batch') != (1 if position <= 183 else 2) or \
                row.get('batch_position') != (position - 1) % 183 + 1 or \
                type(row.get('phase')) is not int or not 1 <= row['phase'] <= 7 or \
                row.get('status') != 'pending_contract' or row.get('live_verified') is not False:
            raise VerdugoError('Work queue must be ordered, pending and duplicate-free')
        seen.add(row['id'])
    if [r['phase'] for r in queue] != sorted(r['phase'] for r in queue):
        raise VerdugoError('Work queue violates construction order')
    corrections = document.get('corrections')
    if not isinstance(corrections, list) or len(corrections) != 6:
        raise VerdugoError('The six proposal corrections must remain traceable')
    corrected = set()
    base_by_id = {r['github_id']: r['id'] for r in identities}
    for correction in corrections:
        if not isinstance(correction, dict) or not isinstance(correction.get('license_evidence'), list) or \
                not 1 <= len(correction['license_evidence']) <= 4:
            raise VerdugoError('Invalid proposal correction')
        matches = [r for r in rows if r['proposed_repository'] == correction.get('proposed_repository')]
        if len(matches) != 1 or matches[0]['repository'] != correction.get('replacement_repository') or \
                (matches[0]['origin'], matches[0]['proposal_number']) != \
                (correction.get('origin'), correction.get('proposal_number')) or \
                matches[0]['id'] in corrected:
            raise VerdugoError('Correction does not identify its replacement')
        corrected.add(matches[0]['id'])
        if correction.get('reason') == 'duplicate_repository_identity':
            if correction.get('existing_id') is None or base_by_id.get(correction.get('repository_id')) != correction['existing_id']:
                raise VerdugoError('Duplicate correction needs the existing identity')
        elif correction.get('reason') != 'restricted_license' or correction.get('existing_id') is not None:
            raise VerdugoError('Invalid correction reason')
        for item in correction['license_evidence']:
            _license(item, correction.get('canonical_repository'), correction.get('commit_sha'), texts)
    return document
