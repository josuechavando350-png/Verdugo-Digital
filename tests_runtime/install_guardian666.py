"""Explicit CPU source build and licensed model preparation outside Engine."""
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
from verdugo import local_guardian666 as guardian
from install_final import download, digest


def verify_source(source, record):
    for entry in record['native']['files']:
        data = (source / entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256'] or
                hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()
                != entry['blob_sha']):
            raise ValueError('Original native source differs from pinned Git tree')


def record_installation(prefix, source, record, compiler):
    verify_source(source, record)
    for name in guardian.NATIVE:
        version = subprocess.check_output([str(prefix / name), '--version'],
            stderr=subprocess.STDOUT, text=True)
        if record['native']['commit'] not in version or '1.0.0-dev' not in version:
            raise ValueError('Original native build version/commit mismatch')
    receipt = {'schema': 'verdugo.guardian666.operator-build.v1',
        'commit': record['native']['commit'],
        'archive_sha256': record['native']['archive_sha256'],
        'cmake_version': record['native']['cmake_version'],
        'cmake_flags': record['native']['cmake_flags'], 'compiler': compiler,
        'model_revision': record['weights']['revision'],
        'model_sha256': record['weights']['sha256'],
        'native_artifacts': {name: digest(prefix / name) for name in guardian.NATIVE},
        'independent_build_attestation': False, 'reproducible_binary_build_proven': False}
    dest = prefix / guardian.RECEIPT; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + '\n')
    guardian.verify_build(prefix, record)
    return receipt


def install(prefix, archive_file=None):
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Use the tested Python 3.12 installer')
    record = json.loads(guardian.CONTRACT.read_text())
    # Both pinned official model cards link this full Apache license. These
    # evidence bytes must be intact before the explicit model download below.
    for entry in record['assets']:
        if digest(guardian.ASSETS / entry['local_name']) != entry['sha256']:
            raise ValueError('Model license/template evidence changed')
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = str(prefix / 'bin/python')
    subprocess.run([python, '-m', 'pip', 'install', 'Jinja2==3.1.6', 'MarkupSafe==3.0.3',
                    'cmake==' + record['native']['cmake_version']], check=True)
    compiler = subprocess.check_output(['c++', '--version'], text=True).splitlines()[0]
    with tempfile.TemporaryDirectory(prefix='guardian666-build-') as temp:
        work = Path(temp)
        archive_path = archive_file or work / 'source.tar.gz'
        if archive_file:
            if digest(archive_path) != record['native']['archive_sha256']:
                raise ValueError('Administrator source archive checksum mismatch')
        else:
            download(record['native']['archive_url'], archive_path, record['native']['archive_sha256'])
        with tarfile.open(archive_path) as archive:
            archive.extractall(work / 'source', filter='data')
        source = work / 'source' / ('llama.cpp-' + record['native']['commit'])
        verify_source(source, record)
        build = work / 'build'; cmake = str(prefix / 'bin/cmake')
        subprocess.run([cmake, '-S', str(source), '-B', str(build),
                        *record['native']['cmake_flags']], check=True)
        for target in record['native']['build_targets']:
            subprocess.run([cmake, '--build', str(build), '--target', target,
                            '-j', str(record['native']['build_jobs'])], check=True)
            shutil.copy2(build / 'bin' / target, prefix / 'bin' / target)
            (prefix / 'bin' / target).chmod(0o755)
        model = prefix / guardian.MODEL; model.parent.mkdir(parents=True, exist_ok=True)
        # Allows rerunning explicit setup without downloading 2 GB again. An
        # existing artifact is accepted only after complete SHA256 verification.
        if model.exists():
            if digest(model) != record['weights']['sha256']:
                raise ValueError('Existing model does not match pinned weights')
        else:
            download(record['weights']['url'], model, record['weights']['sha256'])
        receipt = record_installation(prefix, source, record, compiler)
    subprocess.run([python, '-m', 'pip', 'check'], check=True)
    with open('/tmp/guardian666-resolved.txt', 'w') as out:
        subprocess.run([python, '-m', 'pip', 'freeze'], stdout=out, check=True)
    Path('/tmp/guardian666-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-guardian666'))
    parser.add_argument('--archive-file', type=Path)
    args = parser.parse_args()
    install(args.prefix.resolve(), args.archive_file.resolve() if args.archive_file else None)
