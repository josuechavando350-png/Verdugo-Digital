"""Select explicit installed profiles for offline original-program acceptance."""
import argparse
import os
from pathlib import Path
import sys
import unittest
from install_final import GROUPS
from verdugo import runtime_profile
parser=argparse.ArgumentParser();parser.add_argument('--group',choices=GROUPS,required=True);args=parser.parse_args()
selected=GROUPS[args.group]
for sid in selected:
    key=runtime_profile.PROFILE_ENV.get(sid)
    if key:os.environ.setdefault(key,'/tmp/verdugo-'+key.removeprefix('VERDUGO_').removesuffix('_PYTHON').lower().replace('_','-')+'-venv/bin/python')
os.environ.setdefault('VERDUGO_LASTNODE_ROOT','/tmp/verdugo-lastnode021')
os.environ.setdefault('VERDUGO_IMAGES_ROOT','/tmp/verdugo-images021')
os.environ.setdefault('VERDUGO_MEDIA_ROOT','/tmp/verdugo-media021')
os.environ.setdefault('VERDUGO_NATIVE_TOOLS_ROOT', '/tmp/verdugo-java021')
os.environ.setdefault('VERDUGO_DATABASE_ROOT','/tmp/verdugo-database021')
os.environ.setdefault('VERDUGO_R_ROOT','/tmp/verdugo-r021')
os.environ.setdefault('VERDUGO_NATIVE_ROOT','/tmp/verdugo-node021')
os.environ.setdefault('VERDUGO_CLI_ROOT','/tmp/verdugo-maps021' if args.group=='source021' else '/tmp/verdugo-cli021')
os.environ['VERDUGO_RUNTIME_SERVICES']=','.join(selected)
os.environ['VERDUGO_RUNTIME_REQUIRED']='1'
os.environ['VERDUGO_RUNTIME_EVIDENCE']='/tmp/'+args.group+'-execution-evidence.json'
os.environ['VERDUGO_PRODUCT_EVIDENCE']='/tmp/'+args.group+'-product-evidence.json'
suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent))
raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
