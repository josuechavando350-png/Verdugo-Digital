"""Original fixed executive SDK operations; no model, generated code or agent loop."""
import asyncio
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, encode, fields, integer
from . import objectives

SPECS = {'agno': ('objective.plan', 'agno', '3.2.0'),
         'ag2': ('actions.check', 'ag2', '1.3.1')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-executive666.json'


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed executive SDK operation')
    if service == 'agno':
        fields(p, ('dataset', 'goal'))
        objectives.validate_goal(p['goal'])
    else:
        fields(p, ('dataset', 'budget_minor', 'currency', 'actions'))
        integer(p['budget_minor'], 0, 10**9)
        if p['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('Unsupported explicit currency')
        if not isinstance(p['actions'], list) or not 1 <= len(p['actions']) <= 4:
            raise VerdugoError('One to four aggregate synthetic actions required')
        seen = set()
        for a in p['actions']:
            fields(a, ('channel', 'contacts', 'cost_per_contact_minor'))
            if not isinstance(a['channel'], str) or a['channel'] not in objectives.CHANNELS or a['channel'] in seen:
                raise VerdugoError('Unknown or duplicated synthetic channel')
            seen.add(a['channel'])
            integer(a['contacts'], 0, objectives.MAX_CONTACTS)
            integer(a['cost_per_contact_minor'], 0, 10**7)
    if p['dataset'] != 'demo':
        raise VerdugoError('Only aggregate synthetic demo data is accepted')


def verify_source(service):
    contract = next(r for r in json.loads(CONTRACT.read_text())['records'] if r['id'] == service)
    distribution = metadata.distribution(contract['distribution'])
    checked = []
    for source in contract['files']:
        if source['installed_path'] is not None:
            raw = distribution.locate_file(source['installed_path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise VerdugoError('Installed executive SDK differs from reviewed source')
            checked.append(source['path'])
    if not checked:
        raise VerdugoError('Missing original executive source evidence')
    return {'source_commit': contract['commit'], 'reviewed_modules_verified': len(checked)}


def run(service, p):
    validate(service, SPECS[service][0], p)
    evidence = verify_source(service)
    result = agno_plan(p) if service == 'agno' else ag2_check(p)
    return result | evidence | {'original_sdk': service, 'sdk_version': SPECS[service][2],
                                'llm_calls': 0, 'autonomous_agent': False,
                                'external_calls_made': False, 'dataset': 'demo'}


def agno_plan(p):
    from agno.workflow.step import Step
    from agno.workflow.types import StepInput, StepOutput
    from agno.workflow.workflow import Workflow

    def allocate(step_input: StepInput) -> StepOutput:
        return StepOutput(content=objectives.plan(step_input.input))

    def check(step_input: StepInput) -> StepOutput:
        plan = step_input.previous_step_content
        if not isinstance(plan, dict) or plan['simulated_cost_minor'] > p['goal']['budget_minor']:
            raise ValueError('Budget check failed')
        return StepOutput(content=plan | {'budget_checked': True})

    wf = Workflow(id='verdugo-synthetic-plan', name='Synthetic goal allocation', db=None,
                  telemetry=False, store_media=False, cache_session=False,
                  steps=[Step(name='allocate', executor=allocate, max_retries=0),
                         Step(name='budget-check', executor=check, max_retries=0)])
    outcome = wf.run(input=p['goal'], session_id='synthetic-local', run_id='synthetic-local',
                     stream=False, background=False)
    if not isinstance(outcome.content, dict) or not outcome.content.get('budget_checked'):
        raise ValueError('Fixed Agno workflow did not complete')
    return outcome.content | {'fixed_sdk_steps': 2, 'telemetry_enabled': False,
                              'sdk_database_used': False}


def check_actions(p):
    cost = sum(a['contacts'] * a['cost_per_contact_minor'] for a in p['actions'])
    contacts = sum(a['contacts'] for a in p['actions'])
    return {'action_count': len(p['actions']), 'planned_contacts': contacts,
            'planned_cost_minor': cost, 'budget_minor': p['budget_minor'],
            'currency': p['currency'], 'within_budget': cost <= p['budget_minor'],
            'within_contact_limit': contacts <= objectives.MAX_CONTACTS,
            'feasible_under_declared_limits': cost <= p['budget_minor'] and contacts <= objectives.MAX_CONTACTS,
            'operator_approval_still_required': True, 'external_execution_authorized': False,
            'dry_run': True, 'commercial_outcome_predicted': False}


def ag2_check(p):
    from ag2.context import ConversationContext
    from ag2.events import ToolCallEvent, ToolErrorEvent, ToolResultEvent, TextInput
    from ag2.stream import MemoryStream
    from ag2.tools.final.function_tool import tool

    @tool(name='check_synthetic_actions', sync_to_thread=False, timeout=5)
    def checked(action_json: str) -> str:
        return encode(check_actions(json.loads(action_json)))

    async def invoke_fixed():
        context = ConversationContext(stream=MemoryStream())
        call = ToolCallEvent(name='check_synthetic_actions', arguments=encode({'action_json': encode(p)}))
        result = await checked(call, context)
        if isinstance(result, ToolErrorEvent) or not isinstance(result, ToolResultEvent):
            raise ValueError('Fixed AG2 tool failed')
        parts = result.result.parts
        if len(parts) != 1 or not isinstance(parts[0], TextInput):
            raise ValueError('Unexpected AG2 tool result')
        return json.loads(parts[0].content)

    return asyncio.run(invoke_fixed()) | {'fixed_sdk_tools': 1, 'sdk_stream_storage': 'ephemeral_memory'}
