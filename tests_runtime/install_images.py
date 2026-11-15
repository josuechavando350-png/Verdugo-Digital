"""Install only the pinned original image CLI; never starts a sandbox."""
import json
import os
from pathlib import Path
import tarfile
from install_final import download
from verdugo import local_images
URL='https://github.com/superradcompany/microsandbox/releases/download/v0.7.15/microsandbox-linux-x86_64.tar.gz'
SHA='37ffc7bf7b2b977ab004f620f47ae4466f021a9b880c94f46f697c56cf6932b7'
def install():
 home=Path('/tmp/verdugo-images021');home.mkdir();archive=home/'runtime.tar.gz';download(URL,archive,SHA)
 with tarfile.open(archive) as t:t.extractall(home,filter='data')
 archive.unlink();os.environ[local_images.ENV]=str(home)
 if not local_images.runtime_state('microsandbox')['version_matches']:raise ValueError('Original image runtime mismatch')
 Path('/tmp/images021-resolved.txt').write_text(json.dumps({'version':'0.7.15','url':URL,'sha256':SHA,'files':local_images.FILES,'scope':'Image cache only; no microVM or cloud'},indent=2)+'\n')
if __name__=='__main__':install()
