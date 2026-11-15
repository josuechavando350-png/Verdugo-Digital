"""Explicit setup of original, hash-pinned native tools; never called by Engine."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verdugo import local_native_tools as nt
from install_final import download

ARTIFACTS = [
 ('java.tar.gz','https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz','d7f5d5cf865a2902b70ff549b97586a7d3f234e016f041ab447ea740c7d66d1c'),
 ('arx.jar','https://github.com/arx-deidentifier/arx/releases/download/v3.9.2/libarx-3.9.2.jar','18040108e95ca7955d806bf32354b20601d664495653b8ee169d249f43f58d44'),
 ('openapi.jar','https://repo.maven.apache.org/maven2/org/openapitools/openapi-generator-cli/7.27.0/openapi-generator-cli-7.27.0.jar','db9c4b738727698748746144394cb7ee96512fe50166555baaeeca9311ee1dba'),
 ('webgraph.jar','https://repo.maven.apache.org/maven2/it/unimi/dsi/webgraph/3.6.12/webgraph-3.6.12.jar','8daddd3881aecc7095643936c9e16d825cbe0e431df507519e36df68d06444ef'),
 ('fastutil.jar','https://repo.maven.apache.org/maven2/it/unimi/dsi/fastutil-core/8.5.19/fastutil-core-8.5.19.jar','57ad7ac9f7aef23317446e996732236b18e1eaf07638c4325b6f464cf69c18ab'),
 ('goaccess.deb','https://deb.debian.org/debian/pool/main/g/goaccess/goaccess_1.7-1_amd64.deb','dff0257b8938861df93101e0d4466a145b54f6bfa1eb1e1cc161d721d6f25973'),
 ('maxmind.deb','https://deb.debian.org/debian/pool/main/libm/libmaxminddb/libmaxminddb0_1.7.1-1_amd64.deb','78f4bf04567160dc2f8704a0a766bbda9241b5cf8b3d557c9442c51dac803707'),
]


def install():
 home=Path('/tmp/verdugo-java021');home.mkdir()
 build=home/'build';build.mkdir()
 for name,url,sha in ARTIFACTS:download(url,build/name,sha)
 with tarfile.open(build/'java.tar.gz') as tar:tar.extractall(build,filter='data')
 shutil.move(str(build/'jdk-21.0.13+9'),str(home/'jdk'))
 for path in (home/'jdk').rglob('*'):
  if path.is_symlink():
   resolved=path.resolve()
   if not resolved.is_relative_to(home/'jdk'):raise ValueError('Unexpected Java runtime link')
   if resolved.is_file():raw=resolved.read_bytes();path.unlink();path.write_bytes(raw)
 for path in build.glob('*.jar'):shutil.copy2(path,home/path.name)
 package=build/'packages';package.mkdir()
 for name in ('goaccess.deb','maxmind.deb'):subprocess.run(['dpkg-deb','-x',str(build/name),str(package)],check=True)
 (home/'goaccess/bin').mkdir(parents=True);(home/'goaccess/lib').mkdir(parents=True)
 shutil.copy2(package/'usr/bin/goaccess',home/'goaccess/bin/goaccess')
 shutil.copy2(package/'usr/lib/x86_64-linux-gnu/libmaxminddb.so.0',home/'goaccess/lib/libmaxminddb.so.0')
 (home/'classes').mkdir()
 subprocess.run([str(home/'jdk/bin/javac'),'-proc:none','-cp',str(home/'*'),'-d',str(home/'classes'),
                 str(nt.SOURCE/'CountingMergedIntIterator.java'),str(nt.SOURCE/'VerdugoJavaWorker.java')],check=True)
 os.environ[nt.ENV]=str(home)
 for sid in nt.SPECS:
  if not nt.runtime_state(sid)['version_matches']:raise ValueError('Original runtime or compiled bridge differs from pinned files: '+sid)
 env=dict(os.environ,LD_LIBRARY_PATH=str(home/'goaccess/lib'))
 subprocess.run(['ldd',str(home/'goaccess/bin/goaccess')],env=env,check=True)
 subprocess.run([str(home/'goaccess/bin/goaccess'),'--version'],env=env,check=True)
 subprocess.run([str(home/'jdk/bin/java'),'-version'],check=True)
 proof={'runtime':nt.contract()['runtime'],'artifacts':[{'name':n,'url':u,'sha256':s} for n,u,s in ARTIFACTS],
        'files_verified':len(nt.contract()['files']),'operations':{s:v[0] for s,v in nt.SPECS.items()},
        'scope':'Bounded supplied data, fixed original programs; not production certification'}
 Path('/tmp/tools021-resolved.txt').write_text(json.dumps(proof,indent=2)+'\n')
 shutil.rmtree(build)

if __name__=='__main__':install()
