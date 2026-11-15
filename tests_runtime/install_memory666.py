"""Build only the fixed original MCP memory server, outside Engine."""
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
from verdugo import local_memory666
from install_final import NODE_SHA, download


def install():
    home = Path('/tmp/verdugo-memory666'); home.mkdir(exist_ok=True)
    build = home / 'build'; build.mkdir(exist_ok=True)
    contract = json.loads(local_memory666.CONTRACT.read_text())
    download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz', build/'node.tar.xz', NODE_SHA)
    with tarfile.open(build/'node.tar.xz') as archive:
        archive.extractall(build, filter='data')
    native = build / 'node-v24.22.1-linux-x64'
    (home/'bin').mkdir(exist_ok=True); shutil.copyfile(native/'bin/node', home/'bin/node')
    (home/'bin/node').chmod(0o755)
    download(contract['archive_url'], build/'source.tar.gz', contract['archive_sha256'])
    wanted = {f['path']: f['sha256'] for f in contract['files']}
    copied = set()
    with tarfile.open(build/'source.tar.gz') as archive:
        for member in archive.getmembers():
            name = '/'.join(Path(member.name).parts[1:])
            if name not in wanted:
                continue
            if not member.isfile() or name in copied:
                raise ValueError('Unexpected original source member')
            raw = archive.extractfile(member).read()
            if hashlib.sha256(raw).hexdigest() != wanted[name]:
                raise ValueError('Original MCP memory source changed')
            dest = home/'upstream'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw); copied.add(name)
    if copied != set(wanted):
        raise ValueError('Missing original source')
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(ROOT/'requirements/runtime-memory666'/name, home/name)
    subprocess.run([str(home/'bin/node'), str(native/'lib/node_modules/npm/bin/npm-cli.js'),
                    'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=home, check=True)
    subprocess.run([str(home/'bin/node'), str(home/'node_modules/typescript/bin/tsc'),
                    '-p', str(home/'upstream/src/memory')], cwd=home, check=True)
    os.environ[local_memory666.ENV] = str(home)
    if not local_memory666.runtime_state('servers')['version_matches']:
        raise ValueError('MCP memory build differs from verified original build')
    Path('/tmp/memory666-resolved.txt').write_text(json.dumps({
        'original_memory_source_commit': contract['commit'],
        'typescript_version': contract['typescript_version'], 'node_version': contract['node_version'],
        'compiled_artifacts_verified': True, 'sdk_source_maps_verified': 3,
        'install_scripts_executed': False})+'\n')
    shutil.rmtree(build)


if __name__ == '__main__': install()
