"""Fixed local tool and dialogue compilation; no model or remote server calls."""
import json
from .common import fields, identifier, integer, VerdugoError
SPECS={'mcp-agent':('campaigns.tool','mcp-agent','0.2.6'),
       'nemo-guardrails':('dialogue.compile','nemoguardrails','0.24.1')}
PROFILES={'mcp-agent':'MCPAGENT021','nemo-guardrails':'RAILS021'}
EXTRA={'mcp-agent':{'mcp':'1.30.0'}}

def validate(service,operation,p):
    from .local_runtime import string,validate as base
    if service not in SPECS or operation!=SPECS[service][0]:raise VerdugoError('Unsupported planning operation')
    if service=='mcp-agent':return base('duckdb','campaigns.aggregate',p)
    fields(p,('dataset','flows'))
    if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
    if not isinstance(p['flows'],list) or not 1<=len(p['flows'])<=20:raise VerdugoError('Provide 1..20 fixed dialogue pairs')
    names=[]
    for row in p['flows']:
        fields(row,('id','request','response'));identifier(row['id']);names.append(row['id'])
        for key in ('request','response'):
            string(row[key],500)
            if any(ord(c)<32 for c in row[key]):raise VerdugoError('Dialogue examples must be single-line text')
    if len(set(names))!=len(names):raise VerdugoError('Duplicate dialogue identifier')

def run(service,p):
    if service=='mcp-agent':
        import asyncio
        from mcp_agent.app import MCPApp
        from mcp_agent.config import Settings
        from mcp_agent.agents.agent import Agent
        def campaign_totals(rows:list[dict])->str:
            return json.dumps({key:sum(row[key] for row in rows) for key in ('spend_minor','revenue_minor','leads','conversions')})
        async def execute():
            app=MCPApp(name='verdugo',settings=Settings(mcp={'servers':{}},usage_telemetry={'enabled':False},otel={'enabled':False},logger={'type':'none'}))
            async with app.run():
                async with Agent(name='bounded',functions=[campaign_totals],server_names=[],context=app.context) as agent:
                    result=await agent.call_tool('campaign_totals',{'rows':p['rows']})
                    if result.isError or len(result.content)!=1:raise ValueError('Native local tool failed')
                    return json.loads(result.content[0].text)
        return {'totals':asyncio.run(execute()),'currency':p['currency'],'llm_calls':0,'remote_servers':0,'autonomous_agent':False}
    if service=='nemo-guardrails':
        from nemoguardrails import RailsConfig
        blocks=[]
        for i,row in enumerate(p['flows']):
            blocks.append(f'define user request {i}\n  '+json.dumps(row['request'])+f'\n\ndefine bot response {i}\n  '+json.dumps(row['response'])+f'\n\ndefine flow pair {i}\n  user request {i}\n  bot response {i}\n')
        cfg=RailsConfig.from_content(colang_content='\n'.join(blocks),config={'models':[],'colang_version':'1.0'})
        if len(cfg.flows)!=len(p['flows']):raise ValueError('Dialogue compilation mismatch')
        return {'flow_ids':[r['id'] for r in p['flows']],'compiled_flows':len(cfg.flows),'user_intents':len(cfg.user_messages),
                'bot_responses':len(cfg.bot_messages),'models_configured':len(cfg.models),'runtime_executed':False,'prompt_safety_certified':False}
    raise ValueError('Unsupported planning recipe')
