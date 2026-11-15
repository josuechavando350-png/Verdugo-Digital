"""Fixed original JVM programs and GoAccess on bounded supplied data, offline."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from .common import VerdugoError, fields, integer
from .local_native import checked

SPECS = {
    'openapi-generator': ('spec.validate', 'original-openapi-cli', '7.27.0'),
    'cc-webgraph': ('adjacency.merge', 'original-cc-webgraph', '8a3a34e2f3bc16b865ee234eab83a4917086b814'),
    'arx': ('groups.anonymize', 'original-arx', '3.9.2'),
    'goaccess': ('requests.summarize', 'original-goaccess', '1.7'),
}
CLI = {'openapi-generator', 'goaccess'}
ENV = 'VERDUGO_NATIVE_TOOLS_ROOT'
CONTRACT = Path(__file__).with_name('native_tools_contract.json')
SOURCE = Path(__file__).with_name('java')


def root():
    value = os.getenv(ENV)
    if not value or not Path(value).is_absolute() or '..' in Path(value).parts or any(c in value for c in ('\0','\n','\r')):
        raise VerdugoError('An absolute administrator native-tools runtime is required')
    return checked(Path(value), directory=True)


def contract():
    return json.loads(CONTRACT.read_text())


def runtime_state(service):
    op, distribution, expected = SPECS[service]
    present, binding = False, None
    try:
        home = root(); spec = contract(); h = hashlib.sha256(str(home).encode()+CONTRACT.read_bytes())
        names = spec['groups'][service]
        for name in names:
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Invalid native runtime path')
            raw = checked(home/name, budget=256*1024*1024).read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            if actual != spec['files'][name]:
                raise ValueError('Original runtime changed')
            h.update(name.encode());h.update(bytes.fromhex(actual))
        for name, sha in spec['sources'].items():
            raw=checked(SOURCE/name,budget=128*1024).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=sha:
                raise ValueError('Compiled bridge or original source changed')
            h.update(raw)
        present, binding = True, h.hexdigest()
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution':distribution,'distribution_kind':'original-native-program',
            'expected':expected,'installed':expected if present else None,'version_matches':present,
            'extra_distributions':{},'operation':op,'execution_verified':False,'runtime_binding':binding}


def private_json(p):
    value = p.get('secret_text')
    if not isinstance(value,str) or not 2 <= len(value.encode()) <= 32768:
        raise VerdugoError('Provide bounded private JSON text')
    def no_duplicates(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('Duplicate JSON key')
            out[k]=v
        return out
    try:
        return json.loads(value,object_pairs_hook=no_duplicates,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (ValueError, RecursionError) as exc:
        raise VerdugoError('Private input must be finite JSON without duplicate keys') from exc


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported fixed native operation')
    keys={'openapi-generator':('secret_text',),'arx':('secret_text','k'),
          'cc-webgraph':('adjacencies',),'goaccess':('events',)}[service]
    try:fields(p,('dataset',*keys))
    except (ValueError,TypeError,OverflowError) as exc:raise VerdugoError('Bounded finite JSON required') from exc
    if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
    if service=='openapi-generator':
        spec=private_json(p)
        if not isinstance(spec,dict) or spec.get('openapi') not in ('3.0.0','3.0.1','3.0.2','3.0.3'):
            raise VerdugoError('Only OpenAPI 3.0 JSON documents are supported')
        nodes=[(spec,0)];count=0
        while nodes:
            value,depth=nodes.pop();count+=1
            if depth>20 or count>3000:raise VerdugoError('OpenAPI document is too complex')
            if isinstance(value,float) and not math.isfinite(value):raise VerdugoError("Finite OpenAPI values required")
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in ('$ref','$dynamicRef') and (not isinstance(item,str) or not item.startswith('#/')):
                        raise VerdugoError('Only local JSON references are permitted')
                    if key in ('$id','externalValue'):raise VerdugoError('External resource locations are not supported')
                    nodes.append((item,depth+1))
            elif isinstance(value,list):nodes.extend((v,depth+1) for v in value)
        return
    if service=='arx':
        rows=private_json(p)
        if not isinstance(rows,list) or not 2<=len(rows)<=100:raise VerdugoError('Provide 2..100 age/zipcode rows')
        integer(p['k'],2,min(10,len(rows)))
        for row in rows:
            fields(row,('age','zipcode'));integer(row['age'],0,99)
            if not isinstance(row['zipcode'],str) or not re.fullmatch('[0-9]{5}',row['zipcode']):
                raise VerdugoError('Five-digit supplied postal codes required')
    elif service=='cc-webgraph':
        rows=p['adjacencies']
        if not isinstance(rows,list) or not 1<=len(rows)<=30:raise VerdugoError('Provide 1..30 sorted adjacency lists')
        if any(not isinstance(row,list) for row in rows) or sum(map(len,rows))>200:
            raise VerdugoError('At most 200 adjacency entries')
        for row in rows:
            for value in row:integer(value,0,10**6)
            if row!=sorted(row):raise VerdugoError('Original merge requires sorted adjacency lists')
    else:
        rows=p['events']
        if not isinstance(rows,list) or not 1<=len(rows)<=200:raise VerdugoError('Provide 1..200 request events')
        for row in rows:
            fields(row,('path','status','bytes','method'))
            if not isinstance(row['path'],str) or not re.fullmatch(r'/[A-Za-z0-9/_\-.]{0,100}',row['path']):
                raise VerdugoError('Only bounded plain request paths')
            if row['method'] not in ('GET','HEAD','POST','PUT','DELETE','PATCH','OPTIONS'):raise VerdugoError('Unsupported HTTP method')
            integer(row['status'],100,599);integer(row['bytes'],0,10**9)


def run(service,p):
    validate(service,SPECS[service][0],p)
    if not runtime_state(service)['version_matches']:raise ValueError('Native tools runtime changed')
    home=root();env={'PATH':os.defpath,'HOME':os.getcwd(),'TMPDIR':os.getcwd(),'LANG':'C.UTF-8'}
    if service=='goaccess':
        return logs(home,env,p)
    args=[str(home/'jdk/bin/java'),'-Djava.security.manager=allow','-Djava.io.tmpdir='+os.getcwd(),
          '-Xmx256m','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',
          str(home/'classes')+os.pathsep+str(home/'*'),'VerdugoJavaWorker',service]
    data=None
    if service=='openapi-generator':Path('input.json').write_text(p['secret_text'])
    elif service=='arx':data=(str(p['k'])+'\n'+'\n'.join(str(r['age'])+','+r['zipcode'] for r in private_json(p))+'\n').encode()
    else:data=('\n'.join(','.join(map(str,row)) for row in p['adjacencies'])+'\n').encode()
    with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
        proc=subprocess.run(args,input=data,stdout=out,stderr=err,env=env,timeout=40,close_fds=True)
        out.seek(0);stdout=out.read(32769);err.seek(0);stderr=err.read(65537)
    if len(stdout)>32768 or len(stderr)>65536:raise ValueError('Native output budget exceeded')
    if service=='openapi-generator':
        if proc.returncode==0 and b'No validation issues detected.' in stdout:valid=True;errors=0
        elif proc.returncode==1 and (m:=re.search(rb'\[error\] Spec has ([0-9]+) errors\.',stderr)):
            valid=False;errors=int(m.group(1))
        else:raise ValueError('Original OpenAPI validator failed unexpectedly')
        return {'schema_valid':valid,'validation_errors':errors,'code_generated':False,'external_references_fetched':False,'api_runtime_verified':False}
    if proc.returncode:raise ValueError('Original JVM operation failed')
    return json.loads(stdout)


def logs(home,env,p):
    lines=[f'203.0.113.1 - - [01/Jan/2026:00:00:00 +0000] "{r["method"]} {r["path"]} HTTP/1.1" {r["status"]} {r["bytes"]}' for r in p['events']]
    Path('input.log').write_text('\n'.join(lines)+'\n');env=dict(env,LD_LIBRARY_PATH=str(home/'goaccess/lib'))
    args=[str(home/'goaccess/bin/goaccess'),'--no-global-config','--no-term-resolver','--log-format=COMMON',
          '--no-progress','-f','input.log','-o','report.json']
    with tempfile.TemporaryFile() as sink:
        proc=subprocess.run(args,stdout=sink,stderr=sink,env=env,timeout=20,close_fds=True)
    if proc.returncode:raise ValueError('Original GoAccess parser failed')
    raw=Path('report.json').read_bytes()
    if len(raw)>1024*1024:raise ValueError('GoAccess report exceeds budget')
    doc=json.loads(raw);general=doc['general']
    if general['failed_requests'] or general['valid_requests']!=len(p['events']):raise ValueError('Original parser did not accept all events')
    counts={}
    for group in doc['status_codes']['data']:
        for row in group['items']:
            code=int(row['data'].split(' - ',1)[0]);counts[str(code)]=row['hits']['count']
    return {'requests':general['valid_requests'],'bytes':general['bandwidth'],'status_codes':counts,
            'input_scope':'supplied_request_events','real_visitors_verified':False,'source_log_files_read':False}
