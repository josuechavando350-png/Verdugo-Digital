"""Explicit, locked original Oxigraph build. The product never installs dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verdugo import local_oxigraph666 as sdk
from install_final import download

DRIVER = ROOT/'tests_runtime/oxigraph666-driver'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(source, files):
    for entry in files:
        path = source/entry['path']
        if 'symlink_target' in entry:
            if not path.is_symlink() or os.readlink(path) != entry['symlink_target']:
                raise ValueError('Original symlink differs')
            data = os.readlink(path).encode()
        else:
            if path.is_symlink(): raise ValueError('Unexpected source symlink')
            data = path.read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256']
                or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != entry['blob_sha']):
            raise ValueError('Original source differs: '+entry['path'])


def verify_resolution(metadata, cache, source, record):
    packages = {p['id']: p for p in metadata['packages']}
    nodes = {n['id']: n for n in metadata['resolve']['nodes']}
    todo, seen = [metadata['resolve']['root']], set()
    while todo:
        key = todo.pop()
        if key in seen: continue
        seen.add(key); todo.extend(nodes[key]['dependencies'])
    names = {key: p['name']+'@'+p['version'] for key, p in packages.items()}
    graph = sorted([{'id': names[key], 'features': sorted(nodes[key]['features']),
                     'dependencies': sorted(names[d] for d in nodes[key]['dependencies'])}
                    for key in seen], key=lambda x: x['id'])
    if graph != record['resolved_graph']:
        raise ValueError('Oxigraph locked Linux dependency/feature graph differs')
    for key in seen:
        package = packages[key]; home = Path(package['manifest_path']).parent
        if package['name'] == 'verdugo-oxigraph666-driver': continue
        if package['source'] is None:
            if not home.resolve().is_relative_to(source.resolve()):
                raise ValueError('Workspace package is outside reviewed source')
            continue
        entry = next(d for d in record['registry_dependencies']
                     if (d['name'], d['version']) == (package['name'], package['version']))
        if package['source'] != 'registry+https://github.com/rust-lang/crates.io-index':
            raise ValueError('Unexpected dependency registry')
        archives = list((cache/'registry/cache').glob('*/'+package['name']+'-'+package['version']+'.crate'))
        if len(archives) != 1 or sha(archives[0]) != entry['crate_sha256']:
            raise ValueError('Locked dependency archive checksum differs')
        vcs = json.loads((home/'.cargo_vcs_info.json').read_text())
        if vcs['git']['sha1'] != entry['commit']:
            raise ValueError('Dependency original revision differs')
        for license_file in entry['selected_license_files']:
            raw = (home/Path(license_file['path']).name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != license_file.get('crate_sha256', license_file['sha256']):
                raise ValueError('Dependency license differs from reviewed archive')
            expected = license_file['text'].encode()
            if license_file.get('packaging_difference'):
                raw = raw.replace(b'\r\n', b'\n')
            if raw != expected:
                raise ValueError('Dependency license differs from original commit')
    verify_source(source, record['files'])
    return graph


def install(prefix):
    if sys.platform != 'linux' or os.uname().machine != 'x86_64' or prefix.exists():
        raise ValueError('A fresh Linux runtime prefix is required')
    record = json.loads(sdk.CONTRACT.read_text())
    for path, expected in record['driver_files'].items():
        if sha(DRIVER/path) != expected: raise ValueError('Reviewed driver changed')
    with tempfile.TemporaryDirectory(prefix='oxigraph666-build-') as tmp:
        work = Path(tmp); cache = work/'cargo'; driver = work/'driver'
        shutil.copytree(DRIVER, driver)
        env = {k: os.environ[k] for k in ('PATH', 'HOME', 'RUSTUP_HOME',
                                         'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'NO_PROXY',
                                         'https_proxy', 'http_proxy', 'all_proxy', 'no_proxy')
               if k in os.environ}
        env.update(CARGO_HOME=str(cache), RUSTUP_TOOLCHAIN=record['rust_toolchain'],
                   CARGO_NET_GIT_FETCH_WITH_CLI='true', CARGO_BUILD_JOBS='2',
                   LANG='C.UTF-8', TMPDIR=str(work))
        compiler = subprocess.check_output(['rustc', '--version'], env=env, text=True).strip()
        if not compiler.startswith('rustc '+record['rust_toolchain']+' '):
            raise ValueError('Use the reviewed Rust toolchain')
        archive = work/'source.tar.gz'
        download(record['archive_url'], archive, record['archive_sha256'])
        with tarfile.open(archive) as tar: tar.extractall(work/'source', filter='data')
        source = next((work/'source').iterdir()); source.rename(work/'oxigraph-source')
        source = work/'oxigraph-source'; verify_source(source, record['files'])
        cargo = ['cargo', '--manifest-path', str(driver/'Cargo.toml')]
        subprocess.run([cargo[0], 'fetch', *cargo[1:], '--locked', '--target', record['target']], check=True, env=env, cwd=work)
        metadata = json.loads(subprocess.check_output(
            [cargo[0], 'metadata', *cargo[1:], '--locked', '--offline', '--format-version', '1', '--filter-platform', record['target']], env=env, cwd=work))
        graph = verify_resolution(metadata, cache, source, record)
        # All source/license checks happen before proc macros or build scripts execute.
        subprocess.run([cargo[0], 'build', *cargo[1:], '--locked', '--offline', '--release', '--target', record['target']], check=True, env=env, cwd=work)
        verify_resolution(metadata, cache, source, record)
        for path, expected in record['driver_files'].items():
            if sha(driver/path) != expected: raise ValueError('Driver or lock changed during build')
        binary = driver/'target'/record['target']/'release/verdugo-oxigraph666-driver'
        dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
        needed = sorted(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic))
        if (not needed or set(needed) - set(record['native_system_libraries_allowed'])
                or '(RPATH)' in dynamic or '(RUNPATH)' in dynamic):
            raise ValueError('Unexpected native library dependency or search path')
        dest = prefix/sdk.BINARY; dest.parent.mkdir(parents=True); shutil.copy2(binary, dest)
        notices = prefix/'share/verdugo-oxigraph/licenses.json'; notices.parent.mkdir(parents=True)
        notices.write_text(json.dumps({'roots': record['root_license_evidence'],
                                      'dependencies': record['registry_dependencies']}, indent=2)+'\n')
        receipt = {'schema': 'verdugo.oxigraph666.operator-build.v1',
                   'contract_sha256': sha(sdk.CONTRACT),
                   **{k: record[k] for k in ('commit', 'archive_sha256', 'rust_toolchain', 'driver_files')},
                   'resolved_graph': graph, 'compiler': compiler, 'target': record['target'], 'native_needed': needed,
                   'artifacts': {sdk.BINARY: sha(dest), str(notices.relative_to(prefix)): sha(notices)},
                   'independent_build_attestation': False, 'reproducible_binary_build_proven': False,
                   'distribution_license_closure_verified': False}
        (prefix/sdk.RECEIPT).write_text(json.dumps(receipt, indent=2)+'\n')
        sdk.verify_build(prefix, record)
    Path('/tmp/oxigraph666-build-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-oxigraph666'))
    install(parser.parse_args().prefix)
