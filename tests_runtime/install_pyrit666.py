"""Explicit original source build, with upstream provenance, outside Engine."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import local_toolaudit666
from install_final import NODE_SHA, download


def install():
    home = Path('/tmp/verdugo-pyrit666')
    subprocess.run([sys.executable, '-m', 'venv', '--copies', str(home)], check=True)
    build = home / 'build'; build.mkdir(exist_ok=True)
    record = json.loads(local_toolaudit666.CONTRACT.read_text())
    download(record['archive_url'], build / 'source.tar.gz', record['archive_sha256'])
    with tarfile.open(build / 'source.tar.gz') as archive:
        archive.extractall(build, filter='data')
    source = build / ('PyRIT-' + record['commit'])
    for entry in record['files']:
        if hashlib.sha256((source / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('PyRIT original source hash mismatch')
    download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz',
             build / 'node.tar.xz', NODE_SHA)
    with tarfile.open(build / 'node.tar.xz') as archive:
        archive.extractall(build, filter='data')
    node = build / 'node-v24.22.1-linux-x64'
    env = os.environ | record['build_environment'] | {
        'PATH': str(node / 'bin') + os.pathsep + os.environ.get('PATH', os.defpath),
        'PIP_CONSTRAINT': str(ROOT / 'requirements/runtime-pyrit666.constraints.txt')}
    python = str(home / 'bin/python')
    subprocess.run([python, '-m', 'pip', 'install', str(source),
                    '-c', str(ROOT / 'requirements/runtime-pyrit666.constraints.txt'),
                    '--report', '/tmp/pyrit666-pip-report.json'], env=env, check=True)
    subprocess.run([python, '-m', 'pip', 'check'], check=True)
    with open('/tmp/pyrit666-resolved.txt', 'w') as output:
        subprocess.run([python, '-m', 'pip', 'freeze'], stdout=output, check=True)
    command = ('import sys; sys.path.insert(0, ' + repr(str(ROOT)) + '); '
               'from verdugo.local_toolaudit666 import verify_source; '
               'print(verify_source())')
    subprocess.run([python, '-I', '-c', command], check=True)
    shutil.rmtree(build)


if __name__ == '__main__':
    install()
