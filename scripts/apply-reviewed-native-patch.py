#!/usr/bin/env python3
"""Apply only reviewed, hash-bound source edits on the integration branch.

No network credentials are read. Git edits only the three named source files.
The workflow performs a normal fast-forward push, never a force push.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'scripts/native-pair-acceptance.py','scripts/native_extra_apps.py','scripts/native_openreplay.py'}
def blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def apply(manifest):
    files=manifest.get('files')
    if manifest.get('schema_version')!=1 or not isinstance(files,list) or {e.get('path') for e in files}!=ALLOWED or len(files)!=len(ALLOWED):raise ValueError('unexpected_patch_scope')
    pending=[]
    for e in files:
        path=ROOT/e['path']
        if path.is_symlink() or not path.is_file():raise ValueError('patch_target_not_regular')
        actual=blob(path.read_bytes())
        if actual==e['after']:continue
        if actual!=e['before']:raise ValueError('patch_preimage_changed_'+e['path'])
        patch=e['diff']
        if not patch.startswith('--- a/'+e['path']+'\n+++ b/'+e['path']+'\n'):raise ValueError('unexpected_patch_header')
        if any(line.startswith(('--- ','+++ ','diff ','rename ','copy ')) for line in patch.splitlines()[2:]):raise ValueError('unexpected_patch_file')
        pending.append(e)
    patch=''.join(e['diff'] for e in pending)
    if not patch:return False
    subprocess.run(['git','apply','--check','--whitespace=error'],cwd=ROOT,input=patch,text=True,check=True)
    subprocess.run(['git','apply','--whitespace=error'],cwd=ROOT,input=patch,text=True,check=True)
    for e in files:
        if blob((ROOT/e['path']).read_bytes())!=e['after']:raise ValueError('patch_postimage_mismatch_'+e['path'])
    return True
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('manifest required')
    path=(ROOT/sys.argv[1]).resolve()
    if path!=ROOT/'integration-patches/openreplay-capture.json':raise SystemExit('unexpected_manifest')
    print('applied' if apply(json.loads(path.read_text())) else 'already_applied')
