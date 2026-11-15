"""Explicit install-time preparation; the Engine never downloads tokenizer data."""
import hashlib
from pathlib import Path
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verdugo.local_reasoning666 import TOKENIZER_URL, TOKENIZER_SHA256, tokenizer_directory, verify_tokenizer


def prepare():
    target=tokenizer_directory()
    with urllib.request.urlopen(TOKENIZER_URL,timeout=30) as response:
        raw=response.read(4*1024*1024+1)
    if len(raw)>4*1024*1024 or hashlib.sha256(raw).hexdigest()!=TOKENIZER_SHA256:
        raise ValueError('Tokenizer download does not match original source contract')
    target.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=target/hashlib.sha1(TOKENIZER_URL.encode()).hexdigest()
    if path.is_symlink():raise ValueError('Refusing tokenizer symlink')
    path.write_bytes(raw);path.chmod(0o600)
    verify_tokenizer()
    print('Prepared verified cl100k_base tokenizer for offline SDK import; no model or API')


if __name__=='__main__':prepare()
