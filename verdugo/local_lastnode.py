"""Bounded original native operations, administered separately from the motor."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from .common import VerdugoError, fields
from .local_native import checked
SPECS={'landscape-app':('landscape.validate','original-landscape-source','a882d0675b2cd9ace3fa158f6d8df3b65a5a82cf')}
ENV='VERDUGO_LASTNODE_ROOT'
CONTRACT=Path(__file__).with_name('lastnode_contract.json')
SOURCE=Path(__file__).with_name('vendor')/'landscape'
GUARD=Path(__file__).with_name('_offline_node_guard.cjs')
def root():
 value=os.getenv(ENV)
 if not value or not Path(value).is_absolute() or '..' in Path(value).parts or any(c in value for c in ('\0','\n','\r')):raise VerdugoError('Absolute administrator native runtime required')
 return checked(Path(value),directory=True)
def runtime_state(service):
 op,dist,version=SPECS[service];present=False;binding=None
 try:
  home=root();raw=CONTRACT.read_bytes();contract=json.loads(raw);h=hashlib.sha256(str(home).encode()+raw)
  for path,sha,budget in [(home/'bin/node',contract['node_sha256'],256*1024*1024),(home/'package-lock.json',contract['lock_sha256'],2*1024*1024)]+[(SOURCE/name,sha,2*1024*1024) for name,sha in contract['landscape_files'].items()]:
   digest=hashlib.sha256(checked(path,budget=budget).read_bytes()).hexdigest()
   if digest!=sha:raise ValueError('Native source/runtime changed')
   h.update(bytes.fromhex(digest))
  lock=json.loads((home/'package-lock.json').read_text())
  for package,expected in contract['packages'].items():
   p=checked(home/'node_modules'/package/'package.json').read_bytes();meta=json.loads(p);entry=lock['packages']['node_modules/'+package]
   if meta['name']!=package or meta['version']!=expected or entry['version']!=expected or not entry['integrity'].startswith('sha512-'):raise ValueError('Native package mismatch')
   h.update(p)
  binding=h.hexdigest();present=True
 except (OSError,ValueError,KeyError,TypeError,VerdugoError):pass
 return {'distribution':dist,'distribution_kind':'original-source-cli','expected':version,'installed':version if present else None,'version_matches':present,'extra_distributions':{},'operation':op,'execution_verified':False,'runtime_binding':binding}
def records(p):
 from .local_runtime import string
 string(p['secret_text'],16000)
 try:rows=json.loads(p['secret_text'])
 except (ValueError,TypeError,RecursionError) as exc:raise VerdugoError('Finite JSON project records required') from exc
 if not isinstance(rows,list) or not 1<=len(rows)<=30:raise VerdugoError('Provide 1..30 project records')
 for row in rows:
  fields(row,('name',),('repo_url','project_org','joined','twitter'))
  for value in row.values():string(value,300)
 return rows
def validate(service,operation,p):
 if service not in SPECS or operation!=SPECS[service][0]:raise VerdugoError('Unsupported native operation')
 fields(p,('dataset','secret_text'))
 if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
 records(p)
def run(service,p):
 validate(service,SPECS[service][0],p)
 if not runtime_state(service)['version_matches']:raise ValueError('Native runtime changed')
 home=root();rows=records(p)
 Path('settings.yml').write_text(json.dumps({'global':{'membership':False},'membership':{}}))
 Path('landscape.yml').write_text(json.dumps({'landscape':[{'category':None,'name':'Supplied','subcategories':[{'subcategory':None,'name':'Projects','items':[{'item':None,**row} for row in rows]}]}]}))
 env={'PATH':os.defpath,'HOME':os.getcwd(),'TMPDIR':os.getcwd(),'LANG':'C.UTF-8','NODE_PATH':str(home/'node_modules'),'PROJECT_PATH':os.getcwd()}
 with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
  result=subprocess.run([str(home/'bin/node'),'--require',str(GUARD),str(SOURCE/'validateLandscape.js')],env=env,stdout=stdout,stderr=stderr,timeout=30,close_fds=True)
 if result.returncode not in (0,1):raise ValueError('Original landscape validator failed')
 path=Path('landscape-errors.json');messages=json.loads(path.read_text()) if path.exists() else []
 if not isinstance(messages,list) or len(messages)>180 or any(not isinstance(m,dict) or m.get('type')!='fatal' or m.get('category')!='general' or not isinstance(m.get('text'),str) for m in messages):raise ValueError('Invalid original validation evidence')
 if (result.returncode==0)!= (not messages):raise ValueError('Original exit status and validation evidence disagree')
 return {'projects_in_input':len(rows),'schema_valid':result.returncode==0,'fatal_errors':len(messages),'network_accessed':False,'github_comment_sent':False,'repositories_verified':False,'scope':'Original metadata checks over supplied project items; category structure fixed; reporter path adapted to private job directory'}
