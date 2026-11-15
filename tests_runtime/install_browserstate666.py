"""Build the pinned Python SDK and its original driver outside Engine."""
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
from verdugo import local_browserstate666 as browserstate
from install_final import download, NODE_SHA


def checkout(path, repository, commit):
    path.mkdir()
    subprocess.run(['git', 'init', '-q'], cwd=path, check=True)
    subprocess.run(['git', 'fetch', '--depth=1', 'https://github.com/' + repository + '.git', commit],
                   cwd=path, check=True)
    subprocess.run(['git', 'checkout', '--detach', 'FETCH_HEAD'], cwd=path, check=True)
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, text=True).strip() != commit:
        raise ValueError('Wrong original source commit')


def verify_source(path, records):
    for entry in records:
        raw = (path / entry['path']).read_bytes()
        if (hashlib.sha256(raw).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != entry['blob_sha']):
            raise ValueError('Original Python SDK or driver source changed')


def install(prefix):
    record = json.loads(browserstate.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = prefix / 'bin/python'
    for path in (prefix / 'bin').glob('python*'):
        if not path.is_symlink(): path.chmod(0o755)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r',
                    str(ROOT / 'requirements/runtime-browserstate666.build.txt')], check=True)
    with tempfile.TemporaryDirectory(prefix='browserstate666-build-') as tmp:
        work = Path(tmp)
        download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz', work/'node.tar.xz', NODE_SHA)
        with tarfile.open(work/'node.tar.xz') as archive:
            archive.extractall(work, filter='data')
        env = dict(os.environ, PATH=str(work/'node-v24.22.1-linux-x64/bin') + os.pathsep + os.environ['PATH'],
                   **record['build_environment'])
        source = work/'source'
        checkout(source, record['repository'], record['commit'])
        driver = source/'.upstream'
        checkout(driver, record['driver']['repository'], record['driver']['commit'])
        verify_source(source, record['files']); verify_source(driver, record['driver']['files'])
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-build-isolation',
                        '-c', str(ROOT / 'requirements/runtime-browserstate666.build.txt'), str(source),
                        '--report', '/tmp/browserstate666-pip-report.json'], check=True, env=env)
        verify_source(source, record['files']); verify_source(driver, record['driver']['files'])
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
        browserstate.verify_artifacts(prefix, record)
    Path('/tmp/browserstate666-resolved.txt').write_text(json.dumps({
        'source_commit': record['commit'], 'driver_source_commit': record['driver']['commit'],
        'version': record['version'], 'verified_python_source_files': record['source_python_files_verified'],
        'verified_installed_artifacts': len(record['installed_artifacts']),
        'browser_binaries_installed': False, 'npm_install_scripts_executed': False,
        'node_version': record['node']['version'], 'node_binary_sha256': record['node']['binary_sha256']}, indent=2)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--prefix',type=Path,default=Path('/tmp/verdugo-browserstate666-venv'))
    install(p.parse_args().prefix)
