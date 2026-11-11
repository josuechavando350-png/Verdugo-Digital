"""Bounded sequential DAG executor; deterministic references, no eval or shell."""
from .common import VerdugoError, fields, identifier, digest


def references(value):
    if isinstance(value, dict):
        if '$ref' in value:
            fields(value, ('$ref',))
            if not isinstance(value['$ref'], str) or '.' not in value['$ref']:
                raise VerdugoError('Reference must be step.field')
            yield value['$ref'].split('.', 1)[0]
        else:
            for v in value.values(): yield from references(v)
    elif isinstance(value, list):
        for v in value: yield from references(v)


def resolve(value, results):
    if isinstance(value, dict):
        if '$ref' in value:
            parts = value['$ref'].split('.')
            current = results
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    raise VerdugoError('Unresolved workflow reference')
                current = current[part]
            return current
        return {k: resolve(v, results) for k, v in value.items()}
    if isinstance(value, list): return [resolve(v, results) for v in value]
    return value


def order(spec, engine):
    fields(spec, ('id', 'steps'))
    identifier(spec['id'])
    if len(spec['id']) > 50: raise VerdugoError('Workflow ID exceeds 50 characters')
    if not isinstance(spec['steps'], list) or not 1 <= len(spec['steps']) <= 50:
        raise VerdugoError('Workflow needs 1..50 steps')
    nodes = {}
    for step in spec['steps']:
        fields(step, ('id', 'service', 'operation', 'params'), ('depends_on',))
        sid = identifier(step['id'])
        if len(sid) > 40 or sid in nodes: raise VerdugoError('Duplicate or overlong step ID')
        if not isinstance(step['params'], dict): raise VerdugoError('Step params must be an object')
        deps = step.get('depends_on', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise VerdugoError('Invalid dependencies')
        deps = set(deps)
        if not set(references(step['params'])) <= deps:
            raise VerdugoError('Every reference must have a declared direct dependency')
        engine.preflight(step['service'], step['operation'])
        nodes[sid] = step | {'depends_on': sorted(deps)}
    if any(set(s['depends_on']) - nodes.keys() for s in nodes.values()):
        raise VerdugoError('Unknown workflow dependency')
    done, result = set(), []
    while len(done) < len(nodes):
        ready = [s for sid, s in nodes.items() if sid not in done and set(s['depends_on']) <= done]
        if not ready: raise VerdugoError('Workflow contains a cycle')
        for step in ready:
            done.add(step['id'])
            result.append(step)
    return result


def run(engine, spec, execute=False):
    if type(execute) is not bool: raise VerdugoError('execute must be boolean')
    steps = order(spec, engine)  # All adapters/config/license gates checked before first step.
    fingerprint = digest(spec)
    with engine.transaction():
        engine.db.execute('CREATE TABLE IF NOT EXISTS workflow_manifests ('
                          'tenant TEXT, id TEXT, hash TEXT NOT NULL, PRIMARY KEY(tenant,id))')
        old = engine.db.execute('SELECT hash FROM workflow_manifests WHERE tenant=? AND id=?',
                               (engine.tenant, spec['id'])).fetchone()
        if old and old['hash'] != fingerprint:
            raise VerdugoError('Workflow ID already bound to a different definition')
        engine.db.execute('INSERT OR IGNORE INTO workflow_manifests VALUES(?,?,?)',
                          (engine.tenant, spec['id'], fingerprint))
    plans = []
    for step in steps:
        if not list(references(step['params'])):
            plans.append(engine.plan({'service': step['service'], 'operation': step['operation'],
                'params': step['params'], 'key': spec['id'] + '-' + step['id']}))
    if not execute:
        return {'state': 'planned', 'id': spec['id'], 'ordered_steps': steps, 'action_plans': plans,
                'approval_batch': [{'key': p['key'], 'fingerprint': p['fingerprint']} for p in plans if p['requires_approval']],
                'external_calls_made': False,
                'note': 'Dependent values and per-action approvals are checked at execution.'}
    results = {}
    for step in steps:
        command = {'service': step['service'], 'operation': step['operation'],
                   'params': resolve(step['params'], results),
                   'key': spec['id'] + '-' + step['id']}
        outcome = engine.execute(command, execute=True)
        if outcome['state'] != 'succeeded':
            return {'state': 'paused', 'step': step['id'], 'outcome': outcome,
                    'completed_steps': list(results),
                    'note': 'No distributed rollback. Reconcile before resuming.'}
        results[step['id']] = outcome['result']
    return {'state': 'succeeded', 'id': spec['id'], 'steps': results}
