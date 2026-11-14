"""Lab only: one fresh isolated interpreter per recipe, worker-like environment."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'verdugo'))
import local_analytics

for sid in local_analytics.SPECS:
    with tempfile.TemporaryDirectory(prefix='verdugo-lab-') as work:
        env = {'PATH': os.defpath, 'HOME': work, 'TMPDIR': work, 'LANG': 'C.UTF-8',
               'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
               'NUMEXPR_NUM_THREADS': '1', 'DO_NOT_TRACK': '1'}
        try:
            proc = subprocess.run([sys.executable, '-I', str(ROOT / 'lab' / 'probe_one.py'), sid],
                                  cwd=work, env=env, capture_output=True, text=True, timeout=240)
            print(proc.stdout[-6000:])
            if proc.returncode or 'PROBE-' not in proc.stdout:
                print('PROBE-STDERR', sid, proc.returncode, proc.stderr[-3000:])
        except subprocess.TimeoutExpired:
            print('PROBE-TIMEOUT', sid)
    sys.stdout.flush()
