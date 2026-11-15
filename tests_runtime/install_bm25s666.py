"""Explicit source preparation of BM25S and NumPy; never called by Engine."""
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
from verdugo import local_bm25s666 as sdk
from install_final import download


def verify_source(source, files):
    for entry in files:
        data = (source/entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256']
                or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != entry['blob_sha']):
            raise ValueError('Original lexical source differs from reviewed Git bytes')


def record_installation(prefix, source, numpy_source, build, record):
    verify_source(source, record['files'])
    verify_source(numpy_source, record['numpy']['files'])
    options = json.loads((build/'meson-info/intro-buildoptions.json').read_text())
    selected = {r['name']:str(r['value']).lower() for r in options}
    if any(selected.get(k) != v for k,v in record['numpy_build_options'].items()):
        raise ValueError('NumPy source build options differ')
    if sdk.package_files(prefix/sdk.PACKAGE) != set(record['artifact_paths']):
        raise ValueError('Unexpected installed lexical artifact set')
    # Check ELF dependencies as data; do not invoke the built modules to audit linkage.
    needed = set()
    for path in record['artifact_paths']:
        if path.endswith('.so'):
            output = subprocess.check_output(['readelf','-d',str(prefix/sdk.PACKAGE/path)],text=True)
            for line in output.splitlines():
                if '(NEEDED)' in line: needed.add(line.split('[')[1].split(']')[0])
    if not needed <= {'libc.so.6','libm.so.6','libgcc_s.so.1'}:
        raise ValueError('Unexpected native library in no-BLAS NumPy build')
    receipt = {'schema':'verdugo.bm25s666.operator-build.v1',
               **{k:record[k] for k in ('commit','archive_sha256','build_tools','numpy_build_options')},
               'numpy_archive_sha256':record['numpy']['archive_sha256'],
               'artifacts':{p:hashlib.sha256((prefix/sdk.PACKAGE/p).read_bytes()).hexdigest() for p in record['artifact_paths']},
               'native_dynamic_dependencies':sorted(needed),
               'compiler':subprocess.check_output(['/usr/bin/gcc-14','--version'],text=True).splitlines()[0],
               'independent_build_attestation':False,'reproducible_binary_build_proven':False}
    dest = prefix/sdk.RECEIPT; dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(receipt,indent=2)+'\n')
    sdk.verify_build(prefix, record)
    return receipt


def install(prefix):
    if sys.version_info[:2] != (3,12) or sys.platform != 'linux':
        raise ValueError('Use the reviewed Linux Python 3.12 source profile')
    if prefix.exists():
        raise ValueError('Select a new empty profile location')
    record = json.loads(sdk.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True,symlinks=False).create(prefix)
    for p in (prefix/'bin').glob('python*'):
        if not p.is_symlink():p.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='bm25s666-build-') as tmp:
        work = Path(tmp); tools = work/'tools'; wheels = work/'wheels'; wheels.mkdir()
        venv.EnvBuilder(with_pip=True,symlinks=False).create(tools)
        python = str(tools/'bin/python')
        subprocess.run([python,'-m','pip','install','--no-cache-dir',
                        *[k+'=='+v for k,v in record['build_tools'].items()],
                        '--report','/tmp/bm25s666-build-tools-report.json'],check=True)
        subprocess.run([python,'-m','pip','check'],check=True)
        sources = []
        for name,row in [('bm25s',record),('numpy',record['numpy'])]:
            archive = work/(name+'.tar.gz')
            download(row['archive_url'],archive,row['archive_sha256'])
            dest = work/name
            with tarfile.open(archive) as tar:tar.extractall(dest,filter='data')
            source = next(dest.iterdir()); verify_source(source,row['files']); sources.append(source)
        original,numpy_source = sources
        env = dict(os.environ,PATH=str(tools/'bin')+os.pathsep+os.defpath,
                   CC='/usr/bin/gcc-14',CXX='/usr/bin/g++-14',PIP_NO_CACHE_DIR='1')
        # The archive's original setup.py fallback is 0.0.0; avoid ambient release labels.
        for key in ('BM25S_VERSION','RELEASE_TAG','GITHUB_REF_TYPE','GITHUB_REF_NAME','GITHUB_REF'):
            env.pop(key,None)
        build = work/'numpy-build'
        subprocess.run([python,'-m','pip','wheel','--no-deps','--no-build-isolation',
                        str(numpy_source),'-w',str(wheels),'-Cbuild-dir='+str(build),'-Ccompile-args=-j2',
                        *['-Csetup-args=-D'+k+'='+v for k,v in record['numpy_build_options'].items()]],env=env,check=True)
        subprocess.run([python,'-m','pip','wheel','--no-deps','--no-build-isolation',
                        str(original),'-w',str(wheels)],env=env,check=True)
        subprocess.run([str(prefix/'bin/python'),'-m','pip','install','--no-index',
                        *[str(p) for p in sorted(wheels.glob('*.whl'))],
                        '--report','/tmp/bm25s666-pip-report.json'],check=True)
        subprocess.run([str(prefix/'bin/python'),'-m','pip','check'],check=True)
        receipt = record_installation(prefix,original,numpy_source,build,record)
    Path('/tmp/bm25s666-build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    Path('/tmp/bm25s666-resolved.txt').write_text(subprocess.check_output(
        [str(prefix/'bin/python'),'-m','pip','freeze'],text=True))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix',type=Path,default=Path('/tmp/verdugo-bm25s666'))
    install(parser.parse_args().prefix)
