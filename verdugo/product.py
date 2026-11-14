"""One product entry point over existing Engine, workflows and local business state.

This is a bounded observation workflow, not a replacement execution engine or
an automatic installer. Only contracts that discard raw provider data enter
the observation report. Other operations remain available via workflow.
"""
import time

from . import (commercial, connections, license_policy, local_runtime,
               marketing_reads, operations_reads, read_contracts, readiness_reads,
               reconciliation, service_reads, tanda1_reads, workflow)
from .adapters import SPECS, service_config
from .common import VerdugoError, fields, identifier


def read_operations():
    candidates = {sid: op for sid, (op, _) in read_contracts.METADATA_SCHEMAS.items()}
    candidates['growthbook'] = 'settings.read'
    for module in (marketing_reads, service_reads, tanda1_reads, readiness_reads, operations_reads):
        candidates.update({sid: next(iter(ops)) for sid, ops in module.SPECS.items()})
    policy = license_policy.read_policy()
    # The existing Airbyte contract addresses paid Cloud only. It cannot enter
    # this free/self-hosted product route merely because its code is available.
    return {sid: op for sid, op in sorted(candidates.items())
            if policy[sid]['policy'] != 'excluido' and sid != 'airbyte'}


def overview(engine, dataset='real'):
    business = commercial.report(engine, {'dataset': dataset})
    state = connections.summary()
    routes = read_operations()
    rows = []
    for sid, kind in connections.read_map()[0].items():
        cfg = service_config(engine.config, engine.tenant, sid)
        rows.append({'service': sid, 'kind': kind, 'state': connections.state(sid),
                     'enabled': cfg.get('enabled') is True,
                     'observation_operation': routes.get(sid),
                     'http_operations': list(SPECS.get(sid, {})),
                     'local_operations': [local_runtime.SPECS[sid][0]] if sid in local_runtime.SPECS else []})
    pending = reconciliation.pending(engine)
    return {'name': 'Verdugo Digital', 'state': 'observed_local', 'tenant': engine.tenant,
            'observed_at': time.time(), 'connection_states': state['states'],
            'registered': state['registered'], 'services': rows,
            'bounded_observation_routes': len(routes), 'business': business,
            'reconciliation_required': len(pending['items']),
            'reconciliation_list_truncated': len(pending['items']) == pending['limit'],
            'external_calls_made': False, 'live_verified': 0,
            'note': 'One Engine and tenant-scoped SQLite. Implemented and enabled do not mean deployed.'}


def observe(engine, request, execute=False):
    fields(request, ('id', 'services', 'dataset', 'currency'))
    if type(execute) is not bool:
        raise VerdugoError('execute must be boolean')
    if execute and engine.role != 'operator':
        raise VerdugoError('Operator role required')
    rid = identifier(request['id'])
    if len(rid) > 42:
        raise VerdugoError('Product run ID exceeds 42 characters')
    selected = request['services']
    routes = read_operations()
    if (not isinstance(selected, list) or not 1 <= len(selected) <= 49
            or any(not isinstance(s, str) or s not in routes for s in selected)
            or len(set(selected)) != len(selected)):
        raise VerdugoError('Select distinct implemented, policy-allowed bounded observation services')
    metrics = {'dataset': request['dataset'], 'currency': request['currency']}
    engine.validate_core('metrics.summary', metrics)
    selected = sorted(selected)
    spec = {'id': 'product-' + rid, 'steps': [
        {'id': sid, 'service': sid, 'operation': routes[sid], 'params': {}}
        for sid in selected]}
    spec['steps'].append({'id': 'business', 'service': 'core', 'operation': 'metrics.summary',
                          'params': metrics, 'depends_on': selected})
    # Prepare every selected contract before creating a manifest or sending the
    # first request. Never silently omit an unavailable service from the report.
    blocked = []
    for step in spec['steps']:
        try:
            prepared, _, _ = engine.prepare({'service': step['service'], 'operation': step['operation'],
                                              'params': step['params'], 'key': spec['id']+'-'+step['id']})
            if prepared['mutates']:
                raise VerdugoError('Product observations cannot perform external writes')
        except VerdugoError:
            # A configuration error may contain an operator-supplied URL or
            # variable name. Surface a stable reason, not private config text.
            blocked.append({'service': step['service'], 'state': 'configuration_required'})
    if blocked:
        return {'name': 'Verdugo Digital', 'state': 'blocked', 'id': rid, 'tenant': engine.tenant,
                'blockers': blocked, 'external_calls_made': False, 'live_verified': 0,
                'note': 'Review enabled/version/license/credentials/authentication with doctor; no service was skipped.'}
    result = workflow.run(engine, spec, execute, include_evidence=True)
    if not execute:
        return result | {'name': 'Verdugo Digital', 'product_run_id': rid,
                         'tenant': engine.tenant, 'live_verified': 0}
    rows = []
    for sid in selected:
        evidence = result['evidence'].get(sid)
        row = {'service': sid, 'operation': routes[sid],
               'state': evidence['state'] if evidence else 'not_started',
               'evidence': evidence}
        if sid in result['steps']:
            row['observation'] = result['steps'][sid]
        rows.append(row)
    succeeded = [r for r in rows if r['state'] == 'succeeded']
    return {'name': 'Verdugo Digital', 'state': result['state'], 'id': rid,
            'workflow_id': spec['id'], 'tenant': engine.tenant,
            'services': rows, 'failed_step': result.get('step'),
            'new_observations': sum(not r['evidence']['replayed'] for r in succeeded),
            'reused_observations': sum(r['evidence']['replayed'] for r in succeeded),
            'business_snapshot': result['steps'].get('business'),
            'business_evidence': result['evidence'].get('business'),
            'business_source': 'local_operator_records_not_provider_counts',
            'live_verified': 0, 'production_certified': False,
            'note': 'Same ID resumes saved observations, including failures. A new ID requests new reads. '
                    'Service counts are separate entities; they are not customers or revenue. '
                    'Local business figures are operator-declared, not bank-reconciled.'}
