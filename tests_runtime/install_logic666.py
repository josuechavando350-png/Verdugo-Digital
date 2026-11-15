"""Explicit original Z3 source build, with GMP and optional bindings disabled."""
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
from verdugo import local_logic666 as sdk
from install_final import download


def verify_source(source, record):
    for entry in record['files']:
        data = (source / entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != entry['blob_sha']):
            raise ValueError('Z3 source differs from reviewed Git bytes')


def record_installation(prefix, source, build, record):
    verify_source(source, record)
    cache = (build / 'CMakeCache.txt').read_text()
    values = {line.partition(':')[0]: line.partition('=')[2]
              for line in cache.splitlines() if '=' in line and not line.startswith('//')}
    for key, value in record['cmake_options'].items():
        if values.get(key) != value:
            raise ValueError('Original Z3 CMake option differs: '+key)
    artifacts = {path: hashlib.sha256((prefix/sdk.PACKAGE/path).read_bytes()).hexdigest()
                 for path in record['native_artifacts'] + record['generated_python']}
    # Wheel packing must preserve both names used by the original loader.
    if len({artifacts[p] for p in record['native_artifacts']}) != 1:
        raise ValueError('Z3 native aliases differ')
    receipt = {'schema': 'verdugo.z3666.operator-build.v1',
               **{k: record[k] for k in ('commit', 'archive_sha256', 'build_tools', 'cmake_options')},
               'artifacts': artifacts, 'cmake_cache_sha256': hashlib.sha256(cache.encode()).hexdigest(),
               'compiler': subprocess.check_output(['/usr/bin/g++-14', '--version'], text=True).splitlines()[0],
               'independent_build_attestation': False, 'reproducible_binary_build_proven': False}
    dest = prefix / sdk.RECEIPT; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2)+'\n')
    sdk.verify_build(prefix, record)
    return receipt


def package_built_source(prefix, source, build, tools, record, work):
    verify_source(source, record)
    env = dict(os.environ, Z3BUILD=str(build), PATH=str(tools/'bin')+os.pathsep+os.defpath,
               CC='/usr/bin/gcc-14', CXX='/usr/bin/g++-14')
    subprocess.run([str(tools/'bin/python'), '-m', 'pip', 'wheel', '--no-build-isolation',
                    '--no-deps', str(source/'src/api/python'), '-w', str(work/'wheels')], env=env, check=True)
    wheel = next((work/'wheels').glob('z3_solver-*.whl'))
    subprocess.run([str(prefix/'bin/python'), '-m', 'pip', 'install', '--no-index', str(wheel),
                    '--report', '/tmp/z3666-pip-report.json'], check=True)
    subprocess.run([str(prefix/'bin/python'), '-m', 'pip', 'check'], check=True)
    return record_installation(prefix, source, build, record)


def install(prefix):
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Use the reviewed Python 3.12 Linux profile')
    record = json.loads(sdk.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    for p in (prefix/'bin').glob('python*'):
        if not p.is_symlink(): p.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='z3666-build-') as tmp:
        work = Path(tmp); tools = work/'tools'
        venv.EnvBuilder(with_pip=True, symlinks=False).create(tools)
        subprocess.run([str(tools/'bin/python'), '-m', 'pip', 'install',
                        *[k+'=='+v for k,v in record['build_tools'].items()]], check=True)
        archive = work/'source.tar.gz'
        download(record['archive_url'], archive, record['archive_sha256'])
        with tarfile.open(archive) as tar: tar.extractall(work/'source', filter='data')
        source = next((work/'source').iterdir()); verify_source(source, record)
        build = work/'build'; cmake = str(tools/'bin/cmake')
        subprocess.run([cmake, '-S', str(source), '-B', str(build), '-G', 'Unix Makefiles',
                        *['-D'+k+'='+v for k,v in record['cmake_options'].items()]], check=True)
        subprocess.run([cmake, '--build', str(build), '--parallel', '1'], check=True)
        receipt = package_built_source(prefix, source, build, tools, record, work)
    Path('/tmp/z3666-build-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    Path('/tmp/z3666-resolved.txt').write_text(subprocess.check_output(
        [str(prefix/'bin/python'), '-m', 'pip', 'freeze'], text=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-z3666'))
    install(parser.parse_args().prefix)
