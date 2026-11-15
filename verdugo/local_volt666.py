"""Pinned original VoltAgent bundle in a separate, offline Node profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .common import VerdugoError, fields, integer
from .local_native import checked

SPECS = {'voltagent': ('measurement.review', 'npm:@voltagent/core', '2.11.1')}
ENV = 'VERDUGO_VOLT666_ROOT'
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-volt666.json'
WORKER = Path(__file__).with_name('_volt666_worker.mjs')
GUARD = Path(__file__).with_name('_offline_node_guard.cjs')


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts or
            any(c in value for c in ('\0', '\n', '\r'))):
        raise VerdugoError('Absolute administrator VoltAgent runtime required')
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
        digest.update(hashlib.sha256(binary.read_bytes()).digest())
        checks = {'package-lock.json': contract['lock_sha256']} | contract['artifacts']
        for name, sha in checks.items():
            actual = hashlib.sha256(checked(home / name, budget=16*1024*1024).read_bytes()).hexdigest()
            if actual != sha:
                raise ValueError('Pinned npm bundle or lockfile changed')
            digest.update(bytes.fromhex(actual))
        manifest = json.loads(checked(home / 'node_modules/@voltagent/core/package.json').read_text())
        if manifest['name'] != '@voltagent/core' or manifest['version'] != version:
            raise ValueError('VoltAgent package identity mismatch')
        present, binding = True, digest.hexdigest()
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'distribution_kind': 'npm', 'expected': version,
            'installed': version if present else None, 'version_matches': present,
            'extra_distributions': {}, 'operation': operation, 'execution_verified': False,
            'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported fixed VoltAgent operation')
    fields(p, ('dataset', 'target_clients', 'simulated_median', 'observed_clients', 'observed_contacts'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic demo counts supported')
    integer(p['target_clients'], 1, 10000)
    for key in ('simulated_median', 'observed_clients', 'observed_contacts'):
        integer(p[key], 0, 20000)
    if p['observed_clients'] > p['observed_contacts']:
        raise VerdugoError('Clients cannot exceed exposure')


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('VoltAgent runtime differs from the reviewed bundle')
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
            raise VerdugoError('Original VoltAgent workflow failed')
    result = json.loads(raw)
    if (result.get('original_sdk') != service or result.get('fixed_sdk_steps') != 2 or
            result.get('external_execution_authorized') is not False or
            result.get('operator_approval_required') is not True):
        raise VerdugoError('Invalid original workflow evidence')
    contract = json.loads(CONTRACT.read_text())
    return result | {'source_commit': contract['commit'],
                     'reviewed_source_map_files': contract['source_map_files_verified']}
