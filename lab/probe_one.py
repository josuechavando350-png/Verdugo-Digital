"""Lab only: run one analytics recipe like the worker would, with full diagnostics."""
import importlib.metadata
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests_runtime'))
sys.path.insert(0, str(ROOT / 'verdugo'))
from _local_worker import guard
from analytics_fixtures import CASES
import local_analytics

sid = sys.argv[1]
sys.addaudithook(guard)
start = time.time()
try:
    version = importlib.metadata.version(local_analytics.SPECS[sid][1])
    result = local_analytics.run(sid, CASES[sid])
    text = json.dumps(result, ensure_ascii=False, allow_nan=False)
    print('PROBE-OK', sid, version, round(time.time() - start, 2), len(text), text[:1800])
except BaseException:
    print('PROBE-FAIL', sid, round(time.time() - start, 2))
    traceback.print_exc(file=sys.stdout)
