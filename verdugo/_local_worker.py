"""Fixed private worker. It is never a general code/SQL/CLI execution endpoint."""
import contextlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import sys


def guard(event, args):
    # Defense in depth for the trusted Python code. Native libraries and browser
    # processes are NOT confined by Python audit hooks; use OS isolation for
    # hostile data. No recipe includes network APIs or runtime downloads.
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind',
                 'socket.getaddrinfo', 'socket.gethostbyname'):
        raise PermissionError('Network is disabled for local library operations')


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise ValueError('Input budget exceeded')
    request = json.loads(raw)
    # Chromium needs bounded profile/shared-memory files larger than 2 MiB.
    # This is a per-file limit, NOT a total disk quota or a security sandbox.
    # JSON output remains capped at 1 MiB for every adapter.
    file_budget = (128 if request['service'] == 'playwright' else 2) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_budget, file_budget))
    budget = int(request['timeout_seconds'])
    resource.setrlimit(resource.RLIMIT_CPU, (budget, budget + 1))
    sys.addaudithook(guard)
    # -I excludes cwd and PYTHONPATH. Add only the fixed installed first-party
    # module directory so no caller-selected modules can be imported.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from local_recipes import run
    dist = request['distribution']
    version = importlib.metadata.version(dist)
    if version != request['version']:
        raise ValueError('Distribution changed')
    if request['service'] == 'evidently' and importlib.metadata.version('pandas') != '2.3.3':
        raise ValueError('Evidently requires the tested pandas compatibility version')
    with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
        result = run(request['service'], request['operation'], request['params'])
    envelope = {'ok': True, 'service': request['service'], 'operation': request['operation'],
                'distribution': dist, 'version': version,
                'dataset': request['params']['dataset'], 'result': result,
                'external_provider_calls_made': False, 'production_certified': False,
                'commercial_success_probability': None,
                'implementation_sha256': request['implementation_sha256']}
    rendered = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(rendered) > 1024 * 1024:
        raise ValueError('Result budget exceeded')
    sys.stdout.buffer.write(rendered)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never print text that could contain user input, credentials, URLs,
        # local paths or provider responses. Full diagnostics require a local
        # developer-run test, not a chat-facing exception message.
        sys.stderr.write(type(error).__name__ + '\n')
        raise SystemExit(2)
