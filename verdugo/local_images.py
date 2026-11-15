"""Original Microsandbox image import/inspection, never VM execution or cloud."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from .common import VerdugoError, fields
from .local_native import checked
SPECS={'microsandbox':('image.inspect','original-microsandbox-cli','0.7.15')}
ENV='VERDUGO_IMAGES_ROOT'
FILES={'msb':'2cb46d96a14ad389e8546d333b61f797d24f249b0e6c3a347763c58bfb2a2742','libkrunfw.so.5.6.1':'e54cd5d8849162bbdb136d3342f0601be1b713a2af529bd60d335ec2d44fdb7c'}
def root():
 value=os.getenv(ENV)
 if not value or not Path(value).is_absolute() or '..' in Path(value).parts or any(c in value for c in ('\0','\n','\r')):raise VerdugoError('Absolute administrator image runtime required')
 return checked(Path(value),directory=True)
def runtime_state(service):
 op,dist,version=SPECS[service];present=False;binding=None
 try:
  home=root();h=hashlib.sha256(str(home).encode())
  for name,expected in FILES.items():
   raw=checked(home/name,budget=128*1024*1024).read_bytes();sha=hashlib.sha256(raw).hexdigest()
   if sha!=expected:raise ValueError('Original image runtime changed')
   h.update(name.encode());h.update(bytes.fromhex(sha))
  binding=h.hexdigest();present=True
 except (OSError,ValueError,TypeError,VerdugoError):pass
 return {'distribution':dist,'distribution_kind':'original-native-cli','expected':version,'installed':version if present else None,'version_matches':present,'extra_distributions':{},'operation':op,'execution_verified':False,'runtime_binding':binding}
def contents(p):
 from .local_runtime import string
 string(p['secret_text'],18000)
 try:rows=json.loads(p['secret_text'])
 except (TypeError,ValueError,RecursionError) as exc:raise VerdugoError('A JSON list of supplied text files is required') from exc
 if not isinstance(rows,list) or not 1<=len(rows)<=20:raise VerdugoError('Provide 1..20 text file contents')
 total=0
 for text in rows:string(text,1000);total+=len(text.encode())
 if total>12000:raise VerdugoError('At most 12000 content bytes')
 return rows
def validate(service,operation,p):
 if service not in SPECS or operation!=SPECS[service][0]:raise VerdugoError('Unsupported image operation')
 fields(p,('dataset','secret_text'))
 if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
 contents(p)
def archive(files):
 buffer=io.BytesIO()
 with tarfile.open(fileobj=buffer,mode='w') as out:
  for name,raw in files.items():
   info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;info.mtime=0;out.addfile(info,io.BytesIO(raw))
 return buffer.getvalue()
def run(service,p):
 validate(service,SPECS[service][0],p)
 if not runtime_state(service)['version_matches']:raise ValueError('Image runtime changed')
 rows=contents(p);layer=archive({f'data/item-{i}.txt':text.encode() for i,text in enumerate(rows)});diff='sha256:'+hashlib.sha256(layer).hexdigest()
 config=json.dumps({'architecture':'amd64','os':'linux','config':{'Labels':{'verdugo.scope':'supplied-data'},'Cmd':[]},'rootfs':{'type':'layers','diff_ids':[diff]},'history':[{'created_by':'Verdugo fixed data archive'}]},separators=(',',':')).encode()
 config_name=hashlib.sha256(config).hexdigest()+'.json'
 manifest=json.dumps([{'Config':config_name,'RepoTags':['verdugo-supplied:latest'],'Layers':['layer/layer.tar']}]).encode()
 Path('input.tar').write_bytes(archive({config_name:config,'manifest.json':manifest,'layer/layer.tar':layer}))
 env={'HOME':os.getcwd(),'TMPDIR':os.getcwd(),'PATH':os.defpath,'LANG':'C.UTF-8','XDG_CACHE_HOME':str(Path.cwd()/'cache'),'XDG_DATA_HOME':str(Path.cwd()/'data'),'XDG_CONFIG_HOME':str(Path.cwd()/'config')}
 def call(args):
  with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
   done=subprocess.run([str(root()/'msb'),*args],env=env,stdout=stdout,stderr=stderr,timeout=35,close_fds=True)
   if done.returncode:raise ValueError('Original Microsandbox image operation failed')
   stdout.seek(0);raw=stdout.read(65537)
   if len(raw)>65536:raise ValueError('Image response budget exceeded')
   return raw
 call(['load','--input','input.tar','--quiet'])
 result=json.loads(call(['image','inspect','verdugo-supplied:latest','--format','json']))
 layers=result['layers']
 if result['reference']!='verdugo-supplied:latest' or result['architecture']!='amd64' or result['os']!='linux' or result['layer_count']!=1 or len(layers)!=1 or layers[0]['diff_id']!=diff or result['config']['digest']!='sha256:'+config_name[:-5]:raise ValueError('Imported image metadata does not match supplied archive')
 if result['size_bytes']!=len(layer) or layers[0]['compressed_size_bytes']!=len(layer):raise ValueError('Imported layer size mismatch')
 return {'files_in_input':len(rows),'content_bytes':sum(len(t.encode()) for t in rows),'image_layers':result['layer_count'],'archive_layer_bytes':result['size_bytes'],'layer_sha256':diff[7:],'architecture':result['architecture'],'os':result['os'],'sandbox_started':False,'hardware_isolation_verified':False,'cloud_called':False,'persistent_cache':False,'scope':'Original Microsandbox imported and inspected a generated data-only Docker image; no guest executable'}
