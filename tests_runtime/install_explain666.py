"""Build original InterpretML C++, frontend and Python package outside Engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import local_explain666 as explain
from install_final import download, digest


def verify_source(source, record):
    for entry in record['files']:
        data = (source / entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()
                != entry['blob_sha']):
            raise ValueError('Interpret source differs from pinned Git tree')


def record_installation(prefix, source, record):
    verify_source(source, record)
    receipt = {'schema': 'verdugo.interpret666.operator-build.v1',
        'commit': record['commit'], 'archive_sha256': record['archive_sha256'],
        'build_arguments': ['-release_64'], 'npm_lock_sha256': record['npm_lock_sha256'],
        'compiler': subprocess.check_output(['c++', '--version'], text=True).splitlines()[0],
        'node_version': record['node_version'],
        'artifacts': {name: digest(prefix / explain.PACKAGE / name) for name in explain.BUILD_FILES},
        'independent_build_attestation': False, 'reproducible_binary_build_proven': False}
    dest = prefix / explain.RECEIPT; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + '\n')
    explain.verify_build(prefix, record)
    return receipt


def install(prefix, archive_file=None):
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Use tested Python 3.12 source installer')
    record = json.loads(explain.CONTRACT.read_text())
    lock = ROOT / 'requirements/runtime-interpret666.lock.json'
    if digest(lock) != record['npm_lock_sha256']:
        raise ValueError('Frontend dependency lock changed')
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = str(prefix / 'bin/python')
    constraints = ROOT / 'requirements/runtime-interpret666.constraints.txt'
    subprocess.run([python, '-m', 'pip', 'install', '-r', str(constraints)], check=True)
    with tempfile.TemporaryDirectory(prefix='interpret666-build-') as temp:
        work = Path(temp)
        archive_path = archive_file or work / 'source.tar.gz'
        if archive_file:
            if digest(archive_path) != record['archive_sha256']:
                raise ValueError('Administrator source archive checksum mismatch')
        else:
            download(record['archive_url'], archive_path, record['archive_sha256'])
        with tarfile.open(archive_path) as archive:
            archive.extractall(work, filter='data')
        source = work / ('interpret-' + record['commit'])
        verify_source(source, record)
        download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz',
                 work / 'node.tar.xz', record['node_archive_sha256'])
        with tarfile.open(work / 'node.tar.xz') as archive:
            archive.extractall(work, filter='data')
        node = work / 'node-v24.22.1-linux-x64'
        env = dict(os.environ, PATH=str(node / 'bin') + os.pathsep + os.defpath,
                   npm_config_cache=str(work / 'npm-cache'))
        js = source / 'shared/vis'; shutil.copy2(lock, js / 'package-lock.json')
        subprocess.run([str(node / 'bin/npm'), 'ci', '--ignore-scripts', '--no-audit', '--no-fund'],
                       cwd=js, env=env, check=True)
        subprocess.run([str(node / 'bin/npm'), 'run', 'build-prod'], cwd=js, env=env, check=True)
        subprocess.run(['/bin/sh', 'build.sh', '-release_64'], cwd=source, check=True)
        dest = source / 'python/interpret-core/interpret/root/bld/lib'
        dest.mkdir(parents=True, exist_ok=True)
        # The unchanged upstream setup.py expressly requires manual copying of
        # prebuilt native artifacts for a wheel built from a repository checkout.
        for artifact in [source / 'bld/lib/libebm_linux_x64.so',
                         js / 'dist/interpret-inline.js', js / 'dist/interpret-inline.js.LICENSE.txt']:
            shutil.copy2(artifact, dest / artifact.name)
        subprocess.run([python, '-m', 'pip', 'install', '--no-build-isolation',
                        '-c', str(constraints), str(source / 'python/interpret-core'),
                        '--report', '/tmp/interpret666-pip-report.json'], env=env, check=True)
        receipt = record_installation(prefix, source, record)
    subprocess.run([python, '-m', 'pip', 'check'], check=True)
    with open('/tmp/interpret666-resolved.txt', 'w') as out:
        subprocess.run([python, '-m', 'pip', 'freeze'], stdout=out, check=True)
    Path('/tmp/interpret666-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-interpret666'))
    parser.add_argument('--archive-file', type=Path)
    args = parser.parse_args()
    install(args.prefix.resolve(), args.archive_file.resolve() if args.archive_file else None)
