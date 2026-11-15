"""Explicit CI/admin setup only; never imported by Engine, CLI or MCP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verdugo.local_cli import SPECS
from install_expansion import install
GROUPS={'content021':['graphiti','openbb','people-also-ask','jobspy'],
        'entities021':['chronos','gliner'],'pycli021':['dvc','dnstwist'],
        'node':['geo-lint','site-md','seo-graph','structured-data-validator'],
        'cli-security':['syft','grype','gitleaks'],'cli-storage':['restic','sops','vale']}
GO_SHA='9849f4e04ee35303714e34fbc3ac8ab44ea3e448a95aa182f91e3b9b79c710ec'
NODE_SHA='6c172a9ab6718f7b801fb5a7bd486af2ee5e32758086a04b84fcce2aa77095e6'
DB_SHA='762b01ba9c79e6a250bd73f11ef62fbf44539ee8e08e043d80df4aaad3afc2aa'
DB_URL='https://grype.anchore.io/databases/v6/vulnerability-db_v6.1.10_2026-11-14T00:20:33Z_1794637165.tar.zst'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def download(url,dest,sha):
    with urlopen(url,timeout=90) as source,dest.open('wb') as target:shutil.copyfileobj(source,target)
    if digest(dest)!=sha:raise ValueError('Downloaded artifact checksum mismatch')

def node():
    home=Path('/tmp/verdugo-node021');home.mkdir()
    archive=home/'node.tar.xz'
    download('https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz',archive,NODE_SHA)
    with tarfile.open(archive) as tar:tar.extractall(home,filter='data')
    native=home/'node-v24.22.1-linux-x64';(home/'bin').mkdir()
    shutil.copy2(native/'bin/node',home/'bin/node');(home/'bin/node').chmod(0o755)
    for source,dest in [('runtime-node.package.json','package.json'),('runtime-node.lock.json','package-lock.json')]:shutil.copy2(ROOT/'requirements'/source,home/dest)
    env=dict(os.environ,PATH=str(home/'bin')+os.pathsep+os.defpath)
    subprocess.run([str(home/'bin/node'),str(native/'lib/node_modules/npm/bin/npm-cli.js'),'ci','--ignore-scripts','--no-audit','--no-fund'],cwd=home,env=env,check=True)
    shutil.rmtree(native);archive.unlink()

def cli(selected):
    home=Path('/tmp/verdugo-cli021');home.mkdir();(home/'bin').mkdir()
    build=Path('/tmp/verdugo-cli-build021');build.mkdir();archive=build/'go.tar.gz'
    download('https://go.dev/dl/go1.26.11.linux-amd64.tar.gz',archive,GO_SHA)
    with tarfile.open(archive) as tar:tar.extractall(build,filter='data')
    archive.unlink();go=str(build/'go/bin/go')
    env=dict(os.environ,GOMAXPROCS='2',GOCACHE=str(build/'cache'),GOMODCACHE=str(build/'modules'),GOPATH=str(build/'gopath'))
    repositories={'gitleaks':'gitleaks/gitleaks','restic':'restic/restic','syft':'anchore/syft','grype':'anchore/grype','sops':'getsops/sops','vale':'vale-cli/vale'}
    manifest={'binaries':{}}
    for sid in selected:
        source=build/sid;source.mkdir()
        subprocess.run(['git','init','-q'],cwd=source,check=True)
        subprocess.run(['git','fetch','--depth=1','https://github.com/'+repositories[sid]+'.git',SPECS[sid][2]],cwd=source,check=True)
        subprocess.run(['git','checkout','--detach','FETCH_HEAD'],cwd=source,check=True)
        binary=home/'bin'/sid;package='.' if sid=='gitleaks' else './cmd/'+sid
        subprocess.run([go,'build','-p','2','-trimpath','-o',str(binary),package],cwd=source,env=env,check=True)
        provenance=subprocess.check_output([go,'version','-m',str(binary)],text=True)
        if 'vcs.revision='+SPECS[sid][2] not in provenance or 'vcs.modified=false' not in provenance:raise ValueError('Dirty or unexpected original build')
        binary.chmod(0o755);manifest['binaries'][sid]={'source_commit':SPECS[sid][2],'sha256':digest(binary)}
    if 'sops' in selected:
        subprocess.run([go,'install','-p','2','filippo.io/age/cmd/age-keygen@v1.3.1'],env=dict(env,GOBIN=str(home/'bin')),check=True)
        manifest['binaries']['sops'].update(age_keygen_version='v1.3.1',age_keygen_sha256=digest(home/'bin/age-keygen'))
    # Free build cache before unpacking the multi-gigabyte vulnerability snapshot.
    # Go marks extracted module directories read-only. Its cleanup command
    # handles permissions correctly for the unprivileged CI account.
    subprocess.run([go,'clean','-modcache'],env=dict(env,GOTOOLCHAIN='local'),check=True)
    shutil.rmtree(build)
    if 'grype' in selected:
        # Use the original client, including its documented checksum verification,
        # downloader, archive handling and public database request headers.
        source=DB_URL+'?checksum=sha256%3A'+DB_SHA
        subprocess.run([str(home/'bin/grype'),'db','import',source],
                       env=dict(os.environ,GRYPE_DB_CACHE_DIR=str(home/'grype-db'),
                                GRYPE_CHECK_FOR_APP_UPDATE='false'),check=True)
        db=home/'grype-db/6'
        if digest(db/'vulnerability.db')!='822674a9d4f3cbeff8db3f8f1795f8ce8684e6ef2a3636a1cf4cba130e8fc96e':
            raise ValueError('Imported vulnerability snapshot mismatch')
        manifest['binaries']['grype'].update(database_sha256=digest(db/'vulnerability.db'),database_source=DB_URL+'?checksum=sha256%3A'+DB_SHA)
    (home/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--group',choices=GROUPS,required=True);args=parser.parse_args()
    if args.group.endswith('021'):install(args.group)
    elif args.group=='node':node()
    else:cli(GROUPS[args.group])
