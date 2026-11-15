"""Explicit source compilation and artifact receipt; never called by Engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import local_monty666 as monty
from install_final import download


def verify_source(source, record):
    for entry in record['files']:
        data = (source / entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != entry['blob_sha']):
            raise ValueError('Original Monty source differs from the reviewed Git tree')


def record_installation(prefix, source, record, rust_version):
    verify_source(source, record)
    if rust_version != record['rust_version']:
        raise ValueError('Unexpected Rust toolchain')
    for entry in record['files']:
        if entry['installed_path']:
            if hashlib.sha256((prefix / entry['installed_path']).read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Installed interface differs from original Python source')
    receipt = {'schema': 'verdugo.monty666.operator-build.v1', 'commit': record['commit'],
        'archive_sha256': record['archive_sha256'], 'rust_version': rust_version,
        'maturin_version': record['maturin_version'], 'cargo_build_jobs': 1,
        'build_profile': 'release with recorded resource-saving compiler flags; Cargo.lock preserved',
        'build_environment': record['build_environment'],
        'native_artifacts': {name: hashlib.sha256((prefix / name).read_bytes()).hexdigest()
                             for name in monty.NATIVE},
        'independent_build_attestation': False, 'reproducible_binary_build_proven': False}
    dest = prefix / monty.RECEIPT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + '\n')
    monty.verify_build(prefix, record)
    return receipt


def install(prefix):
    record = json.loads(monty.CONTRACT.read_text())
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = prefix / 'bin/python'
    for p in (prefix / 'bin').glob('python*'):
        if not p.is_symlink(): p.chmod(0o755)
    subprocess.run([str(python), '-m', 'pip', 'install',
                    'maturin==' + record['maturin_version'], 'typing_extensions==4.16.0'], check=True)
    # PEP 517 invokes the maturin executable, not just its Python module.
    # A venv interpreter selected by absolute path does not activate its bin dir.
    env = dict(os.environ, RUSTUP_TOOLCHAIN=record['rust_version'],
               PATH=str(prefix / 'bin') + os.pathsep + os.environ.get('PATH', ''),
               **record['build_environment'])
    subprocess.run(['rustup', 'toolchain', 'install', record['rust_version'], '--profile', 'minimal'],
                   check=True, env=env)
    rust = subprocess.check_output(['rustc', '--version'], env=env, text=True).split()[1]
    with tempfile.TemporaryDirectory(prefix='monty666-build-') as tmp:
        work = Path(tmp)
        download(record['archive_url'], work / 'source.tar.gz', record['archive_sha256'])
        with tarfile.open(work / 'source.tar.gz') as archive:
            archive.extractall(work / 'source', filter='data')
        source = work / 'source' / ('monty-' + record['commit'])
        verify_source(source, record)
        env['CARGO_TARGET_DIR'] = str(work / 'target')
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-build-isolation',
                        '-c', str(ROOT / 'requirements/runtime-monty666.constraints.txt'),
                        str(source / 'crates/monty-python'), str(source / 'crates/monty-runtime'),
                        '--report', '/tmp/monty666-pip-report.json'], check=True, env=env)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
        receipt = record_installation(prefix, source, record, rust)
    Path('/tmp/monty666-resolved.txt').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-monty666-venv'))
    install(p.parse_args().prefix)
