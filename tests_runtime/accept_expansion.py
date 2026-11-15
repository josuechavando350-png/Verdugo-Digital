"""Execute the selected expansion through the actual Engine in offline CI."""
import os
import argparse
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdugo import local_analytics, local_research, local_interop, local_knowledge, local_data, runtime_profile

groups = {'expansion': [*local_analytics.SPECS, *local_research.SPECS], 'interop': list(local_interop.SPECS),
          'knowledge': [*local_knowledge.SPECS, 'ipranges', 'the-great-gpt-firewall']}
parser = argparse.ArgumentParser(); parser.add_argument('--group', choices=groups, default='expansion')
args = parser.parse_args()
selected = groups[args.group]
for sid in selected:
    key = runtime_profile.PROFILE_ENV.get(sid)
    if key:
        name = key.removeprefix('VERDUGO_').removesuffix('_PYTHON').lower().replace('_', '-')
        os.environ.setdefault(key, '/tmp/verdugo-'+name+'-venv/bin/python')
os.environ['VERDUGO_RUNTIME_SERVICES'] = ','.join(selected)
suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
