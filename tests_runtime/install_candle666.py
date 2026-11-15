"""Build the original CPU Candle extension; preparation is outside Engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import local_tensor666 as tensor
from install_final import download


def verify_source(source, record):
    for entry in record['files']:
        data = (source / entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest() != entry['blob_sha']):
            raise ValueError('Original Candle source differs from pinned Git tree')


def record_installation(prefix, source, record, rust_version):
    verify_source(source, record)
    if rust_version != record['rust_version']:
        raise ValueError('Unexpected Rust toolchain')
    if hashlib.sha256((source / 'Cargo.lock').read_bytes()).hexdigest() != record['cargo_lock_sha256']:
        raise ValueError('Candle operator-resolved Cargo lock changed')
    receipt = {'schema': 'verdugo.candle666.operator-build.v1',
        **{key: record[key] for key in ('commit', 'archive_sha256', 'cargo_lock_sha256',
            'rust_version', 'maturin_version', 'build_environment')},
        'native_sha256': hashlib.sha256((prefix / tensor.NATIVE).read_bytes()).hexdigest(),
        'independent_build_attestation': False, 'reproducible_binary_build_proven': False}
    dest = prefix / tensor.RECEIPT; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + '\n')
    tensor.verify_build(prefix, record)
    return receipt


def install(prefix):
    raise RuntimeError('Candle dependency license review unresolved; preparation disabled')


def _historical_unregistered_installer(prefix):
    raise RuntimeError('Quarantined historical installer')
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError('Original PyO3 abi3-py313 requires the reviewed Python 3.13 profile')
    record = json.loads(tensor.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = prefix / 'bin/python'
    for p in (prefix / 'bin').glob('python*'):
        if not p.is_symlink(): p.chmod(0o755)
    subprocess.run([str(python), '-m', 'pip', 'install', 'maturin==' + record['maturin_version']], check=True)
    env = dict(os.environ, RUSTUP_TOOLCHAIN=record['rust_version'],
               PATH=str(prefix / 'bin') + os.pathsep + os.environ.get('PATH', ''),
               **record['build_environment'])
    subprocess.run(['rustup', 'toolchain', 'install', record['rust_version'], '--profile', 'minimal'], check=True, env=env)
    rust = subprocess.check_output(['rustc', '--version'], env=env, text=True).split()[1]
    with tempfile.TemporaryDirectory(prefix='candle666-build-') as tmp:
        work = Path(tmp)
        download(record['archive_url'], work / 'source.tar.gz', record['archive_sha256'])
        with tarfile.open(work / 'source.tar.gz') as archive:
            archive.extractall(work / 'source', filter='data')
        source = next((work / 'source').iterdir()); verify_source(source, record)
        lock = ROOT / 'requirements/runtime-candle666.Cargo.lock'
        if hashlib.sha256(lock.read_bytes()).hexdigest() != record['cargo_lock_sha256']:
            raise ValueError('Candle dependency lock digest mismatch')
        shutil.copyfile(lock, source / 'Cargo.lock')
        env['CARGO_TARGET_DIR'] = str(work / 'target')
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-build-isolation',
            str(source / 'candle-pyo3'), '--report', '/tmp/candle666-pip-report.json'], check=True, env=env)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
        receipt = record_installation(prefix, source, record, rust)
    Path('/tmp/candle666-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    Path('/tmp/candle666-resolved.txt').write_text(subprocess.check_output(
        [str(python), '-m', 'pip', 'freeze'], text=True))
    print(json.dumps({'prepared': True, 'commit': record['commit'], 'prefix': str(prefix),
                      'source_built': True, 'independent_build_attestation': False}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--prefix', default='/tmp/verdugo-candle666')
    args = p.parse_args(); install(Path(args.prefix))
