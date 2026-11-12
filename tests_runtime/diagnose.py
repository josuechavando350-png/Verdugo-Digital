"""CI-only synthetic diagnostics. Never consumes user data or production state."""
import os
from pathlib import Path
import resource
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'verdugo'))
from fixtures import CASES
from _local_worker import guard
from local_recipes import run

if len(sys.argv) != 2 or sys.argv[1] not in ('evidently', 'playwright'):
    raise SystemExit('Only fixed synthetic diagnosis cases are supported')
service = sys.argv[1]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
file_budget = (128 if service == 'playwright' else 2) * 1024 * 1024
resource.setrlimit(resource.RLIMIT_FSIZE, (file_budget, file_budget))
sys.addaudithook(guard)
os.environ['DO_NOT_TRACK'] = '1'
os.environ['OTEL_SDK_DISABLED'] = 'true'
try:
    result = run(service, '', CASES[service])
    print(service, 'direct recipe completed; keys:', sorted(result))
except Exception:
    traceback.print_exc()
    raise SystemExit(1)
