"""Administrator-only original source builds for ephemeral database acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdugo import local_database as db
from install_final import download

BUILD_TOOLS = [
    ('https://deb.debian.org/debian/pool/main/b/bison/bison_3.8.2%2bdfsg-1%2bb1_amd64.deb',
     'a414afd7519c53bfa33415ba5b951bc8b4906877004c49723ffda50a6033c3e8'),
    ('https://deb.debian.org/debian/pool/main/f/flex/flex_2.6.4-8.2_amd64.deb',
     'da3fd55dbb6aff4f7b3187580813e0ef707d0c596402e37c8fd144df60003636'),
    ('https://deb.debian.org/debian/pool/main/m/m4/m4_1.4.19-3_amd64.deb',
     'b2dd7bfca426712416e651bb5ff6dabe7d05e4caebbac61d714dbe261b31e4c3'),
]
PG_URL = 'https://ftp.postgresql.org/pub/source/v18.7/postgresql-18.7.tar.bz2'
REPOSITORIES = {'valkey':'valkey-io/valkey', 'pgvector':'pgvector/pgvector', 'apache-age':'apache/age'}


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def source(build, sid):
    path = build / sid; path.mkdir()
    for args in (['git','init','-q'], ['git','fetch','--depth=1','https://github.com/'+REPOSITORIES[sid]+'.git',db.SPECS[sid][2]],
                 ['git','checkout','--detach','FETCH_HEAD']):
        subprocess.run(args, cwd=path, check=True)
    actual = subprocess.check_output(['git','rev-parse','HEAD'], cwd=path, text=True).strip()
    if actual != db.SPECS[sid][2]:
        raise ValueError('Unexpected source checkout')
    return path


def manifest(home):
    programs = {}
    for sid in db.SPECS:
        files = {}
        for directory in ('bin','lib','share'):
            for path in sorted((home/directory).rglob('*')):
                if not path.is_file() or path.is_symlink():
                    continue
                name = str(path.relative_to(home))
                group = ('valkey' if name in ('bin/valkey-server','bin/valkey-cli') else
                         'pgvector' if name == 'lib/postgresql/vector.so' or name.startswith('share/postgresql/extension/vector') else
                         'apache-age' if name == 'lib/postgresql/age.so' or name.startswith('share/postgresql/extension/age') else 'postgres')
                if group == sid:
                    files[name] = digest(path)
        record = {'source_version':db.SPECS[sid][2], 'source_dirty':False, 'files':files}
        if sid == 'postgres':
            record['archive_sha256'] = db.PG_ARCHIVE_SHA
        programs[sid] = record
    (home/'manifest.json').write_text(json.dumps({'programs':programs},indent=2)+'\n')


def install():
    home, build = Path('/tmp/verdugo-database021'), Path('/tmp/verdugo-database-build021')
    home.mkdir(); build.mkdir()
    tool_root = build / 'tools'; tool_root.mkdir()
    for index, (url, sha) in enumerate(BUILD_TOOLS):
        archive = build / ('tool-'+str(index)+'.deb')
        download(url, archive, sha)
        subprocess.run(['dpkg-deb','-x',str(archive),str(tool_root)],check=True)
    env = dict(os.environ, PATH=str(tool_root/'usr/bin')+os.pathsep+os.defpath,
               BISON_PKGDATADIR=str(tool_root/'usr/share/bison'), M4=str(tool_root/'usr/bin/m4'))
    pg_archive = build / 'postgres.tar.bz2'
    download(PG_URL, pg_archive, db.PG_ARCHIVE_SHA)
    with tarfile.open(pg_archive) as archive:
        archive.extractall(build, filter='data')
    pg = build / 'postgresql-18.7'
    subprocess.run(['./configure','--prefix='+str(home),'--without-icu','--without-readline','--without-zlib'],cwd=pg,env=env,check=True)
    subprocess.run(['make','-j2'],cwd=pg,env=env,check=True)
    subprocess.run(['make','install'],cwd=pg,env=env,check=True)
    pg_config = 'PG_CONFIG='+str(home/'bin/pg_config')
    for sid in REPOSITORIES:
        path = source(build, sid)
        if sid == 'valkey':
            subprocess.run(['make','-j2','MALLOC=libc','BUILD_TLS=no'],cwd=path,env=env,check=True)
            for name in ('valkey-server','valkey-cli'):
                shutil.copy2(path/'src'/name,home/'bin'/name)
            version = subprocess.check_output([str(home/'bin/valkey-server'),'--version'],text=True)
            if 'sha='+db.SPECS[sid][2][:8]+':0' not in version:
                raise ValueError('Valkey source revision is not clean and pinned')
        else:
            subprocess.run(['make','-j2',pg_config,'OPTFLAGS='],cwd=path,env=env,check=True)
            subprocess.run(['make',pg_config,'install'],cwd=path,env=env,check=True)
        subprocess.run(['git','diff','--quiet'],cwd=path,check=True)
    version = subprocess.check_output([str(home/'bin/postgres'),'--version'],text=True)
    if version.strip() != 'postgres (PostgreSQL) 18.7':
        raise ValueError('Unexpected PostgreSQL release')
    manifest(home)
    os.environ[db.ENV] = str(home)
    for sid in db.SPECS:
        if not db.runtime_state(sid)['version_matches']:
            raise ValueError('Incomplete native database runtime')
    proof = {'scope':'Original local servers; private Unix sockets by default; no production deployment',
             'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
             'postgres_archive':{'url':PG_URL,'sha256':db.PG_ARCHIVE_SHA},
             'build_tools':[{'url':url,'sha256':sha} for url,sha in BUILD_TOOLS],
             'programs':json.loads((home/'manifest.json').read_text())['programs']}
    Path('/tmp/database021-resolved.txt').write_text(json.dumps(proof,indent=2)+'\n')
    shutil.rmtree(build)


if __name__ == '__main__':
    install()
