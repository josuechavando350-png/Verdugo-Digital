"""First bounded pilot adapter: original Semantic Kernel, with no AI service.

Only one first-party deterministic function is registered and invoked. The SDK
does not choose tools, load a model, send prompts, or execute generated code.
"""
import asyncio
import json
import hashlib
from importlib import metadata
from pathlib import Path

from .common import VerdugoError, encode, fields
from . import objectives

SPECS = {'semantic-kernel': ('objective.plan', 'semantic-kernel', '1.47.0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-kernel666.json'


def verify_installed_source():
    """Version equality alone cannot prove the five reviewed SDK modules match."""
    contract = json.loads(CONTRACT.read_text())
    distribution = metadata.distribution('semantic-kernel')
    checked = 0
    for source in contract['source_files']:
        if source['path'].startswith('python/semantic_kernel/'):
            installed = distribution.locate_file(source['path'].removeprefix('python/'))
            if hashlib.sha256(installed.read_bytes()).hexdigest() != source['sha256']:
                raise VerdugoError('Installed SDK differs from reviewed source; provision the pinned source archive')
            checked += 1
    if checked != 5:
        raise VerdugoError('Incomplete reviewed SDK source contract')


def validate(service, operation, params):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown pilot adapter action')
    fields(params, ('dataset', 'goal'))
    if params['dataset'] != 'demo':
        raise VerdugoError('The pilot adapter requires synthetic demo data')
    objectives.validate_goal(params['goal'])


def run(service, params):
    validate(service, SPECS[service][0], params)
    verify_installed_source()
    from semantic_kernel import Kernel
    from semantic_kernel.functions import KernelFunctionFromMethod, kernel_function

    @kernel_function(name='plan_synthetic_goal', description='A fixed aggregate synthetic goal baseline')
    def plan_synthetic_goal(goal_json: str) -> str:
        return encode(objectives.plan(json.loads(goal_json)))

    async def invoke_fixed():
        kernel = Kernel()
        function = KernelFunctionFromMethod(method=plan_synthetic_goal, plugin_name='verdugo')
        result = await kernel.invoke(function=function, goal_json=encode(params['goal']))
        if kernel.services or result is None or not isinstance(result.value, str):
            raise ValueError('Unexpected SDK service configuration or response')
        return json.loads(result.value)

    result = asyncio.run(invoke_fixed())
    return result | {'original_sdk': 'semantic-kernel', 'sdk_version': '1.47.0',
                     'invoked_function': 'verdugo-plan_synthetic_goal',
                     'registered_ai_services': 0, 'llm_calls': 0, 'autonomous_agent': False}
