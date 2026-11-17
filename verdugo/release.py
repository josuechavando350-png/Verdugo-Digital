"""Verify an extracted, prebuilt local distribution. Checksums are not signatures."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

from . import __version__
from .common import VerdugoError, encode


def verify(root):
    root = Path(root)
    try:
        path = root/'RELEASE.json'
        if path.is_symlink() or path.stat().st_size > 2*1024*1024: raise ValueError()
        manifest = json.loads(path.read_text())
        files = manifest['sha256']
        if (manifest['schema'] != 1 or manifest['version'] != __version__
                or not re.fullmatch('[a-f0-9]{40}', manifest['source_commit'])
                or not isinstance(files, dict) or not 1 <= len(files) <= 10000
                or not {'panel/dist/index.html', 'verdugo/__main__.py', 'sources/panel.json'} <= files.keys()):
            raise ValueError()
        for name, expected in files.items():
            parts = PurePosixPath(name).parts
            if not parts or parts[0] == '/' or '..' in parts or '\\' in name: raise ValueError()
            current = root
            for part in parts:
                current = current/part
                if current.is_symlink(): raise ValueError()
            if not current.is_file() or current.stat().st_size > 16*1024*1024: raise ValueError()
            if hashlib.sha256(current.read_bytes()).hexdigest() != expected: raise ValueError()
        # Prevent an unlisted JS/Python file from being introduced into a verified package.
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.name != 'RELEASE.json'}
        if actual != set(files): raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise VerdugoError('Paquete incompleto o modificado; extrae otra copia del artefacto comprobado') from None
    return {'state': 'verified_release_files', 'version': manifest['version'],
            'source_commit': manifest['source_commit'], 'files': len(files),
            'signature_verified': False, 'external_calls_made': False}


if __name__ == '__main__':
    try: print(encode(verify(Path(__file__).resolve().parents[1])))
    except VerdugoError as exc:
        print(encode({'error': str(exc)}), file=sys.stderr); raise SystemExit(2)
