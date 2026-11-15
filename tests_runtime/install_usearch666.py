"""Explicit native CPU source build; preparation tools never enter the runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import local_usearch666 as sdk
from install_final import download


def verify_source(source, record):
    for entry in record['files']:
        data = (source / entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != entry['blob_sha']):
            raise ValueError('USearch source differs from reviewed Git bytes')


def record_installation(prefix, sources, record):
    for source in record['sources']:
        verify_source(sources[source['id']], source)
    caches = list((sources['usearch'] / 'build_python').glob('*/CMakeCache.txt'))
    if len(caches) != 1:
        raise ValueError('Expected exactly one original USearch build')
    cache = caches[0].read_text()
    values = {line.partition(':')[0]: line.partition('=')[2]
              for line in cache.splitlines() if '=' in line and not line.startswith('//')}
    for key, value in record['cmake_options'].items():
        if values.get(key) != value:
            raise ValueError('Original USearch CMake options differ: ' + key)
    for sid, source in sources.items():
        if sid != 'usearch' and values.get('FETCHCONTENT_SOURCE_DIR_' + sid.upper()) != str(source):
            raise ValueError('USearch dependency did not use verified local source')
    receipt = {'schema': 'verdugo.usearch666.operator-build.v1',
               **{k: record[k] for k in ('commit', 'build_tools', 'build_environment', 'cmake_options')},
               'source_archives': {r['id']: r['archive_sha256'] for r in record['sources']},
               'native_sha256': hashlib.sha256((prefix / sdk.NATIVE).read_bytes()).hexdigest(),
               'cmake_cache_sha256': hashlib.sha256(cache.encode()).hexdigest(),
               'compiler': subprocess.check_output(['g++-14', '--version'], text=True).splitlines()[0],
               'independent_build_attestation': False, 'reproducible_binary_build_proven': False}
    dest = prefix / sdk.RECEIPT; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + '\n')
    sdk.verify_build(prefix, record)
    return receipt


def install(prefix):
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Use the reviewed Python 3.12 Linux x86_64 profile')
    record = json.loads(sdk.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = prefix / 'bin/python'
    for p in (prefix / 'bin').glob('python*'):
        if not p.is_symlink(): p.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='usearch666-build-') as tmp:
        work = Path(tmp); build_env = work / 'tools'
        venv.EnvBuilder(with_pip=True, symlinks=False).create(build_env)
        build_python = build_env / 'bin/python'
        subprocess.run([str(build_python), '-m', 'pip', 'install',
                        *[k+'=='+v for k, v in record['build_tools'].items()]], check=True)
        sources = {}
        for source in record['sources']:
            archive = work / (source['id'] + '.tar.gz')
            download(source['archive_url'], archive, source['archive_sha256'])
            target = work / source['id']
            with tarfile.open(archive) as tar: tar.extractall(target, filter='data')
            sources[source['id']] = next(target.iterdir())
            verify_source(sources[source['id']], source)
        env = dict(os.environ, **record['build_environment'])
        env['PATH'] = str(build_env / 'bin') + os.pathsep + os.defpath
        args = [str(build_python), '-m', 'pip', 'wheel', '--no-build-isolation', '--no-deps',
                str(sources['usearch']), '-w', str(work / 'wheels'),
                '--config-settings=cmake.build-type=Release']
        args += ['--config-settings=cmake.define.'+k+'='+v for k, v in record['cmake_options'].items()]
        args += ['--config-settings=cmake.define.FETCHCONTENT_SOURCE_DIR_'+sid.upper()+'='+str(path)
                 for sid, path in sources.items() if sid != 'usearch']
        subprocess.run(args, env=env, check=True)
        wheel = next((work / 'wheels').glob('usearch-*.whl'))
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', str(wheel),
                        '--report', '/tmp/usearch666-pip-report.json'], check=True)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
        receipt = record_installation(prefix, sources, record)
    Path('/tmp/usearch666-build-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    Path('/tmp/usearch666-resolved.txt').write_text(subprocess.check_output(
        [str(python), '-m', 'pip', 'freeze'], text=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-usearch666'))
    install(parser.parse_args().prefix)
