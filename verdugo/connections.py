"""v0.15 connection map: how each of the 322 catalogue entries plugs into Verdugo.

`kind` is a design classification stored in sources/connections.json.
`state` is computed from code only: an entry is `conectado` exclusively when
the Engine has an implemented HTTP or local adapter for it and the license
policy allows it. A map entry is never evidence of a working deployment.
"""
import json
from collections import Counter
from pathlib import Path

from .adapters import SPECS
from .catalog import catalog
from .common import VerdugoError
from . import license_policy, local_runtime

PATH = Path(__file__).resolve().parents[1] / "sources" / "connections.json"
KINDS = ('servicio', 'biblioteca', 'componente', 'cli', 'mcp', 'protocolo', 'datos', 'excluido')
STATES = ('conectado', 'pieza_de_construccion', 'pendiente', 'excluido')
_CACHE = {}


def read_map(path=None):
    path = Path(path) if path is not None else PATH
    if str(path) in _CACHE:
        return _CACHE[str(path)]
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 131072:
            raise VerdugoError('Connection map is not a bounded regular file')
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise VerdugoError('Connection map is unreadable or invalid JSON') from exc
    records = document.get('records') if isinstance(document, dict) else None
    kinds = document.get('kinds') if isinstance(document, dict) else None
    approved = catalog()
    if not isinstance(records, list) or len(records) != len(approved) or \
            not isinstance(kinds, dict) or set(kinds) != set(KINDS):
        raise VerdugoError('Connection map must classify the whole catalogue')
    policy = license_policy.read_policy()
    table = {}
    for row, expected in zip(records, approved):
        sid = expected['id']
        if not isinstance(row, dict) or set(row) != {'number', 'id', 'kind'} or \
                row['number'] != expected['number'] or row['id'] != sid or row['kind'] not in KINDS:
            raise VerdugoError('Connection map does not match the catalogue')
        if (row['kind'] == 'excluido') != (policy[sid]['policy'] == 'excluido'):
            raise VerdugoError('Connection map disagrees with the license policy: ' + sid)
        if sid in SPECS and row['kind'] not in ('servicio', 'excluido'):
            raise VerdugoError('An HTTP adapter requires kind servicio: ' + sid)
        if sid in local_runtime.SPECS and row['kind'] != 'biblioteca':
            raise VerdugoError('A local recipe requires kind biblioteca: ' + sid)
        table[sid] = row['kind']
    _CACHE[str(path)] = (table, kinds)
    return _CACHE[str(path)]


def state(sid):
    table, _ = read_map()
    kind = table[sid]
    if kind == 'excluido':
        return 'excluido'
    if sid in SPECS or sid in local_runtime.SPECS:
        return 'conectado'
    if kind == 'componente':
        return 'pieza_de_construccion'
    return 'pendiente'


def summary(project_id=None):
    table, kinds = read_map()
    if project_id is not None:
        if not isinstance(project_id, str) or project_id not in table:
            raise VerdugoError('Unknown registered source ID')
        return {'project_id': project_id, 'kind': table[project_id], 'state': state(project_id),
                'how': kinds[table[project_id]],
                'http_actions': sorted(SPECS.get(project_id, {})),
                'local_actions': [local_runtime.SPECS[project_id][0]] if project_id in local_runtime.SPECS else [],
                'live_verified': False}
    states = Counter(state(s) for s in table)
    by_kind = {k: dict(Counter(state(s) for s, v in table.items() if v == k)) for k in KINDS}
    return {'name': 'Verdugo Digital connection map', 'registered': len(table),
            'states': {s: states.get(s, 0) for s in STATES},
            'kinds': dict(Counter(table.values())), 'by_kind': by_kind,
            'pending': sorted(s for s in table if state(s) == 'pendiente'),
            'live_verified': 0,
            'note': 'conectado means an adapter is implemented and allowed by license policy; '
                    'it does not mean a real service was deployed or verified.'}
