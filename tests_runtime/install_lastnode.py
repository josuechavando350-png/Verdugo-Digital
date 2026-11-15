"""Explicit pinned npm and Chromium installation for original local tool tests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
from install_final import download,NODE_SHA,ROOT
from verdugo import local_lastnode
CHROME_URL='https://storage.googleapis.com/chrome-for-testing-public/158.0.8127.18/linux64/chrome-linux64.zip'
CHROME_SHA='c6cb06e1574ac2f6c5c38e31551157fbcaa67e6366c89974084553c5a5772592'
def install():
 home=Path('/tmp/verdugo-lastnode021');home.mkdir();build=home/'build';build.mkdir()
 archive=build/'node.tar.xz';download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz',archive,NODE_SHA)
 with tarfile.open(archive) as tar:tar.extractall(build,filter='data')
 native=build/'node-v24.22.1-linux-x64';(home/'bin').mkdir();shutil.copy2(native/'bin/node',home/'bin/node')
 for source,dest in [('runtime-lastnode.package.json','package.json'),('runtime-lastnode.lock.json','package-lock.json')]:shutil.copy2(ROOT/'requirements'/source,home/dest)
 env=dict(os.environ,PATH=str(home/'bin')+os.pathsep+os.defpath)
 subprocess.run([str(home/'bin/node'),str(native/'lib/node_modules/npm/bin/npm-cli.js'),'ci','--ignore-scripts','--no-audit','--no-fund'],cwd=home,env=env,check=True)
 archive=build/'chrome.zip';download(CHROME_URL,archive,CHROME_SHA)
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   if Path(info.filename).is_absolute() or '..' in Path(info.filename).parts:raise ValueError('Unsafe Chromium archive')
  z.extractall(home/'chromium')
  for info in z.infolist():
   target=home/'chromium'/info.filename;mode=info.external_attr>>16
   if target.is_file() and mode:target.chmod(mode&0o777)
 os.environ[local_lastnode.ENV]=str(home)
 if not local_lastnode.runtime_state('landscape-app')['version_matches']:raise ValueError('Original node sources and profile mismatch')
 Path('/tmp/lastnode021-resolved.txt').write_text(json.dumps({'node':'24.22.1','node_archive_sha256':NODE_SHA,'chrome_url':CHROME_URL,'chrome_sha256':CHROME_SHA,'lock_sha256':hashlib.sha256((home/'package-lock.json').read_bytes()).hexdigest()},indent=2)+'\n')
 shutil.rmtree(build)
if __name__=='__main__':install()
