"""Prepare the two original pure-Python SDKs and their exact runtime dependencies."""
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
sys.path.insert(0,str(ROOT))
from verdugo import local_symbolic666 as sdk
from install_final import download


def install(prefix):
    if sys.version_info[:2] != (3,12):
        raise ValueError('Use the reviewed Python 3.12 profile')
    record = json.loads(sdk.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True,symlinks=False).create(prefix)
    for p in (prefix/'bin').glob('python*'):
        if not p.is_symlink():p.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='symbolic666-build-') as tmp:
        work = Path(tmp); tools = work/'tools'; wheels = work/'wheels'; wheels.mkdir()
        venv.EnvBuilder(with_pip=True,symlinks=False).create(tools)
        subprocess.run([str(tools/'bin/python'),'-m','pip','install',
                        *[k+'=='+v for k,v in record['build_tools'].items()]],check=True)
        for source in record['records']:
            archive = work/(source['id']+'.tar.gz')
            download(source['archive_url'],archive,source['archive_sha256'])
            dest = work/source['id']
            with tarfile.open(archive) as tar:tar.extractall(dest,filter='data')
            original = next(dest.iterdir())
            for entry in source['files']:
                data = (original/entry['path']).read_bytes()
                if (hashlib.sha256(data).hexdigest()!=entry['sha256'] or
                        hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=entry['blob_sha']):
                    raise ValueError('Symbolic source differs from Git evidence')
            env = dict(os.environ,**source.get('version_evidence',{}).get('archive_build_environment',{}))
            subprocess.run([str(tools/'bin/python'),'-m','pip','wheel','--no-deps','--no-build-isolation',
                            str(original),'-w',str(wheels)],env=env,check=True)
            for dependency in source['dependencies']:
                path = wheels/dependency['url'].rsplit('/',1)[1]
                download(dependency['url'],path,dependency['sha256'])
        subprocess.run([str(prefix/'bin/python'),'-m','pip','install','--no-index',
                        *[str(p) for p in sorted(wheels.glob('*.whl'))],
                        '--report','/tmp/symbolic666-pip-report.json'],check=True)
        subprocess.run([str(prefix/'bin/python'),'-m','pip','check'],check=True)
        probe = ('import sys;sys.path.insert(0,'+repr(str(ROOT))+');'
                 'from verdugo import local_symbolic666 as s;'
                 'assert all(s.runtime_state(i)["version_matches"] for i in s.SPECS)')
        subprocess.run([str(prefix/'bin/python'),'-I','-c',probe],check=True)
    Path('/tmp/symbolic666-resolved.txt').write_text(subprocess.check_output(
        [str(prefix/'bin/python'),'-m','pip','freeze'],text=True))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix',type=Path,default=Path('/tmp/verdugo-symbolic666'))
    install(parser.parse_args().prefix)
