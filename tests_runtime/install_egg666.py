"""Explicit, locked original Egg build. The product never installs dependencies."""
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
from verdugo import local_egg666 as sdk
from install_final import download

DRIVER = ROOT/'tests_runtime/egg666-driver'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(source, files):
    for entry in files:
        data = (source/entry['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != entry['sha256']
                or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != entry['blob_sha']):
            raise ValueError('Original source differs: '+entry['path'])


def verify_resolution(metadata, cache, record):
    packages = {p['id']: p for p in metadata['packages']}
    names = {key: p['name']+'@'+p['version'] for key, p in packages.items()}
    graph = sorted([{'id': names[n['id']], 'features': sorted(n['features']),
                     'dependencies': sorted(names[d] for d in n['dependencies'])}
                    for n in metadata['resolve']['nodes']], key=lambda x: x['id'])
    if graph != record['resolved_graph']:
        raise ValueError('Egg locked dependency or feature graph differs')
    if set(names.values()) != {n['id'] for n in graph}:
        raise ValueError('Unexpected package outside reviewed graph')
    for p in packages.values():
        home = Path(p['manifest_path']).parent
        if p['name'] == 'symbol_table':
            if not p['source'].endswith('#'+record['symbol_table']['commit']):
                raise ValueError('Original symbol_table Git revision differs')
            verify_source(home, record['symbol_table']['files'])
        elif p['name'] == 'egg':
            if p['source'] is not None:
                raise ValueError('Egg must come from the reviewed source archive')
            verify_source(home, record['files'])
        elif p['name'] != 'verdugo-egg666-driver':
            entry = next(d for d in record['registry_dependencies']
                         if (d['name'], d['version']) == (p['name'], p['version']))
            if p['source'] != 'registry+https://github.com/rust-lang/crates.io-index':
                raise ValueError('Unexpected dependency registry')
            archives = list((cache/'registry/cache').glob('*/'+p['name']+'-'+p['version']+'.crate'))
            if len(archives) != 1 or sha(archives[0]) != entry['crate_sha256']:
                raise ValueError('Locked dependency archive checksum differs')
            vcs = json.loads((home/'.cargo_vcs_info.json').read_text())
            if vcs['git']['sha1'] != entry['commit']:
                raise ValueError('Dependency original revision differs')
            for license_file in entry['selected_license_files']:
                if sha(home/Path(license_file['path']).name) != license_file['sha256']:
                    raise ValueError('Dependency license differs from original commit')
    return graph


def install(prefix):
    if sys.platform != 'linux' or prefix.exists():
        raise ValueError('A fresh Linux runtime prefix is required')
    record = json.loads(sdk.CONTRACT.read_text())
    for path, expected in record['driver_files'].items():
        if sha(DRIVER/path) != expected: raise ValueError('Reviewed driver changed')
    with tempfile.TemporaryDirectory(prefix='egg666-build-') as tmp:
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
        source = next((work/'source').iterdir()); source.rename(work/'egg-source')
        source = work/'egg-source'; verify_source(source, record['files'])
        cargo = ['cargo', '--manifest-path', str(driver/'Cargo.toml')]
        subprocess.run([cargo[0], 'fetch', *cargo[1:], '--locked'], check=True, env=env)
        metadata = json.loads(subprocess.check_output(
            [cargo[0], 'metadata', *cargo[1:], '--locked', '--offline', '--format-version', '1'], env=env))
        graph = verify_resolution(metadata, cache, record)
        # All source/license checks happen before proc macros or build scripts execute.
        subprocess.run([cargo[0], 'build', *cargo[1:], '--locked', '--offline', '--release'], check=True, env=env)
        verify_resolution(metadata, cache, record)
        for path, expected in record['driver_files'].items():
            if sha(driver/path) != expected: raise ValueError('Driver or lock changed during build')
        binary = driver/'target/release/verdugo-egg666-driver'
        dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
        needed = sorted(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic))
        if (not needed or set(needed) - set(record['native_system_libraries_allowed'])
                or '(RPATH)' in dynamic or '(RUNPATH)' in dynamic):
            raise ValueError('Unexpected native library dependency or search path')
        dest = prefix/sdk.BINARY; dest.parent.mkdir(parents=True); shutil.copy2(binary, dest)
        notices = prefix/'share/verdugo-egg/licenses.json'; notices.parent.mkdir(parents=True)
        notices.write_text(json.dumps({'roots': record['root_license_evidence'],
                                      'dependencies': record['registry_dependencies']}, indent=2)+'\n')
        receipt = {'schema': 'verdugo.egg666.operator-build.v1',
                   'contract_sha256': sha(sdk.CONTRACT),
                   **{k: record[k] for k in ('commit', 'archive_sha256', 'rust_toolchain', 'driver_files')},
                   'resolved_graph': graph, 'compiler': compiler, 'native_needed': needed,
                   'artifacts': {sdk.BINARY: sha(dest), str(notices.relative_to(prefix)): sha(notices)},
                   'independent_build_attestation': False, 'reproducible_binary_build_proven': False,
                   'distribution_license_closure_verified': False}
        (prefix/sdk.RECEIPT).write_text(json.dumps(receipt, indent=2)+'\n')
        sdk.verify_build(prefix, record)
    Path('/tmp/egg666-build-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=Path('/tmp/verdugo-egg666'))
    install(parser.parse_args().prefix)
