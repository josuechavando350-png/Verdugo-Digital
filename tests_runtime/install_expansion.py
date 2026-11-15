"""CI setup only. No installer is exposed by Engine, CLI or MCP."""
from concurrent.futures import ThreadPoolExecutor
import argparse
from pathlib import Path
import subprocess
import sys
import venv


def install(name):
    root = Path('/tmp')/('verdugo-'+name+'-venv')
    venv.EnvBuilder(with_pip=True, symlinks=False).create(root)
    python = root/'bin'/'python'
    python.chmod(0o755)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', 'requirements/runtime-'+name+'.txt',
                    '--report', '/tmp/'+name+'-pip-report.json'], check=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
    freeze = subprocess.check_output([str(python), '-m', 'pip', 'freeze'], text=True)
    Path('/tmp/'+name+'-resolved.txt').write_text(freeze)


if __name__ == '__main__':
    # Independent dependency graphs intentionally avoid combining pandas and
    # protobuf versions required by different upstream libraries.
    groups = {'expansion': ('analytics', 'research', 'language', 'protocol'),
              'interop': ('agents', 'legacy-agents', 'camel', 'anyagent', 'semantics', 'discovery', 'guard'),
              'knowledge': ('knowledge', 'modeling', 'graph-forecast')}
    parser = argparse.ArgumentParser(); parser.add_argument('--group', choices=groups, default='expansion')
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(install, groups[args.group]))
