"""Fixed native operations inside the existing local worker; never a shell API."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from .common import VerdugoError, fields, identifier

SPECS = {
    'geo-lint': ('content.lint', 'npm:@ijonis/geo-lint', '0.2.1'),
    'site-md': ('html.markdown', 'npm:site-md', '0.2.6'),
    'seo-graph': ('breadcrumbs.build', 'npm:@jdevalk/seo-graph-core', '0.7.0'),
    'structured-data-validator': ('breadcrumbs.validate', 'npm:@adobe/structured-data-validator', '1.7.1'),
}
WORKER = Path(__file__).with_name('_node_worker.mjs')
ENV = 'VERDUGO_NATIVE_ROOT'


def checked(path, directory=False, budget=2*1024*1024):
    info = path.stat()
    if (path.is_symlink() or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_size > budget)):
        raise VerdugoError('Unsafe administrator native runtime')
    return path


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts
            or any(c in value for c in ('\x00', '\n', '\r'))):
        raise VerdugoError('An absolute administrator native runtime is required')
    return checked(Path(value), directory=True)


def runtime_state(service):
    operation, distribution, expected = SPECS[service]
    version, binding = None, None
    try:
        home = root()
        binary = checked(home/'bin/node', budget=256*1024*1024)
        if not os.access(binary, os.X_OK):
            raise VerdugoError('Native interpreter is not executable')
        package = distribution.removeprefix('npm:')
        package_dir = checked(home/'node_modules'/package, directory=True)
        manifest = checked(package_dir/'package.json').read_bytes()
        record = json.loads(manifest)
        if record['name'] != package:
            raise VerdugoError('Native package identity mismatch')
        version = record['version']
        lock = checked(home/'package-lock.json').read_bytes()
        entry = json.loads(lock)['packages']['node_modules/'+package]
        if entry['version'] != version or not entry.get('integrity', '').startswith('sha512-'):
            raise VerdugoError('Native lockfile does not match the package')
        h = hashlib.sha256(str(home).encode()+manifest+lock)
        with binary.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                h.update(block)
        binding = h.hexdigest()
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        version = None
    return {'distribution': distribution, 'distribution_kind': 'npm', 'expected': expected,
            'installed': version, 'version_matches': version == expected,
            'extra_distributions': {}, 'operation': operation, 'execution_verified': False,
            'runtime_binding': binding}


def validate(service, operation, p):
    from .local_runtime import string, validate as base
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported fixed native operation')
    required = {'geo-lint': ('title', 'description', 'text'), 'site-md': ('html',),
                'seo-graph': ('host', 'entries'), 'structured-data-validator': ('graph',)}[service]
    fields(p, ('dataset', *required))
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')
    if service == 'site-md':
        base('trafilatura', 'html.extract', p)
    elif service == 'geo-lint':
        string(p['title'], 500); string(p['description'], 1000); string(p['text'], 16000)
    elif service == 'seo-graph':
        host = p['host']
        if not isinstance(host, str) or len(host) > 253 or not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,63}', host):
            raise VerdugoError('A plain lower-case domain is required for local schema identifiers')
        entries = p['entries']
        if not isinstance(entries, list) or not 2 <= len(entries) <= 20:
            raise VerdugoError('Provide 2..20 ordered breadcrumbs')
        slugs = []
        for item in entries:
            fields(item, ('slug', 'name')); identifier(item['slug']); string(item['name'], 200)
            slugs.append(item['slug'])
        if len(set(slugs)) != len(slugs):
            raise VerdugoError('Duplicate breadcrumb slug')
    else:
        graph = p['graph']
        fields(graph, ('@context', '@graph'))
        if graph['@context'] != 'https://schema.org' or not isinstance(graph['@graph'], list) or len(graph['@graph']) != 1:
            raise VerdugoError('One bounded schema.org breadcrumb graph is required')
        item = graph['@graph'][0]
        fields(item, ('@type', 'itemListElement'), ('@id',))
        if item['@type'] != 'BreadcrumbList' or not isinstance(item['itemListElement'], list) or len(item['itemListElement']) > 20:
            raise VerdugoError('Only breadcrumb validation is implemented')
        if '@id' in item: string(item['@id'], 1000)
        # Missing/invalid values reach the upstream validator as data, but no
        # arbitrary nested structures, huge graphs, scripts or imports do.
        for crumb in item['itemListElement']:
            fields(crumb, (), ('@type', 'name', 'position', 'item'))
            for key, value in crumb.items():
                if key == 'item' and isinstance(value, dict):
                    fields(value, ('@id',)); string(value['@id'], 1000)
                elif not isinstance(value, (str, int)) or isinstance(value, bool):
                    raise VerdugoError('Bounded scalar breadcrumb fields required')
                elif isinstance(value, str): string(value, 1000)


def run(service, params):
    state = runtime_state(service)
    if not state['version_matches']:
        raise ValueError('Native runtime changed')
    home = root()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        result = subprocess.run([str(home/'bin/node'), str(WORKER)],
            input=json.dumps({'service': service, 'params': params}).encode(), stdout=out, stderr=err,
            timeout=60, check=False, env={'PATH': os.defpath, 'HOME': os.getcwd(), 'TMPDIR': os.getcwd(),
                                         ENV: str(home), 'LANG': 'C.UTF-8', 'DO_NOT_TRACK': '1'}, close_fds=True)
        out.seek(0); raw = out.read(1024*1024+1)
        if result.returncode or len(raw) > 1024*1024:
            raise ValueError('Native operation failed')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Invalid native operation result')
    return value
