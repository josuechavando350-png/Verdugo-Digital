"""One bounded workflow across commercial surfaces. Counts are not revenue."""
from . import workflow
from .common import VerdugoError, fields, identifier

ROUTES = {'mautic': ('contacts.list', 'contacts', dict),
          'easyappointments': ('services.list', None, list),
          'formbricks': ('surveys.list', 'data', list),
          'dub': ('links.list', None, list)}


def overview(engine, request, execute=False):
    fields(request, ('id', 'services'))
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    if execute and engine.role != 'operator': raise VerdugoError('Operator role required')
    identifier(request['id'])
    selected = request['services']
    if (not isinstance(selected, list) or not 1 <= len(selected) <= len(ROUTES) or
        any(not isinstance(s, str) or s not in ROUTES for s in selected) or
        len(set(selected)) != len(selected)):
        raise VerdugoError('Choose 1..4 distinct implemented commercial surfaces')
    spec = {'id': request['id'], 'steps': [{'id': sid, 'service': sid, 'operation': ROUTES[sid][0],
                                         'params': {}} for sid in selected]}
    result = workflow.run(engine, spec, execute)
    if not execute: return result
    if result['state'] != 'succeeded':
        return {'state': 'incomplete', 'id': request['id'], 'step': result.get('step'),
                'completed_steps': result.get('completed_steps', []),
                'reason': result.get('outcome', {}).get('state'), 'revenue_inferred': False}
    rows = []
    for sid in selected:
        op, key, expected_type = ROUTES[sid]
        raw = result['steps'][sid]
        values = raw.get(key) if key and isinstance(raw, dict) else raw if key is None else None
        valid = isinstance(values, expected_type)
        items = list(values.values()) if valid and isinstance(values, dict) else values if valid else []
        valid = valid and all(isinstance(v, dict) for v in items)
        run = engine.db.execute('SELECT key,finished FROM runs WHERE tenant=? AND key=?',
                                (engine.tenant, request['id']+'-'+sid)).fetchone()
        rows.append({'service': sid, 'operation': op, 'state': 'observed' if valid else 'invalid_response',
                     'records_in_response': len(items) if valid else None,
                     'coverage': 'single_response_not_complete_export', 'read_key': run['key'],
                     'observed_at': run['finished'], 'live_verified': False})
    return {'state': 'succeeded' if all(r['state'] == 'observed' for r in rows) else 'incomplete',
            'id': request['id'], 'tenant': engine.tenant, 'surfaces': rows,
            'revenue_inferred': False, 'combined_customer_count': None,
            'note': 'Different entities are not added together; repeat ID reuses saved reads. No bidirectional sync.'}
