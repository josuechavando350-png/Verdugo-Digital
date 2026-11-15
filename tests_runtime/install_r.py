"""Explicit administrator setup of the pinned R runtime; never called by Engine."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdugo import local_r
from install_final import download

ARTIFACTS = [
    ('https://deb.debian.org/debian/pool/main/r/r-base/r-base-core_4.2.2.20221110-2_amd64.deb',
     'cfc8aafc639333d16d9019c7d498ced00fc3565b153682a9d9baa48b9eb96a38'),
    ('https://deb.debian.org/debian/pool/main/i/icu/libicu72_72.1-3+deb12u1_amd64.deb',
     'f7f6f99c6d7b025914df2447fc93e11d22c44c0c8bdd8b6f36691c9e7ddcef88'),
]


def install():
    home = Path('/tmp/verdugo-r021')
    home.mkdir()
    for index, (url, digest) in enumerate(ARTIFACTS):
        archive = home / ('archive-' + str(index) + '.deb')
        download(url, archive, digest)
        subprocess.run(['dpkg-deb', '-x', str(archive), str(home)], check=True)
        archive.unlink()
    # Debian packages link to /etc/R. Relocate only those known config links
    # to the exact packaged contents, without invoking root package scripts.
    etc = home / 'usr/lib/R/etc'
    for name in ('Makeconf', 'Renviron', 'Renviron.site', 'Rprofile.site', 'ldpaths', 'repositories'):
        dest = etc / name
        if dest.is_symlink():
            dest.unlink()
        source = etc / 'Renviron.ucf' if name == 'Renviron' else home / 'etc/R' / name
        shutil.copyfile(source, dest)
    import os
    os.environ[local_r.ENV] = str(home)
    for service in local_r.SPECS:
        if not local_r.runtime_state(service)['version_matches']:
            raise ValueError('Extracted runtime differs from the reviewed R distribution')
    # A binary checksum does not establish dynamic-link compatibility. Check
    # native dependencies and package loading explicitly before acceptance.
    r_home = home / 'usr/lib/R'
    env = dict(os.environ, R_HOME=str(r_home),
               LD_LIBRARY_PATH=str(r_home/'lib')+':'+str(home/'usr/lib/x86_64-linux-gnu'))
    subprocess.run(['ldd', str(r_home/'bin/exec/R')], env=env, check=True)
    subprocess.run([str(r_home/'bin/exec/R'), '--vanilla', '--slave', '-e',
                    'stopifnot(as.character(getRversion()) == "4.2.2", requireNamespace("stats", quietly=TRUE), requireNamespace("methods", quietly=TRUE))'],
                   env=env, check=True)
    Path('/tmp/r021-resolved.txt').write_text(json.dumps({
        'artifacts': [{'url': url, 'sha256': digest} for url, digest in ARTIFACTS],
        'runtime': 'R 4.2.2, Debian Linux amd64; fixed original sources',
        'runtime_files_checked': len(local_r.contract()['runtime_files']),
        'source_commits': {sid: spec[2] for sid, spec in local_r.SPECS.items()},
    }, indent=2) + '\n')


if __name__ == '__main__':
    install()
