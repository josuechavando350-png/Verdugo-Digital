"""Explicit original-source preparation, never called by Engine."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def prepare(prefix):
    contract = json.loads((ROOT / 'sources/contracts-manus666.json').read_text())
    destination = Path(prefix) / 'share/verdugo-openmanus/source.tar.gz'
    if destination.exists():
        raw = destination.read_bytes()
    else:
        with urllib.request.urlopen(contract['archive_url'], timeout=90) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
    if hashlib.sha256(raw).hexdigest() != contract['archive_sha256']:
        raise ValueError('Original source archive checksum mismatch')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    print('Prepared original OpenManus source archive; no models or browsers installed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', default=sys.prefix)
    prepare(parser.parse_args().prefix)
