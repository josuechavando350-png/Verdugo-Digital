"""Explicit offline-profile preparation, never invoked by the runtime."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdugo import local_volt666
from install_final import NODE_SHA, download


def install():
    home = Path('/tmp/verdugo-volt666'); home.mkdir()
    build = home/'build'; build.mkdir()
    download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz', build/'node.tar.xz', NODE_SHA)
    with tarfile.open(build/'node.tar.xz') as archive:
        archive.extractall(build, filter='data')
    native = build/'node-v24.22.1-linux-x64'
    (home/'bin').mkdir(); shutil.copy2(native/'bin/node', home/'bin/node')
    for name in ('package.json', 'package-lock.json'):
        shutil.copy2(local_volt666.CONTRACT.parents[1]/'requirements/runtime-volt666'/name, home/name)
    subprocess.run([str(home/'bin/node'), str(native/'lib/node_modules/npm/bin/npm-cli.js'),
                    'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=home, check=True)
    os.environ[local_volt666.ENV] = str(home)
    if not local_volt666.runtime_state('voltagent')['version_matches']:
        raise ValueError('Npm bundle or dependency lock differs from reviewed profile')
    Path('/tmp/volt666-resolved.txt').write_text(json.dumps({
        'node_version': '24.22.1', 'node_archive_sha256': NODE_SHA,
        'registry_bundle_and_lock_verified': True, 'install_scripts_executed': False})+'\n')
    shutil.rmtree(build)


if __name__ == '__main__': install()
