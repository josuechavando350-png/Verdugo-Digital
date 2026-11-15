"""Fixed original pipelines and review routing; no model or general code input."""
import asyncio
import hashlib
from importlib import metadata
import json
from pathlib import Path

from .common import VerdugoError, encode, fields, integer
from . import objectives

SPECS={'griptape':('objective.scenarios','griptape','1.13.0'),
       'beeai-framework':('review.route','beeai-framework','0.1.86')}
CONTRACT=Path(__file__).resolve().parents[1]/'sources/contracts-flow666.json'


def validate(service,operation,p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed pipeline action')
    if service=='griptape':
        fields(p,('dataset','goals'))
        if not isinstance(p['goals'],list) or not 2<=len(p['goals'])<=4:
            raise VerdugoError('Compare two to four synthetic goals')
        for goal in p['goals']:objectives.validate_goal(goal)
        for key in ('currency','target_clients','horizon_days'):
            if len({g[key] for g in p['goals']}) != 1:
                raise VerdugoError('Scenarios require the same currency, target and time horizon')
    else:
        fields(p,('dataset','budget_ok','capacity_ok','observed_clients','target_clients'))
        if type(p['budget_ok']) is not bool or type(p['capacity_ok']) is not bool:
            raise VerdugoError('Explicit boolean checks required')
        integer(p['observed_clients'],0,objectives.MAX_CONTACTS)
        integer(p['target_clients'],1,10000)
    if p['dataset']!='demo':raise VerdugoError('Only synthetic demo data is supported')


def verify_source(service):
    record=next(r for r in json.loads(CONTRACT.read_text())['records'] if r['id']==service)
    distribution=metadata.distribution(record['distribution'])
    checked=0
    for f in record['files']:
        if f['installed_path']:
            if hashlib.sha256(distribution.locate_file(f['installed_path']).read_bytes()).hexdigest()!=f['sha256']:
                raise VerdugoError('Installed flow SDK differs from reviewed original source')
            checked+=1
    if not checked:raise VerdugoError('Missing original flow SDK modules')
    return {'source_commit':record['commit'],'reviewed_modules_verified':checked}


def compare_plans(plans):
    rows=[{'index':i,'contacts':r['planned_contacts'],'cost_minor':r['simulated_cost_minor'],
           'conditional_expected_clients':r['conditional_expected_clients'],
           'target_feasible_under_point_assumptions':r['target_feasible_under_point_assumptions']}
          for i,r in enumerate(plans)]
    frontier=[]
    for candidate in rows:
        dominated=any(other['cost_minor']<=candidate['cost_minor'] and
                      other['conditional_expected_clients']>=candidate['conditional_expected_clients'] and
                      (other['cost_minor']<candidate['cost_minor'] or
                       other['conditional_expected_clients']>candidate['conditional_expected_clients']) for other in rows)
        if not dominated:frontier.append(candidate['index'])
    return {'scenarios':rows,'pareto_nondominated_indices':frontier,
            'comparison_scope':'Point assumptions supplied in synthetic goals; cost and expected clients only',
            'real_market_optimality_proven':False,'forecast_is_guarantee':False}


def run(service,p):
    validate(service,SPECS[service][0],p)
    evidence=verify_source(service)
    result=scenarios(p) if service=='griptape' else route(p)
    return result | evidence | {'original_sdk':service,'sdk_version':SPECS[service][2],
        'dataset':'demo','dry_run':True,'llm_calls':0,'autonomous_agent':False,
        'external_calls_made':False,'external_execution_authorized':False}


def scenarios(p):
    from griptape.structures import Pipeline
    from griptape.tasks import CodeExecutionTask
    from griptape.artifacts import TextArtifact

    def project(task):
        return TextArtifact(encode([objectives.plan(g) for g in json.loads(task.input.value)]))

    def compare(task):
        return TextArtifact(encode(compare_plans(json.loads(task.input.value))))

    pipeline=Pipeline(conversation_memory=None,tasks=[
        CodeExecutionTask(id='project',input=TextArtifact(encode(p['goals'])),on_run=project),
        CodeExecutionTask(id='compare',input=lambda task:task.parents[0].output,on_run=compare)])
    pipeline.run()
    if len(pipeline.finished_tasks)!=2 or not isinstance(pipeline.output,TextArtifact):
        raise ValueError('Fixed Griptape pipeline failed')
    return json.loads(pipeline.output.value) | {'fixed_sdk_tasks':2,'conversation_memory_used':False,
                                               'caller_code_executed':False}


def route(p):
    from pydantic import BaseModel
    from beeai_framework.workflows.workflow import Workflow

    class Review(BaseModel):
        budget_ok:bool
        capacity_ok:bool
        observed_clients:int
        target_clients:int
        recommendation:str='unreviewed'

    def assess(state):
        if not state.budget_ok or not state.capacity_ok:return 'limits'
        return 'revise' if state.observed_clients<state.target_clients else 'review'

    def limits(state):
        state.recommendation='revise_limits'
        return Workflow.END

    def revise(state):
        state.recommendation='revise_strategy'
        return Workflow.END

    def review(state):
        state.recommendation='request_operator_review'
        return Workflow.END

    wf=Workflow(Review,name='verdugo-synthetic-review')
    for name,handler in [('assess',assess),('limits',limits),('revise',revise),('review',review)]:
        wf.add_step(name,handler)

    async def execute():
        return await wf.run(Review(**{k:v for k,v in p.items() if k!='dataset'}))

    outcome=asyncio.run(execute())
    path=[step.name for step in outcome.steps]
    if len(path)!=2 or path[0]!='assess' or outcome.state.recommendation=='unreviewed':
        raise ValueError('Fixed BeeAI review workflow failed')
    return {'recommendation':outcome.state.recommendation,'sdk_step_path':path,
            'operator_approval_required':True,'real_observations_verified':False}
