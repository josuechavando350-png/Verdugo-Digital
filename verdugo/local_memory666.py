"""Pinned original MCP memory bundle in a separate, offline Node profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .common import VerdugoError, fields, integer
from .local_native import checked

SPECS = {'servers': ('graph.audit', 'mcp:@modelcontextprotocol/server-memory', '2.1.1')}
ENV = 'VERDUGO_MEMORY666_ROOT'
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-memory666.json'
WORKER = Path(__file__).with_name('_memory666_worker.mjs')
GUARD = Path(__file__).with_name('_offline_node_guard.cjs')


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts or
            any(c in value for c in ('\0', '\n', '\r'))):
        raise VerdugoError('Absolute administrator MCP memory runtime required')
    return checked(Path(value), directory=True)


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        home = root()
        contract = json.loads(CONTRACT.read_text())
        digest = hashlib.sha256(str(home).encode() + CONTRACT.read_bytes())
        binary = checked(home / 'bin/node', budget=256*1024*1024)
        if not os.access(binary, os.X_OK):
            raise ValueError('Node is not executable')
        node_digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        if node_digest != contract['node_binary_sha256']:
            raise ValueError('Node differs from the verified distribution')
        digest.update(bytes.fromhex(node_digest))
        checks = {'package-lock.json': contract['lock_sha256']} | contract['artifacts']
        for name, sha in checks.items():
            actual = hashlib.sha256(checked(home / name, budget=16*1024*1024).read_bytes()).hexdigest()
            if actual != sha:
                raise ValueError('Pinned npm bundle or lockfile changed')
            digest.update(bytes.fromhex(actual))
        manifest = json.loads(checked(home / 'upstream/src/memory/package.json').read_text())
        if manifest['name'] != '@modelcontextprotocol/server-memory' or manifest['version'] != version:
            raise ValueError('MCP memory package identity mismatch')
        present, binding = True, digest.hexdigest()
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'distribution_kind': 'mcp', 'expected': version,
            'installed': version if present else None, 'version_matches': present,
            'extra_distributions': {}, 'operation': operation, 'execution_verified': False,
            'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported fixed MCP memory operation')
    fields(p, ('dataset', 'statuses', 'edges', 'query'))
    statuses = ('not_started', 'in_progress', 'completed', 'blocked')
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic stage graphs supported')
    if (not isinstance(p['statuses'], list) or not 1 <= len(p['statuses']) <= 16 or
            any(not isinstance(s, str) or s not in statuses for s in p['statuses'])):
        raise VerdugoError('One to sixteen fixed synthetic stage states required')
    if not isinstance(p['query'], str) or p['query'] not in statuses:
        raise VerdugoError('Only fixed status queries supported')
    if not isinstance(p['edges'], list) or len(p['edges']) > 64:
        raise VerdugoError('At most 64 dependency edges supported')
    for edge in p['edges']:
        if not isinstance(edge, list) or len(edge) != 2:
            raise VerdugoError('Each edge must be a pair of stage indices')
        for endpoint in edge:
            integer(endpoint, 0, len(p['statuses']) - 1)
        if edge[0] == edge[1]:
            raise VerdugoError('Self dependencies are not supported')


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('MCP memory runtime differs from the reviewed bundle')
    home = root()
    env = {'PATH': os.defpath, 'HOME': os.getcwd(), 'TMPDIR': os.getcwd(), 'LANG': 'C.UTF-8',
           ENV: str(home), 'DO_NOT_TRACK': '1', 'OTEL_SDK_DISABLED': 'true', 'NODE_ENV': 'production'}
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run([str(home / 'bin/node'), '--require', str(GUARD), str(WORKER)],
                              input=json.dumps(p).encode(), stdout=out, stderr=err, env=env,
                              timeout=30, close_fds=True)
        out.seek(0)
        raw = out.read(8193)
        if proc.returncode or len(raw) > 8192:
            raise VerdugoError('Original MCP memory workflow failed')
    result = json.loads(raw)
    if (result.get('original_sdk') != service or result.get('original_tools_called') != 6 or
            result.get('external_execution_authorized') is not False or
            result.get('operator_approval_required') is not True):
        raise VerdugoError('Invalid original workflow evidence')
    contract = json.loads(CONTRACT.read_text())
    return result | {'source_commit': contract['commit'],
                     'original_source_files_verified': len(contract['files']),
                     'reviewed_sdk_source_map_files': len(contract['sdk_dependency']['verified_files'])}
