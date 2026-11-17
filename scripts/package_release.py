#!/usr/bin/env python3
"""Package committed source plus a freshly built panel; no user state or dependencies."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import __version__


def build(destination):
    subprocess.run(['git', 'diff', '--exit-code', '--quiet', 'HEAD', '--'], cwd=ROOT, check=True)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', 'archive', '--format=tar', 'HEAD'], cwd=ROOT)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for entry in source.getmembers():
            if entry.isdir(): continue
            if not entry.isfile(): raise ValueError('Only regular committed source files are distributable')
            files[entry.name] = (source.extractfile(entry).read(), entry.mode & 0o777)
    assets = ROOT/'panel/dist'
    if not (assets/'index.html').is_file(): raise ValueError('Build the panel before packaging')
    for path in sorted(assets.rglob('*')):
        if path.is_symlink(): raise ValueError('Panel assets must not be symlinks')
        if path.is_file(): files[path.relative_to(ROOT).as_posix()] = (path.read_bytes(), 0o644)
    manifest = {'schema': 1, 'version': __version__, 'source_commit': revision,
                'sha256': {p: hashlib.sha256(data).hexdigest() for p, (data, _) in sorted(files.items())}}
    files['RELEASE.json'] = ((json.dumps(manifest, indent=2)+'\n').encode(), 0o644)
    destination = Path(destination).resolve(); destination.mkdir(parents=True, exist_ok=True)
    stem = 'verdugo-digital-'+__version__
    path = destination/(stem+'.tar.gz')
    with path.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as out:
            for name, (data, mode) in sorted(files.items()):
                entry = tarfile.TarInfo(stem+'/'+name)
                entry.mode = mode; entry.size = len(data); entry.mtime = 0
                out.addfile(entry, io.BytesIO(data))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination/'SHA256SUMS').write_text(digest+'  '+path.name+'\n')
    return {'archive': str(path), 'sha256': digest, 'bytes': path.stat().st_size, 'source_commit': revision}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    print(json.dumps(build(parser.parse_args().output)))
