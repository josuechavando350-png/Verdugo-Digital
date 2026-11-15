"""Synthetic business-goal baseline through the existing Engine.

This is a deterministic baseline plus a seeded binomial simulation, not an LLM
planner, a calibrated market model, or an adapter for any of the 366 projects.
Only aggregate synthetic counts are accepted. No external actions exist here.
"""
import math
import random
import hashlib
from pathlib import Path

from .common import VerdugoError, digest, fields, integer

ACTIONS = {'objective.plan', 'objective.simulate', 'objective.measure'}
CHANNELS = {'organic', 'referral', 'content', 'direct_outreach'}
SIMULATIONS = 128
MAX_CONTACTS = 20000
ALGORITHM = 'synthetic-funnel-v1'


def implementation_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def validate_goal(goal):
    fields(goal, ('dataset', 'target_clients', 'horizon_days', 'budget_minor', 'currency', 'channels'))
    if goal['dataset'] != 'demo':
        raise VerdugoError('The goal baseline accepts only aggregate synthetic demo data')
    integer(goal['target_clients'], 1, 10000)
    integer(goal['horizon_days'], 1, 366)
    integer(goal['budget_minor'], 0, 10**9)
    if goal['currency'] not in ('MXN', 'USD', 'EUR'):
        raise VerdugoError('Unsupported explicit currency')
    channels = goal['channels']
    if not isinstance(channels, list) or not 1 <= len(channels) <= 4:
        raise VerdugoError('Select one to four synthetic channels')
    seen = set()
    for channel in channels:
        fields(channel, ('channel', 'contacts_available', 'cost_per_contact_minor',
                         'history_contacts', 'history_clients'))
        name = channel['channel']
        if not isinstance(name, str) or name not in CHANNELS or name in seen:
            raise VerdugoError('Unknown or duplicate channel')
        seen.add(name)
        integer(channel['contacts_available'], 0, MAX_CONTACTS)
        integer(channel['cost_per_contact_minor'], 0, 10**7)
        integer(channel['history_contacts'], 1, 10**6)
        integer(channel['history_clients'], 0, channel['history_contacts'])


def validate(operation, params):
    if operation == 'objective.plan':
        fields(params, ('goal',))
        validate_goal(params['goal'])
    elif operation == 'objective.simulate':
        fields(params, ('goal', 'seed'))
        validate_goal(params['goal'])
        integer(params['seed'], 0, 2**31-1)
    elif operation == 'objective.measure':
        fields(params, ('simulation_key', 'observed_contacts', 'observed_clients', 'dataset'))
        from .common import identifier
        identifier(params['simulation_key'])
        if params['dataset'] != 'demo':
            raise VerdugoError('Measurements must be synthetic demo counts')
        integer(params['observed_contacts'], 0, MAX_CONTACTS)
        integer(params['observed_clients'], 0, params['observed_contacts'])
    else:
        raise VerdugoError('Unknown objective action')


def wilson(successes, trials):
    """95% Wilson interval for the supplied synthetic Bernoulli observations."""
    p, z = successes / trials, 1.959963984540054
    den = 1 + z*z/trials
    center = (p + z*z/(2*trials)) / den
    radius = z * math.sqrt((p*(1-p) + z*z/(4*trials))/trials) / den
    return [max(0.0, center-radius), min(1.0, center+radius)]


