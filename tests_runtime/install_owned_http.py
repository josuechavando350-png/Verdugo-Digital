"""Install fixed original programs for owned-loopback-only operations."""
import json
import os
from pathlib import Path
import shutil
import tarfile
from install_final import download,NODE_SHA
from install_expansion import install as install_python
from verdugo import local_owned_http
SITE_URL='https://github.com/janreges/siteone-crawler/releases/download/v2.5.1/siteone-crawler-v2.5.1-linux-x64.tar.gz'
SITE_SHA='09278d958d4a087fa46093805cd33b085b96618001dd31d45c448ad724c9024e'
def install():
 install_python('sherlock021')
 home=Path('/tmp/verdugo-owned-http021');home.mkdir();(home/'bin').mkdir();build=home/'build';build.mkdir()
 download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz',build/'node.tar.xz',NODE_SHA)
 with tarfile.open(build/'node.tar.xz') as t:t.extractall(build,filter='data')
 shutil.copy2(build/'node-v24.22.1-linux-x64/bin/node',home/'bin/node')
 download(SITE_URL,build/'siteone.tar.gz',SITE_SHA)
 with tarfile.open(build/'siteone.tar.gz') as t:t.extractall(build/'siteone',filter='data')
 candidates=[p for p in (build/'siteone').rglob('siteone-crawler') if p.is_file()]
 if len(candidates)!=1:raise ValueError('Original SiteOne binary missing')
 shutil.copy2(candidates[0],home/'bin/siteone-crawler')
 os.environ[local_owned_http.ENV]=str(home);os.environ['VERDUGO_SHERLOCK021_PYTHON']='/tmp/verdugo-sherlock021-venv/bin/python'
 for sid in local_owned_http.SPECS:
  if not local_owned_http.runtime_state(sid)['version_matches']:raise ValueError('Original owned HTTP runtime unavailable: '+sid)
 Path('/tmp/network021-resolved.txt').write_text(json.dumps({'node_archive_sha256':NODE_SHA,'siteone_url':SITE_URL,'siteone_archive_sha256':SITE_SHA,'native_files':local_owned_http.FILES},indent=2)+'\n');shutil.rmtree(build)
if __name__=='__main__':install()
