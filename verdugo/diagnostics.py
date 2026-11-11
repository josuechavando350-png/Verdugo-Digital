"""One bounded read per configured adapter; never a production certificate."""
from collections import Counter
from .adapters import SPECS, service_config
from .catalog import catalog
from .common import VerdugoError, identifier, digest


def doctor(engine, probe_id='configuration-check', execute=False):
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    identifier(probe_id)
    if len(probe_id) > 40: raise VerdugoError('Probe ID exceeds 40 characters')
    if execute and engine.role != 'operator':
        raise VerdugoError('Operator role required to probe external services')
    rows = []
    for item in catalog():
        sid = item['id']
        cfg = service_config(engine.config, engine.tenant, sid)
        row = {'service': sid, 'live_verified': False}
        if cfg.get('enabled') is not True:
            rows.append(row | {'state': 'disabled'}); continue
        operation = next((op for op, recipe in SPECS.get(sid, {}).items()
                          if recipe[0] == 'GET'), None)
        if operation is None:
            rows.append(row | {'state': 'not_implemented'}); continue
        params = {}
        if sid == 'prometheus':
            allowed = cfg.get('allowed_queries', [])
            if not isinstance(allowed, list) or not allowed:
                rows.append(row | {'state': 'blocked', 'error': 'No allowed read query'}); continue
            params = {'query': allowed[0]}
        command = {'service': sid, 'operation': operation, 'params': params,
                   'key': 'probe-'+digest([probe_id, sid])[:32]}
        try:
            result = engine.execute(command, execute)
            row.update(state='read_succeeded' if result['state'] == 'succeeded' else result['state'],
                       operation=operation, replayed=result.get('replayed', False))
            if result['state'] == 'succeeded': row['result_digest'] = digest(result['result'])
            if result['state'] == 'failed': row['error'] = result['result']['error']
        except VerdugoError as exc:
            row.update(state='blocked', error=str(exc))
        rows.append(row)
    counts = dict(Counter(row['state'] for row in rows))
    active = len(rows) - counts.get('disabled', 0)
    problems = any(counts.get(s, 0) for s in ('blocked', 'failed', 'not_implemented', 'uncertain', 'running'))
    state = 'not_configured' if not active else 'incomplete' if problems else 'checked'
    return {'state': state, 'counts': counts, 'tenant': engine.tenant, 'probe_id': probe_id,
            'mode': 'bounded-read' if execute else 'configuration-only',
            'checks': rows, 'live_verified': 0,
            'note': 'Reads do not prove business correctness, isolation or production readiness. '
                    'Reusing a probe_id replays prior results; choose a new ID for fresh reads.'}
