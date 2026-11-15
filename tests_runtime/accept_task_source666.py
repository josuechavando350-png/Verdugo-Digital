"""Probe original KAG request models and TTL task cache, not a full KAG server.

Preparation downloads two exact source files; execution can then run offline
using the existing Langroid test profile's Pydantic and cachetools dependencies.
No KAG solver, model backend, credentials or task submission is exercised.
"""
import argparse
import hashlib
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import task_reads666 as adapter

PATHS = ('kag/solver/server/model/task_req.py', 'kag/solver/server/asyn_task_manager.py')


def verified_sources(directory, prepare=False):
    contract = json.loads(adapter.CONTRACT.read_text())['records'][0]
    records = {r['path']: r for r in contract['files']}
    directory = Path(directory)
    if directory.is_symlink(): raise RuntimeError('Source root cannot be a symlink')
    if prepare: directory.mkdir(parents=True, exist_ok=True)
    result = {}
    for name in PATHS:
        rec = records[name]
        path = directory / Path(name).name
        if path.is_symlink(): raise RuntimeError('Source file cannot be a symlink')
        if prepare:
            url = 'https://raw.githubusercontent.com/' + contract['repository'] + '/' + contract['commit'] + '/' + name
            with urllib.request.urlopen(url, timeout=30) as response: raw = response.read(65537)
        else:
            if not path.is_file() or path.stat().st_size > 65536: raise RuntimeError('Missing bounded original source')
            raw = path.read_bytes()
        if (len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != rec['sha256']
                or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != rec['git_blob_sha']):
            raise RuntimeError('Original KAG source digest mismatch')
        if prepare: path.write_bytes(raw)
        result[name] = path
    return result


def load_original(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(source_root):
    paths = verified_sources(source_root)
    models = load_original('verdugo_upstream_kag_task_models', paths[PATHS[0]])
    cache = load_original('verdugo_upstream_kag_task_cache', paths[PATHS[1]])
    manager = cache.AsyncTaskManager(max_workers=1)
    task = 'a6c437f3-71f8-45d7-95fe-218d9ee24567'
    cfg = {'api_surface': 'self_hosted_solver_server', 'auth_mode': 'reviewed_proxy_bearer',
           'task_id_env': 'VERDUGO_SOURCE_PROBE_TASK_ID', 'version': adapter.PINNED_COMMITS['kag'],
           **{gate: True for gate in adapter.GATES}}
    previous = os.environ.get(cfg['task_id_env'])
    os.environ[cfg['task_id_env']] = task
    cases = []
    try:
        request = adapter.build('kag', 'task.summary', {}, cfg, 'https://example.invalid',
                                'synthetic-source-probe', {'Authorization': 'Bearer synthetic-source-probe'})
        envelope = json.loads(adapter.body_bytes(request))
        parsed = models.FeatureRequest.model_validate(envelope).features.task_req
        assert parsed.req_id == task and parsed.cmd == 'query'
        assert parsed.app_id == 0 and parsed.project_id == 0
        assert parsed.req.query == '' and parsed.req.host_addr == '' and parsed.config == {}
        for state, value in [('running', None), ('completed', {'answer': 'private-synthetic-result'}),
                             ('failed', 'private-synthetic-error')]:
            manager.result_cache[task] = {'task_id': task, 'status': state, 'result': value}
            response = manager.get_task_result(parsed.req_id)
            projected = adapter.check('kag', 'task.summary', response, request['public'])
            assert projected[state + '_reported'] == 1
            assert 'private-synthetic' not in json.dumps(projected) and task not in json.dumps(projected)
            cases.append(state)
        manager.result_cache.clear()
        missing = manager.get_task_result(parsed.req_id)
        assert adapter.check('kag', 'task.summary', missing, request['public'])['failed_may_mean_missing_or_expired']
        cases.append('missing_is_ambiguous_failed')
        manager.result_cache[task] = {'task_id': task, 'status': 'completed', 'result': None}
        manager.result_cache.expire(time=manager.result_cache.timer() + manager.result_cache.ttl + 1)
        expired = manager.get_task_result(parsed.req_id)
        assert expired == missing
        cases.append('expired_is_ambiguous_failed')
        assert manager.task_queue.empty() and cache.asyn_task.task_queue.empty()
    finally:
        manager.shutdown(); cache.asyn_task.shutdown()
        if previous is None: os.environ.pop(cfg['task_id_env'], None)
        else: os.environ[cfg['task_id_env']] = previous
    return {'schema': 'verdugo.kag-original-boundary-probe.v1',
            'source_commit': adapter.PINNED_COMMITS['kag'],
            'contract_sha256': hashlib.sha256(adapter.CONTRACT.read_bytes()).hexdigest(),
            'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'original_request_model_validated': True, 'original_task_cache_cases_passed': cases,
            'test_profile_dependencies': {name: version(name) for name in ('pydantic', 'cachetools')},
            'tasks_submitted': 0, 'models_called': 0, 'provider_network_calls': 0,
            'original_full_server_executed': False, 'http_dispatch_executed': False,
            'dependency_closure_certified': False, 'live_verified': False,
            'os_network_isolated': os.environ.get('VERDUGO_OS_NETWORK_ISOLATED') == '1',
            'note': 'Only two original source modules with synthetic cache data; HTTP/CLI/MCP/replay are tested separately.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-source')
    p.add_argument('--source-root')
    p.add_argument('--out')
    args = p.parse_args()
    if args.prepare_source:
        verified_sources(args.prepare_source, True)
        print('Two pinned KAG source modules verified and prepared')
        return
    if not args.source_root or not args.out: p.error('--source-root and --out required for execution')
    result = run(args.source_root)
    Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
