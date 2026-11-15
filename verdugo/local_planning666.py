"""Original graph scheduling and formal validation of fixed synthetic stages."""
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from . import objectives

SPECS = {
    'harness-sdk': ('limits.parallel', 'strands-agents', '1.65.1.dev10+gc8e1351a'),
    'unified-planning': ('sequence.validate', 'unified-planning', '0.0.0'),
}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-planning666.json'
STAGES = ('plan', 'limits', 'operator_review', 'simulate', 'measure')


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed planning operation')
    if service == 'harness-sdk':
        fields(p, ('dataset', 'budget_minor', 'capacity_contacts', 'actions'))
        integer(p['budget_minor'], 0, 10**9)
        integer(p['capacity_contacts'], 0, objectives.MAX_CONTACTS)
        if not isinstance(p['actions'], list) or not 1 <= len(p['actions']) <= 4:
            raise VerdugoError('One to four synthetic action allocations required')
        for action in p['actions']:
            fields(action, ('contacts', 'cost_per_contact_minor'))
            integer(action['contacts'], 0, objectives.MAX_CONTACTS)
            integer(action['cost_per_contact_minor'], 0, 10**7)
    else:
        fields(p, ('dataset', 'sequence', 'limits_satisfied', 'hypothetical_review_available'))
        if (not isinstance(p['sequence'], list) or len(p['sequence']) > 8 or
                any(not isinstance(s, str) or s not in STAGES for s in p['sequence'])):
            raise VerdugoError('At most eight fixed synthetic stages are supported')
        for key in ('limits_satisfied', 'hypothetical_review_available'):
            if type(p[key]) is not bool:
                raise VerdugoError('Explicit synthetic booleans required')
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic demo data is supported')


def verify_source(service):
    record = next(r for r in json.loads(CONTRACT.read_text())['records'] if r['id'] == service)
    distribution = metadata.distribution(record['distribution'])
    checked = 0
    for f in record['files']:
        if f['installed_path']:
            if hashlib.sha256(distribution.locate_file(f['installed_path']).read_bytes()).hexdigest() != f['sha256']:
                raise VerdugoError('Installed planning SDK differs from reviewed original source')
            checked += 1
    if not checked:
        raise VerdugoError('Missing original planning modules')
    return {'source_commit': record['commit'], 'reviewed_modules_verified': checked}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source(service)
    result = parallel_limits(p) if service == 'harness-sdk' else sequence(p)
    return result | evidence | {
        'original_sdk': service, 'sdk_version': SPECS[service][2], 'dataset': 'demo',
        'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True,
    }


def parallel_limits(p):
    from strands.multiagent.graph import GraphBuilder
    from strands.multiagent.base import MultiAgentBase, MultiAgentResult, Status

    # Fixed deterministic executors are supported by GraphBuilder. They are not
    # LLM agents or replacements for SDK classes; the original scheduler runs.
    checks = {}
    completed = []

    class LimitNode(MultiAgentBase):
        def __init__(self, key):
            super().__init__()
            self.id = key

        async def invoke_async(self, task, invocation_state=None, **kwargs):
            if self.id == 'budget':
                cost = sum(a['contacts'] * a['cost_per_contact_minor'] for a in p['actions'])
                checks.update(planned_cost_minor=cost, within_budget=cost <= p['budget_minor'])
            elif self.id == 'capacity':
                contacts = sum(a['contacts'] for a in p['actions'])
                checks.update(planned_contacts=contacts,
                              within_capacity=contacts <= p['capacity_contacts'])
            else:
                if set(completed) != {'budget', 'capacity'}:
                    raise ValueError('Original graph did not enforce join dependencies')
                checks['recommendation'] = ('request_operator_review' if checks['within_budget'] and
                                             checks['within_capacity'] else 'revise_limits')
            completed.append(self.id)
            return MultiAgentResult(status=Status.COMPLETED, execution_count=1)

    builder = GraphBuilder()
    for key in ('budget', 'capacity', 'review'):
        builder.add_node(LimitNode(key), key)
    for key in ('budget', 'capacity'):
        builder.add_edge(key, 'review')
        builder.set_entry_point(key)
    builder.set_max_node_executions(3)
    builder.set_execution_timeout(10)
    result = builder.build()('fixed synthetic allocation checks')
    if result.status != Status.COMPLETED or result.execution_count != 3 or completed[-1] != 'review':
        raise ValueError('Original graph did not finish the three fixed checks')
    if result.accumulated_usage['totalTokens'] != 0:
        raise ValueError('Unexpected model token usage')
    return checks | {'fixed_sdk_nodes': 3, 'join_dependencies_verified': True,
                     'completed_nodes': sorted(completed), 'model_usage_count': 0,
                     'sdk_session_persistence': False, 'approvals_granted': 0}


def sequence(p):
    from unified_planning.shortcuts import BoolType, Fluent, InstantaneousAction, Not, Problem
    from unified_planning.engines.plan_validator import SequentialPlanValidator
    from unified_planning.engines.results import ValidationResultStatus
    from unified_planning.plans import SequentialPlan

    problem = Problem('verdugo_synthetic_process')
    flags = {k: Fluent(k, BoolType()) for k in STAGES}
    for flag in flags.values():
        problem.add_fluent(flag, default_initial_value=False)
    limits_ok = Fluent('declared_limits_ok', BoolType())
    review_possible = Fluent('hypothetical_review_possible', BoolType())
    problem.add_fluent(limits_ok, default_initial_value=p['limits_satisfied'])
    problem.add_fluent(review_possible, default_initial_value=p['hypothetical_review_available'])
    actions = {}
    for index, stage in enumerate(STAGES):
        action = InstantaneousAction(stage + '_step')
        action.add_precondition(Not(flags[stage]))
        if index:
            action.add_precondition(flags[STAGES[index - 1]])
        if stage == 'limits':
            action.add_precondition(limits_ok)
        elif stage == 'operator_review':
            action.add_precondition(review_possible)
        action.add_effect(flags[stage], True)
        problem.add_action(action)
        actions[stage] = action
    problem.add_goal(flags['measure'])
    outcome = SequentialPlanValidator().validate(
        problem, SequentialPlan([actions[stage]() for stage in p['sequence']]))
    if outcome.status not in (ValidationResultStatus.VALID, ValidationResultStatus.INVALID):
        raise ValueError('The original validator did not determine a result')
    failed = outcome.inapplicable_action
    return {'sequence_valid': outcome.status == ValidationResultStatus.VALID,
            'reason': outcome.reason.name.lower() if outcome.reason else None,
            'first_inapplicable_stage': failed.action.name.removesuffix('_step') if failed else None,
            'validated_transition_count': max(0, len(outcome.trace) - 1),
            'submitted_stage_count': len(p['sequence']), 'formal_engine': outcome.engine_name,
            'scope': 'Fixed synthetic process and supplied booleans only',
            'operator_approval_verified': False, 'approvals_granted': 0,
            'plan_optimality_proven': False, 'business_outcome_proven': False}
