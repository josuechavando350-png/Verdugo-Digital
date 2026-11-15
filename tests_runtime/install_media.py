"""Explicit, checksum-pinned original media runtimes; never called by Engine."""
import json
import os
from pathlib import Path
import shutil
import tarfile
from install_final import download
from verdugo import local_media as media

ARTIFACTS=[
 ('quarto.tar.gz','https://github.com/quarto-dev/quarto-cli/releases/download/v1.11.9/quarto-1.11.9-linux-amd64.tar.gz','9d037baa3b38ffac7217edca1d2e53760b0fab4d5749220740a32056e03a1530'),
 ('auto-editor','https://github.com/WyattBlue/auto-editor/releases/download/31.9.0/auto-editor-linux-x86_64','5a921b1396ebf72e27d4bec106894782b739b30a908bd195d63a42e80524548e'),
]
def install():
 home=Path('/tmp/verdugo-media021');home.mkdir();build=home/'build';build.mkdir()
 for name,url,sha in ARTIFACTS:download(url,build/name,sha)
 with tarfile.open(build/'quarto.tar.gz') as tar:tar.extractall(build,filter='data')
 (home/'quarto').mkdir();shutil.move(str(build/'quarto-1.11.9'),str(home/'quarto/1.11.9'))
 (home/'bin').mkdir();shutil.move(str(build/'auto-editor'),str(home/'bin/auto-editor'));(home/'bin/auto-editor').chmod(0o755)
 for path in (home/'quarto').rglob('*'):
  if path.is_symlink():
   resolved=path.resolve()
   if not resolved.is_relative_to(home/'quarto'):raise ValueError('Unexpected runtime link')
   if resolved.is_file():raw=resolved.read_bytes();path.unlink();path.write_bytes(raw)
 os.environ[media.ENV]=str(home)
 for sid in media.SPECS:
  if not media.runtime_state(sid)['version_matches']:raise ValueError('Original media runtime differs: '+sid)
 Path('/tmp/media021-resolved.txt').write_text(json.dumps({'artifacts':[{'name':n,'url':u,'sha256':s} for n,u,s in ARTIFACTS],'files_verified':len(json.loads(media.CONTRACT.read_text())['files'])},indent=2)+'\n')
 shutil.rmtree(build)
if __name__=='__main__':install()
