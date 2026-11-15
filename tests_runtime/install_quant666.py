"""Build original bitsandbytes CPU library outside Engine."""
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
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verdugo import local_quant666 as quant
from install_final import download


def verify_source(source, record):
    for entry in record['files']:
        data=(source/entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest()!=entry['sha256'] or
            hashlib.sha1(b'blob '+str(len(data)).encode()+bytes([0])+data).hexdigest()!=entry['blob_sha']):
            raise ValueError('bitsandbytes original source differs from pinned Git tree')


def record_installation(prefix, source, record):
    verify_source(source,record)
    caches=list((source/'build').glob('temp.*/_skbuild/CMakeCache.txt'))
    if len(caches)!=1:
        raise ValueError('Expected one original CPU CMake build')
    cache=caches[0].read_text()
    required=['COMPUTE_BACKEND:STRING=cpu', 'CMAKE_DISABLE_FIND_PACKAGE_OpenMP:UNINITIALIZED=TRUE',
              'HAS_AVX512F_FLAG:UNINITIALIZED=FALSE','HAS_AVX512BF16_FLAG:UNINITIALIZED=FALSE']
    if not all(line in cache.splitlines() for line in required):
        raise ValueError('Original CPU CMake options differ')
    receipt={'schema':'verdugo.bitsandbytes666.operator-build.v1',
        **{key:record[key] for key in ('commit','archive_sha256','build_tools','torch_version','build_environment')},
        'native_sha256':hashlib.sha256((prefix/quant.NATIVE).read_bytes()).hexdigest(),
        'cmake_cache_sha256':hashlib.sha256(cache.encode()).hexdigest(),
        'checked_cmake_options':required,
        'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
        'independent_build_attestation':False,'reproducible_binary_build_proven':False}
    dest=prefix/quant.RECEIPT;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(receipt,indent=2)+'\n')
    quant.verify_build(prefix,record)
    return receipt


def install(prefix):
    if sys.version_info[:2]!=(3,12):raise ValueError('Use the reviewed Python 3.12 profile')
    record=json.loads(quant.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True,symlinks=False).create(prefix)
    python=str(prefix/'bin/python')
    for p in (prefix/'bin').glob('python*'):
        if not p.is_symlink():p.chmod(0o755)
    constraints=ROOT/'requirements/runtime-quant666.constraints.txt'
    torch='https://download-r2.pytorch.org/whl/cpu/torch-2.9.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl#sha256=7417d8c565f219d3455654cb431c6d892a3eb40246055e14d645422de13b9ea1'
    subprocess.run([python,'-m','pip','install',torch,'-c',str(constraints),
        'cmake==4.1.3','scikit-build-core==1.1.2','setuptools==84.2.1',
        'trove-classifiers==2026.9.21.13','numpy==2.5.4','packaging==26.3'],check=True)
    env=dict(os.environ,**record['build_environment'])
    env['PATH']=str(prefix/'bin')+os.pathsep+os.defpath
    env.pop('BNB_SKIP_CMAKE',None)
    with tempfile.TemporaryDirectory(prefix='bnb666-build-') as tmp:
        work=Path(tmp)
        download(record['archive_url'],work/'source.tar.gz',record['archive_sha256'])
        with tarfile.open(work/'source.tar.gz') as archive:archive.extractall(work/'source',filter='data')
        source=next((work/'source').iterdir());verify_source(source,record)
        subprocess.run([python,'-m','pip','install','--no-build-isolation',
            '-c',str(constraints),str(source),'--report','/tmp/bnb666-pip-report.json'],env=env,check=True)
        subprocess.run([python,'-m','pip','check'],check=True)
        receipt=record_installation(prefix,source,record)
    Path('/tmp/bnb666-build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    Path('/tmp/bnb666-resolved.txt').write_text(subprocess.check_output([python,'-m','pip','freeze'],text=True))
    print(json.dumps({'prepared':True,'commit':record['commit'],'source_built':True,'prefix':str(prefix)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',default='/tmp/verdugo-bnb666')
    args=parser.parse_args();install(Path(args.prefix))
