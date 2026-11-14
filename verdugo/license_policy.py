"""v0.14 license policy: only permissive upstream licenses may be operated.

The evidence in sources/licenses.json comes from reading each pinned commit's
root license file. It is a technical classification, not a legal review:
`license_review` stays `pending` everywhere and a human (ideally a software
IP lawyer) still has to approve real use. This module never fetches anything.

Policies:
- libre: permissive license (MIT, Apache-2.0, BSD, ISC, CC0, Unlicense, PostgreSQL).
- libre_nucleo: permissive core; enterprise/commercial folders must not be used.
- libre_condicionado: usable as-is with a stated condition (MPL-2.0 files,
  Meta platform SDK, license declared only in README).
- excluido: copyleft, source-available, custom or missing license. Registered
  so the history stays traceable, but the Engine refuses to operate it unless
  the operator records an explicit, named exception in the private config.
"""
import json
import re
from pathlib import Path

from .catalog import catalog
from .common import VerdugoError

PATH = Path(__file__).resolve().parents[1] / "sources" / "licenses.json"
POLICIES = ('libre', 'libre_nucleo', 'libre_condicionado', 'excluido')
PERMISSIVE = {'MIT', 'Apache-2.0', 'Apache-2.0 OR MIT', 'Apache-2.0 AND MIT',
              'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'CC0-1.0', 'Unlicense',
              'PostgreSQL', 'MIT AND BUSL-1.1'}
EXCLUDED = frozenset({
    'twenty', 'frappe-crm', 'erpnext', 'odoo', 'mautic', 'listmonk',
    'easyappointments', 'formbricks', 'documenso', 'postiz', 'dub', 'comfyui',
    'remotion', 'n8n', 'nango', 'airbyte', 'plausible', 'matomo', 'metabase',
    'lago', 'unleash', 'grafana'})
ALLOWED_TOTAL = 300
SHA = re.compile(r'^[0-9a-f]{40}$')
_CACHE = {}


def read_policy(path=None):
    """Fail closed unless every catalogue entry has exactly one valid record."""
    path = Path(path) if path is not None else PATH
    key = str(path)
    if key in _CACHE:
        return _CACHE[key]
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 262144:
            raise VerdugoError('License evidence is not a bounded regular file')
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise VerdugoError('License evidence is unreadable or invalid JSON') from exc
    records = document.get('records') if isinstance(document, dict) else None
    approved = catalog()
    if not isinstance(records, list) or len(records) != len(approved):
        raise VerdugoError('License evidence must cover the whole catalogue')
    table = {}
    for row, expected in zip(records, approved):
        if not isinstance(row, dict) or row.get('number') != expected['number'] or \
                row.get('id') != expected['id'] or row.get('repository') != expected['repository']:
            raise VerdugoError('License evidence does not match the catalogue')
        policy, spdx = row.get('policy'), row.get('spdx')
        if policy not in POLICIES or not isinstance(spdx, str) or not spdx:
            raise VerdugoError('Invalid license policy record: ' + expected['id'])
        if not isinstance(row.get('scanned_commit'), str) or not SHA.fullmatch(row['scanned_commit']):
            raise VerdugoError('License evidence requires the scanned 40-hex commit')
        if (policy == 'excluido') != (expected['id'] in EXCLUDED):
            raise VerdugoError('Excluded set differs from the declared policy: ' + expected['id'])
        if policy in ('libre', 'libre_nucleo') and spdx not in PERMISSIVE:
            raise VerdugoError('Non-permissive license marked as libre: ' + expected['id'])
        if 'license_review' in row or 'approved' in row:
            raise VerdugoError('License evidence cannot assert a legal review')
        table[expected['id']] = row
    if sum(r['policy'] != 'excluido' for r in table.values()) != ALLOWED_TOTAL:
        raise VerdugoError('Permissive portfolio must contain exactly 300 projects')
    _CACHE[key] = table
    return table


def record(service):
    return read_policy().get(service)


def check(service, cfg):
    """Refuse excluded services unless a named operator exception is configured."""
    row = record(service)
    if row is None or row['policy'] != 'excluido':
        return None
    exception = cfg.get('license_policy_exception')
    if not isinstance(exception, dict) or set(exception) != {'approved_by', 'reason'} or \
            any(not isinstance(exception[k], str) or not exception[k].strip() or len(exception[k]) > 200
                for k in exception):
        raise VerdugoError('Excluded by license policy (%s): %s' % (row['spdx'], service))
    return {'service': service, 'spdx': row['spdx'], 'approved_by': exception['approved_by']}


def summary(project_id=None):
    table = read_policy()
    if project_id is not None:
        if not isinstance(project_id, str) or project_id not in table:
            raise VerdugoError('Unknown registered source ID')
        row = table[project_id]
        return {'project_id': project_id, 'repository': row['repository'],
                'spdx': row['spdx'], 'policy': row['policy'], 'note': row.get('note'),
                'scanned_commit': row['scanned_commit'], 'origin': row.get('origin'),
                'license_review': 'pending', 'legal_advice': False}
    counts = {p: sum(r['policy'] == p for r in table.values()) for p in POLICIES}
    return {'name': 'Verdugo Digital license policy', 'registered': len(table),
            'allowed': len(table) - counts['excluido'], 'counts': counts,
            'excluded': sorted(k for k, r in table.items() if r['policy'] == 'excluido'),
            'core_only': sorted(k for k, r in table.items() if r['policy'] == 'libre_nucleo'),
            'conditioned': sorted(k for k, r in table.items() if r['policy'] == 'libre_condicionado'),
            'license_review_pending': len(table), 'legal_advice': False,
            'note': 'Automated reading of root license files at pinned commits; '
                    'not a legal review. Excluded entries cannot run without a named operator exception.'}
