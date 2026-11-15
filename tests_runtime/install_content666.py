"""Install the unchanged upstream MINIMAL build; no model/provider extras."""
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
from verdugo import local_content666 as sdk
from install_final import download


def install(prefix):
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Use the reviewed Python 3.12 profile')
    if prefix.exists():
        raise ValueError('Choose a new empty runtime prefix')
    record = json.loads(sdk.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    for p in (prefix/'bin').glob('python*'):
        if not p.is_symlink():
            p.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='content666-build-') as tmp:
        work = Path(tmp)
        tools = work/'tools'
        wheels = work/'wheels'
        wheels.mkdir()
        venv.EnvBuilder(with_pip=True, symlinks=False).create(tools)
        subprocess.run([str(tools/'bin/python'), '-m', 'pip', 'install',
                        *[k+'=='+v for k, v in record['build_tools'].items()]], check=True)
        archive = work/'source.tar.gz'
        download(record['archive_url'], archive, record['archive_sha256'])
        with tarfile.open(archive) as tar:
            tar.extractall(work/'source', filter='data')
        original = next((work/'source').iterdir())
        for entry in record['files']:
            data = (original/entry['path']).read_bytes()
            if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != entry['blob_sha']):
                raise ValueError('txtai source differs from original Git evidence')
        subprocess.run([str(tools/'bin/python'), '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                        str(original), '-w', str(wheels)], env=dict(os.environ, MINIMAL='1'), check=True)
        subprocess.run([str(prefix/'bin/python'), '-m', 'pip', 'install', '--no-index',
                        *[str(p) for p in wheels.glob('*.whl')],
                        '--report', '/tmp/content666-pip-report.json'], check=True)
        subprocess.run([str(prefix/'bin/python'), '-m', 'pip', 'check'], check=True)
        probe = ('import sys;sys.path.insert(0,'+repr(str(ROOT))+');'
                 'from verdugo import local_content666 as s;'
                 'assert s.runtime_state("txtai")["version_matches"]')
        subprocess.run([str(prefix/'bin/python'), '-I', '-c', probe], check=True)
    Path('/tmp/content666-resolved.txt').write_text(subprocess.check_output(
        [str(prefix/'bin/python'), '-m', 'pip', 'freeze'], text=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-content666'))
    install(parser.parse_args().prefix)
