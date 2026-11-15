"""Explicit admin setup for the source functions and original Maps parser."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from install_expansion import install as install_python
from install_final import download,GO_SHA
from verdugo import local_cli


def install():
 install_python('source021')
 home=Path('/tmp/verdugo-maps021');home.mkdir();(home/'bin').mkdir()
 build=home/'build';build.mkdir();archive=build/'go.tar.gz'
 download('https://go.dev/dl/go1.26.11.linux-amd64.tar.gz',archive,GO_SHA)
 with tarfile.open(archive) as t:t.extractall(build,filter='data')
 env=dict(os.environ,GOTOOLCHAIN='local',GOMAXPROCS='2',CGO_ENABLED='0',GOPROXY='off',GOSUMDB='off',GOCACHE=str(build/'cache'))
 source=build/'source';shutil.copytree(local_cli.MAPS_SOURCE,source)
 binary=home/'bin/google-maps-scraper'
 subprocess.run([str(build/'go/bin/go'),'build','-trimpath','-buildvcs=false','-ldflags=-s -w','-o',str(binary),'.'],cwd=source,env=env,check=True)
 manifest={'binaries':{'google-maps-scraper':{'source_commit':local_cli.SPECS['google-maps-scraper'][2],
           'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'original_sources':local_cli.MAPS_FILES,
           'go_archive_sha256':GO_SHA,'scope':'Original EntryFromJSON and Validate; fixed first-party projection; no network'}}}
 (home/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 os.environ[local_cli.ENV]=str(home)
 if not local_cli.runtime_state('google-maps-scraper')['version_matches']:raise ValueError('Compiled parser runtime unavailable')
 Path('/tmp/maps021-resolved.txt').write_text(json.dumps(manifest,indent=2)+'\n')
 shutil.rmtree(build)

if __name__=='__main__':install()
