"""Fixed Quarto and Auto-Editor operations on generated local inputs only."""
import hashlib
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import wave
from .common import VerdugoError, fields
from .local_native import checked

SPECS={'quarto':('document.render','original-quarto','1.11.9'),
       'auto-editor':('audio.levels','original-auto-editor','31.9.0')}
ENV='VERDUGO_MEDIA_ROOT'
CONTRACT=Path(__file__).with_name('media_contract.json')


def root():
 value=os.getenv(ENV)
 if not value or not Path(value).is_absolute() or '..' in Path(value).parts or any(x in value for x in ('\0','\n','\r')):
  raise VerdugoError('An absolute administrator media runtime is required')
 return checked(Path(value),directory=True)


def runtime_state(service):
 op,dist,expected=SPECS[service];present=False;binding=None
 try:
  home=root();raw=CONTRACT.read_bytes();spec=json.loads(raw);h=hashlib.sha256(str(home).encode()+raw)
  if (home/'src/quarto.ts').exists():raise ValueError('Quarto development mode is prohibited')
  for name in spec['groups'][service]:
   if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Invalid runtime path')
   digest=hashlib.sha256(checked(home/name,budget=256*1024*1024).read_bytes()).hexdigest()
   if digest!=spec['files'][name]:raise ValueError('Native media runtime changed')
   h.update(name.encode());h.update(bytes.fromhex(digest))
  binding=h.hexdigest();present=True
 except (OSError,ValueError,KeyError,TypeError,VerdugoError):pass
 return {'distribution':dist,'distribution_kind':'original-native-cli','expected':expected,'installed':expected if present else None,
         'version_matches':present,'extra_distributions':{},'operation':op,'execution_verified':False,'runtime_binding':binding}


def validate(service,operation,p):
 from .local_runtime import finite,string
 if service not in SPECS or operation!=SPECS[service][0]:raise VerdugoError('Unsupported media operation')
 keys=('title','sections') if service=='quarto' else ('samples',)
 try:fields(p,('dataset',*keys))
 except (ValueError,TypeError,OverflowError) as exc:raise VerdugoError('Bounded finite JSON required') from exc
 if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
 if service=='quarto':
  string(p['title'],120)
  if not isinstance(p['sections'],list) or not 1<=len(p['sections'])<=10:raise VerdugoError('Provide 1..10 text sections')
  size=len(p['title'])
  for row in p['sections']:
   fields(row,('heading','text'));string(row['heading'],120);string(row['text'],1200);size+=len(row['heading'])+len(row['text'])
  if size>5000:raise VerdugoError('At most 5000 document characters')
 else:
  if not isinstance(p['samples'],list) or not 800<=len(p['samples'])<=8000:raise VerdugoError('Provide 800..8000 PCM amplitudes at 8000 Hz')
  for value in p['samples']:finite(value,-1,1)


def run(service,p):
 validate(service,SPECS[service][0],p)
 if not runtime_state(service)['version_matches']:raise ValueError('Media runtime changed')
 home=root();env={'PATH':os.defpath,'HOME':os.getcwd(),'TMPDIR':os.getcwd(),'LANG':'C.UTF-8',
                  'DENO_DIR':str(Path.cwd()/'deno-cache'),'QUARTO_DENO_EXTRA_OPTIONS':'--deny-net'}
 if service=='quarto':
  def escaped(value):
   # Callers supply plain text. Escape syntax that could become code, YAML,
   # includes, links, math, raw HTML, attributes, citations or filters.
   return re.sub(r'([\\`*_{}\[\]()#+.!|<>$@^~:=\-])',r'\\\1',value)
  document='---\nformat:\n  html:\n    theme: none\n    minimal: true\n    embed-resources: false\n    toc: false\nexecute:\n  enabled: false\n---\n\n'
  document+='# '+escaped(p['title'])+'\n\n'
  document+='\n\n'.join('## '+escaped(row['heading'])+'\n\n'+escaped(row['text']) for row in p['sections'])+'\n'
  Path('document.qmd').write_text(document)
  args=[str(home/'quarto/1.11.9/bin/quarto'),'render','document.qmd','--to','html','--no-execute','--no-cache','--quiet']
 else:
  with wave.open('audio.wav','wb') as out:
   out.setparams((1,2,8000,0,'NONE','not compressed'))
   out.writeframes(b''.join(struct.pack('<h',round(v*32767)) for v in p['samples']))
  args=[str(home/'bin/auto-editor'),'levels','audio.wav','--edit','audio','--timebase','10','--no-cache']
 with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
  result=subprocess.run(args,stdout=stdout,stderr=stderr,env=env,timeout=50,close_fds=True)
  if result.returncode:raise ValueError('Original media operation failed')
  stdout.seek(0);raw=stdout.read(65537)
 if len(raw)>65536:raise ValueError('Media output budget exceeded')
 if service=='auto-editor':
  lines=raw.decode().strip().splitlines()
  if not lines or lines.pop(0)!='@start':raise ValueError('Original audio level protocol changed')
  levels=[float(v) for v in lines if v.strip()]
  if not 1<=len(levels)<=10 or any(not math.isfinite(v) or not 0<=v<=1 for v in levels):raise ValueError('Invalid original audio levels')
  return {'levels':levels,'samples':len(p['samples']),'sample_rate_hz':8000,'channels':1,'timebase_hz':10,
          'pcm_bits':16,'audio_edited':False,'speech_transcribed':False}
 raw=Path('document.html').read_bytes()
 if len(raw)>1024*1024:raise ValueError('Rendered document exceeds budget')
 document=raw.decode();match=re.search(r'<body\b[^>]*>(.*?)</body>',document,re.S)
 if not match:raise ValueError('Quarto body content absent')
 fragment=match.group(1).strip()
 if len(fragment.encode())>24000:raise ValueError('Rendered content exceeds product result budget')
 class PlainContent(HTMLParser):
  def handle_starttag(self,tag,attrs):
   if tag in ('script','iframe','object','embed') or any(k.lower().startswith('on') for k,v in attrs):
    raise ValueError('Unexpected active content in plain-text render')
 PlainContent().feed(fragment)
 return {'html':fragment,'sections':len(p['sections']),'renderer':'Quarto 1.11.9 HTML',
         'code_executed':False,'remote_assets_fetched':False,'published':False}