def plan(goal):
    validate_goal(goal)
    channels = []
    for raw in goal['channels']:
        trials, clients = raw['history_contacts'], raw['history_clients']
        channels.append(raw | {'rate': clients/trials, 'interval': wilson(clients, trials)})
    # Fixed ranking: lower Wilson rate per minor currency unit, free channels
    # first. This is a stated heuristic; it is not an optimal allocation proof.
    channels.sort(key=lambda c: (c['cost_per_contact_minor'] != 0,
                                -c['interval'][0]/max(1, c['cost_per_contact_minor']), c['channel']))
    remaining_budget, total_contacts, expected_clients = goal['budget_minor'], 0, 0.0
    actions = []
    for c in channels:
        remaining_clients = max(0, goal['target_clients'] - expected_clients)
        needed = math.ceil(remaining_clients/c['rate']) if c['rate'] else 0
        affordable = remaining_budget//c['cost_per_contact_minor'] if c['cost_per_contact_minor'] else MAX_CONTACTS
        contacts = min(needed, affordable, c['contacts_available'], MAX_CONTACTS-total_contacts)
        cost = contacts * c['cost_per_contact_minor']
        remaining_budget -= cost
        total_contacts += contacts
        expected_clients += contacts*c['rate']
        actions.append({'channel': c['channel'], 'contacts': contacts,
                        'simulated_cost_minor': cost, 'synthetic_conversion_rate': c['rate'],
                        'history_rate_interval_95': c['interval'],
                        'requires_operator_approval': True, 'external_execution_supported': False})
    return {'algorithm': ALGORITHM, 'dataset': 'demo', 'goal_digest': digest(goal),
            'target_clients': goal['target_clients'], 'horizon_days': goal['horizon_days'],
            'currency': goal['currency'], 'budget_minor': goal['budget_minor'],
            'planned_contacts': total_contacts, 'simulated_cost_minor': goal['budget_minor']-remaining_budget,
            'conditional_expected_clients': expected_clients,
            'target_feasible_under_point_assumptions': expected_clients >= goal['target_clients']-1e-9,
            'actions': actions, 'dry_run': True, 'external_calls_made': False,
            'local_model_used': False, 'calibrated_to_real_market': False,
            'forecast_is_guarantee': False,
            'basis': 'Fixed allocation heuristic on supplied synthetic counts; horizon is a supplied capacity window.'}


def simulate(params):
    validate('objective.simulate', params)
    blueprint = plan(params['goal'])
    rng = random.Random(params['seed'])
    counts = []
    for _ in range(SIMULATIONS):
        count = sum(sum(rng.random() < a['synthetic_conversion_rate'] for _ in range(a['contacts']))
                    for a in blueprint['actions'])
        counts.append(count)
    counts.sort()
    # Empirical order statistics; interval is conditional on fixed supplied
    # rates. Wilson uncertainty above is separate and is not calibrated away.
    quantiles = {name: counts[round(q*(SIMULATIONS-1))]
                 for name, q in [('p05', .05), ('p50', .5), ('p95', .95)]}
    return blueprint | {'simulation_seed': params['seed'], 'simulations': SIMULATIONS,
                        'clients_quantiles': quantiles,
                        'runs_reaching_target': sum(c >= blueprint['target_clients'] for c in counts),
                        'uncertainty_scope': 'Synthetic binomial variation conditional on fixed rates; excludes model misspecification and real-market change.'}


def measure(engine, params):
    validate('objective.measure', params)
    import json
    row = engine.db.execute('SELECT r.state,r.result,p.document FROM runs r JOIN plans p '
                            'ON r.tenant=p.tenant AND r.key=p.key WHERE r.tenant=? AND r.key=?',
                            (engine.tenant, params['simulation_key'])).fetchone()
    if not row or row['state'] != 'succeeded':
        raise VerdugoError('Measurement requires a completed simulation in this tenant')
    document = json.loads(row['document'])
    result = json.loads(row['result'])
    if document.get('service') != 'core' or document.get('operation') != 'objective.simulate' or \
            result.get('algorithm') != ALGORITHM or result.get('dataset') != 'demo':
        raise VerdugoError('Measurement reference is not a synthetic objective simulation')
    if params['observed_contacts'] != result['planned_contacts']:
        raise VerdugoError('Measured exposure must match the simulated exposure')
    quantiles, actual = result['clients_quantiles'], params['observed_clients']
    return {'algorithm': ALGORITHM, 'dataset': 'demo', 'goal_digest': result['goal_digest'],
            'simulation_result_digest': digest(result),
            'observed_contacts': params['observed_contacts'], 'observed_clients': actual,
            'difference_from_simulated_median': actual-quantiles['p50'],
            'inside_simulated_90_interval': quantiles['p05'] <= actual <= quantiles['p95'],
            'target_reached_in_supplied_demo': actual >= result['target_clients'],
            'measurement_source': 'operator_supplied_synthetic_counts',
            'real_clients_verified': 0, 'real_revenue_verified': False,
            'calibrated_to_real_market': False, 'external_calls_made': False}


def apply(engine, operation, params):
    validate(operation, params)
    if operation == 'objective.plan':
        return plan(params['goal'])
    if operation == 'objective.simulate':
        return simulate(params)
    return measure(engine, params)
