"""Original tools against a private authenticated server of supplied content only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from .common import VerdugoError,fields,identifier
from .local_native import checked
SPECS={'siteone-crawler':('pages.crawl','original-siteone-cli','2.5.1.20260627'),'sherlock':('responses.classify','sherlock-project','0.16.2')}
ENV='VERDUGO_OWNED_HTTP_ROOT'
WORKER=Path(__file__).with_name('_owned_http_worker.cjs')
PY_WORKER=Path(__file__).with_name('_sherlock_original_worker.py')
FILES={'node':'e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb','siteone-crawler':'9e51159ab845f0bafb93ceeaf99e93537dfca14d7cd5f20998c3074def571e9b'}
def root():
 value=os.getenv(ENV)
 if not value or not Path(value).is_absolute() or '..' in Path(value).parts or any(c in value for c in ('\0','\n','\r')):raise VerdugoError('Absolute administrator owned HTTP runtime required')
 return checked(Path(value),directory=True)
def runtime_state(service):
 from . import runtime_profile
 op,dist,version=SPECS[service];present=False;binding=None;extras={}
 try:
  home=root();h=hashlib.sha256(str(home).encode())
  for name in ('node','siteone-crawler') if service=='siteone-crawler' else ('node',):
   digest=hashlib.sha256(checked(home/'bin'/name,budget=256*1024*1024).read_bytes()).hexdigest()
   if digest!=FILES[name]:raise ValueError('Owned HTTP native runtime changed')
   h.update(name.encode());h.update(bytes.fromhex(digest))
  if service=='sherlock':
   expected={'sherlock-project':'0.16.2','requests':'2.34.2','requests-futures':'1.1.0'};versions=runtime_profile.versions(service,list(expected))
   if versions!=expected:raise ValueError('Sherlock exact profile unavailable')
   h.update(json.dumps(versions,sort_keys=True).encode());extras={k:{'expected':v,'installed':versions[k],'version_matches':True} for k,v in expected.items() if k!='sherlock-project'}
  binding=h.hexdigest();present=True
 except (OSError,ValueError,KeyError,TypeError,VerdugoError):pass
 return {'distribution':dist,'distribution_kind':'original-cli-owned-loopback','expected':version,'installed':version if present else None,'version_matches':present,'extra_distributions':extras,'operation':op,'execution_verified':False,'runtime_binding':binding}
def decoded(p):
 from .local_runtime import string
 string(p['secret_text'],20000)
 try:rows=json.loads(p['secret_text'])
 except (ValueError,TypeError,RecursionError) as exc:raise VerdugoError('Bounded supplied response JSON required') from exc
 return rows
def validate(service,operation,p):
 from .local_runtime import string
 if service not in SPECS or operation!=SPECS[service][0]:raise VerdugoError('Unsupported owned HTTP operation')
 fields(p,('dataset','pages') if service=='siteone-crawler' else ('dataset','secret_text'))
 if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
 rows=p['pages'] if service=='siteone-crawler' else decoded(p)
 if not isinstance(rows,list) or not 1<=len(rows)<=8:raise VerdugoError('Provide 1..8 supplied records')
 ids=[]
 for row in rows:
  fields(row,('id','title','links') if service=='siteone-crawler' else ('id','status','text','mode','marker'))
  identifier(row['id']);ids.append(row['id'])
  if service=='siteone-crawler':
   string(row['title'],160)
   if not isinstance(row['links'],list) or len(row['links'])>2:raise VerdugoError('At most two links to record IDs per page')
   for link in row['links']:identifier(link)
  else:
   if type(row['status']) is not int or row['status'] not in (200,403,404,500):raise VerdugoError('Supported supplied HTTP statuses: 200,403,404,500')
   string(row['text'],1500);string(row['marker'],100)
   if row['mode'] not in ('status_code','message'):raise VerdugoError('Only original status-code and message checks')
 if len(set(ids))!=len(ids):raise VerdugoError('Duplicate record IDs')
def run(service,p):
 validate(service,SPECS[service][0],p)
 if not runtime_state(service)['version_matches']:raise ValueError('Owned HTTP runtime changed')
 home=root();payload={'service':service,'params':p if service=='siteone-crawler' else {'responses':decoded(p)}}
 env={'PATH':os.defpath,'HOME':os.getcwd(),'TMPDIR':os.getcwd(),'LANG':'C.UTF-8',ENV:str(home)}
 if service=='sherlock':env['VERDUGO_SHERLOCK_EXECUTABLE']=sys.executable
 with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
  result=subprocess.run([str(home/'bin/node'),str(WORKER)],input=json.dumps(payload).encode(),env=env,stdout=stdout,stderr=stderr,timeout=45,close_fds=True)
  if result.returncode:raise ValueError('Original owned HTTP operation failed')
  stdout.seek(0);raw=stdout.read(32769)
 if len(raw)>32768:raise ValueError('Owned HTTP output budget exceeded')
 result=json.loads(raw)
 if not isinstance(result,dict) or result.get('local_server_closed') is not True or type(result.get('owned_http_requests')) is not int or not 1<=result['owned_http_requests']<=100:raise ValueError('Owned server lifecycle evidence missing')
 return result
