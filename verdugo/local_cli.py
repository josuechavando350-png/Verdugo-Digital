"""Pinned fixed CLI recipes, invoked only by the existing resource-limited worker."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
from collections import Counter

from .common import VerdugoError, fields, identifier
from .local_native import checked

SPECS = {
    'google-maps-scraper': ('places.inspect', 'compiled-source:google-maps-scraper', 'e0c1d501e49cdcd5c6b2cecd2a032831f6ee9ba8'),
    'grype': ('packages.audit', 'cli:grype', 'cd1f23eb50dfb52647090158f453c7359172591f'),
    'sops': ('encryption.verify', 'cli:sops', '9aa10f12bcd82400b7eb73331dd7a87a93bb17f7'),
    'gitleaks': ('text.scan', 'cli:gitleaks', '5f6ec56cfa6f8c67648d863582c7ae2f206d5c1c'),
    'restic': ('archive.verify', 'cli:restic', 'c734245fd3ae9bcac8ab3aaafb4482d4b5d0ae92'),
    'syft': ('packages.inventory', 'cli:syft', 'a0c0d3890a9d79421c403e8fcadec50a2e55bf21'),
    'vale': ('prose.lint', 'cli:vale', '4ce91ef208b37f9ac2894766e8cd7b33ffe3baed'),
}
MAPS_SOURCE = Path(__file__).with_name('native_maps')
MAPS_FILES = {'LICENSE': '3b74f7e7dc75d6ec836c6dc3f072ce510e2a1cbf34aff1f3e7fbc46105ffcd2b', 'main.go': 'fdac79e4386ddea08ab905f3e1f835906046995ec633ffb3c450b35a23c6b977', 'go.mod': 'f699e36c116b6842700fa9f80b34be4404f892aa1d9d8ff4753d5ca5e6f58593', 'gmaps/entry.go': '8b80dec3e063461584e4f8fcbfecf224752f6010a194d20ec03513b4636d943e'}
ENV = 'VERDUGO_CLI_ROOT'


def root():
    value = os.getenv(ENV)
    if not value or not Path(value).is_absolute() or '..' in Path(value).parts or any(c in value for c in ('\x00','\n','\r')):
        raise VerdugoError('An absolute administrator CLI runtime is required')
    return checked(Path(value), directory=True)


def runtime_state(service):
    op, dist, expected = SPECS[service]
    version = binding = None
    try:
        home = root()
        manifest = checked(home/'manifest.json').read_bytes()
        row = json.loads(manifest)['binaries'][service]
        binary = checked(home/'bin'/service, budget=512*1024*1024)
        if not os.access(binary, os.X_OK) or row['source_commit'] != expected:
            raise ValueError('Binary is not the pinned reviewed build')
        h = hashlib.sha256()
        with binary.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
        if h.hexdigest() != row['sha256']: raise ValueError('Binary changed')
        if service == 'google-maps-scraper':
            for name, expected_sha in MAPS_FILES.items():
                source = checked(MAPS_SOURCE/name, budget=128*1024).read_bytes()
                if hashlib.sha256(source).hexdigest()!=expected_sha:raise ValueError('Maps parser source changed')
                h.update(source)
        if service == 'grype':
            database = checked(home/'grype-db/6/vulnerability.db',budget=5*1024**3)
            dh = hashlib.sha256()
            with database.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):dh.update(block)
            if dh.hexdigest()!=row['database_sha256']:raise ValueError('Vulnerability snapshot changed')
            h.update(dh.digest())
        if service == 'sops':
            helper = checked(home/'bin/age-keygen',budget=64*1024*1024)
            helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
            if not os.access(helper,os.X_OK) or row['age_keygen_version']!='v1.3.1' or helper_sha!=row['age_keygen_sha256']:
                raise ValueError('Encryption helper changed')
            h.update(helper_sha.encode())
        version = expected
        binding = hashlib.sha256(str(home).encode()+manifest+h.digest()).hexdigest()
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        version = None
    return {'distribution':dist, 'distribution_kind':'pinned-native-cli', 'expected':expected,
            'installed':version, 'version_matches':version==expected, 'extra_distributions':{},
            'operation':op, 'execution_verified':False, 'runtime_binding':binding}


def validate(service, operation, p):
    from .local_runtime import string
    if service not in SPECS or operation != SPECS[service][0]: raise VerdugoError('Unsupported fixed CLI operation')
    if service == 'google-maps-scraper':
        from .local_native_tools import private_json
        fields(p,('dataset','secret_text'))
        if p['dataset'] not in ('demo','real'):raise VerdugoError('Explicit dataset required')
        rows=private_json(p)
        if not isinstance(rows,list) or not 1<=len(rows)<=10:raise VerdugoError('Provide 1..10 supplied Maps JSON payloads')
        for row in rows:
            if not isinstance(row,list) or not 7<=len(row)<=40 or not isinstance(row[6],list) or not 14<=len(row[6])<=220:
                raise VerdugoError('Expected the original Maps array payload shape')
        pending=[(rows,0)];count=0
        while pending:
            value,depth=pending.pop();count+=1
            if depth>16 or count>4000:raise VerdugoError('Maps payload is too complex')
            if isinstance(value,list):pending.extend((v,depth+1) for v in value)
            elif isinstance(value,dict):raise VerdugoError('Only original array payloads and scalars are supported')
            elif isinstance(value,float):
                import math
                if not math.isfinite(value):raise VerdugoError('Finite numeric payload values required')
        return
    required = {'gitleaks':('secret_text',), 'restic':('secret_text',), 'syft':('packages',), 'vale':('text',),'sops':('secret_text',),'grype':('packages',)}[service]
    fields(p, ('dataset', *required))
    if p['dataset'] not in ('demo','real'): raise VerdugoError('An explicit dataset is required')
    if service not in ('syft','grype'):
        string(p[required[0]], 16000)
    else:
        rows = p['packages']
        if not isinstance(rows,list) or not 1 <= len(rows) <= 30: raise VerdugoError('Provide 1..30 npm package records')
        names = []
        for row in rows:
            fields(row,('name','version'))
            if not isinstance(row['name'],str) or not re.fullmatch(r'(?:@[a-z0-9_-]+/)?[a-z0-9_-]{1,70}',row['name']):
                raise VerdugoError('Invalid package name')
            if not isinstance(row['version'],str) or not re.fullmatch(r'[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}',row['version']):
                raise VerdugoError('Exact bounded numeric package version required')
            names.append(row['name'])
        if len(set(names)) != len(names): raise VerdugoError('Duplicate package name')


def invoke(service, args, payload=b'', extra=None, limit=1024*1024):
    home = root()
    env = {'PATH':os.defpath,'HOME':os.getcwd(),'TMPDIR':os.getcwd(),'LANG':'C.UTF-8',
           'GOMAXPROCS':'2','NO_COLOR':'1','DO_NOT_TRACK':'1','SYFT_CHECK_FOR_APP_UPDATE':'false'}
    env.update(extra or {})
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        result = subprocess.run([str(home/'bin'/service), *args], input=payload,
                                stdout=out, stderr=err, timeout=60, env=env, close_fds=True)
        out.seek(0); data = out.read(limit+1)
        if result.returncode or len(data)>limit: raise ValueError('Fixed CLI operation failed')
    return data


def run(service, p):
    if not runtime_state(service)['version_matches']: raise ValueError('CLI runtime changed')
    if service == 'google-maps-scraper':
        result=json.loads(invoke(service, [], p['secret_text'].encode()))
        rows=result['records']
        from .local_runtime import finite
        from .common import integer
        if not isinstance(rows,list) or not 1<=len(rows)<=10:raise ValueError('Original Maps parser result shape changed')
        for row in rows:
            integer(row['review_count'],0,10**9);finite(row['rating'],0,5);integer(row['categories'],1,100);integer(row['opening_days'],0,7)
            if type(row['website_present']) is not bool:raise ValueError('Invalid website presence')
        return result | {'parser_scope':'supplied Google Maps array payloads; no scraping', 'input_payload_retained':False}
    if service == 'gitleaks':
        data = json.loads(invoke(service, ['stdin','--report-format','json','--report-path','-',
              '--redact=100','--exit-code=0','--no-banner','--no-color','--log-level','error',
              '--max-decode-depth','0','--max-archive-depth','0'], p['secret_text'].encode()))
        if data is None: data = []
        if not isinstance(data,list) or len(data)>1000: raise ValueError('Unexpected scan result')
        counts = Counter(row['RuleID'] for row in data)
        return {'findings':len(data),'by_rule':[{'rule_id':rule,'count':count} for rule,count in sorted(counts.items())],
                'input_persisted':False,'credentials_tested':False,'exhaustive_detection':False}
    if service == 'restic':
        password = secrets.token_urlsafe(32)
        extra = {'RESTIC_REPOSITORY':str(Path.cwd()/'archive'), 'RESTIC_PASSWORD':password,
                 'RESTIC_CACHE_DIR':str(Path.cwd()/'cache')}
        invoke(service,['init','--json'],extra=extra)
        payload=p['secret_text'].encode()
        invoke(service,['backup','--stdin','--stdin-filename','document.txt','--json'],payload,extra)
        restored=invoke(service,['dump','latest','/document.txt'],extra=extra,limit=20000)
        if restored != payload: raise ValueError('Archive round trip mismatch')
        invoke(service,['check','--read-data','--json'],extra=extra)
        return {'bytes_verified':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
                'roundtrip_verified':True,'temporary_only':True,'durable_backup_created':False}
    if service == 'syft':
        dest=Path('input');dest.mkdir()
        entries={r['name']:r['version'] for r in p['packages']}
        (dest/'package.json').write_text(json.dumps({'name':'verdugo-input','version':'1.0.0','dependencies':entries}))
        package_rows={'':{'name':'verdugo-input','version':'1.0.0','dependencies':entries}}
        package_rows.update({'node_modules/'+n:{'version':v} for n,v in entries.items()})
        (dest/'package-lock.json').write_text(json.dumps({'name':'verdugo-input','version':'1.0.0','lockfileVersion':3,'packages':package_rows}))
        raw=json.loads(invoke(service,['scan','dir:input','--override-default-catalogers','javascript-lock-cataloger','-o','syft-json','--quiet']))
        packages=sorted({(r['name'],r['version']) for r in raw['artifacts'] if r['name']!='verdugo-input'})
        if packages != sorted(entries.items()): raise ValueError('Catalogued packages do not match the submitted lock records')
        return {'packages':[{'name':n,'version':v} for n,v in packages],'count':len(packages),
                'scope':'submitted npm lock records only','installed_packages_verified':False,'vulnerabilities_checked':False}
    if service == 'grype':
        from urllib.parse import quote
        components=[{'type':'library','name':r['name'],'version':r['version'],
                     'purl':'pkg:npm/'+quote(r['name'],safe='/')+'@'+r['version']} for r in p['packages']]
        Path('sbom.json').write_text(json.dumps({'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'components':components}))
        extra={'GRYPE_DB_CACHE_DIR':str(root()/'grype-db'),'GRYPE_DB_AUTO_UPDATE':'false',
               'GRYPE_CHECK_FOR_APP_UPDATE':'false','GRYPE_DB_VALIDATE_AGE':'false'}
        raw=json.loads(invoke(service,['sbom:sbom.json','-o','json','--quiet'],extra=extra))
        rows=raw['matches']
        if not isinstance(rows,list) or len(rows)>2000:raise ValueError('Vulnerability result budget')
        counts=Counter(r['vulnerability']['severity'] for r in rows)
        if not set(counts)<={'Unknown','Negligible','Low','Medium','High','Critical'}:raise ValueError('Unknown severity')
        metadata=json.loads((root()/'manifest.json').read_text())['binaries'][service]
        return {'matches':len(rows),'by_severity':dict(sorted(counts.items())),'packages_submitted':len(components),
                'snapshot_sha256':metadata['database_sha256'],'snapshot_source':metadata['database_source'],
                'scope':'submitted npm package versions against a fixed database; not exploitability proof',
                'network_calls':0,'installed_assets_verified':False}
    if service == 'sops':
        key=Path('age-key.txt')
        invoke('age-keygen',['-o',str(key)])
        public=next(line.split(': ',1)[1] for line in key.read_text().splitlines() if line.startswith('# public key: '))
        if not re.fullmatch(r'age1[a-z0-9]+',public):raise ValueError('Invalid ephemeral recipient')
        plain={'content':p['secret_text']}
        Path('plain.json').write_text(json.dumps(plain))
        extra={'SOPS_AGE_KEY_FILE':str(key.resolve())}
        encrypted=invoke(service,['--encrypt','--age',public,'--input-type','json','--output-type','json','plain.json'],extra=extra)
        Path('encrypted.json').write_bytes(encrypted)
        restored=json.loads(invoke(service,['--decrypt','--input-type','json','--output-type','json','encrypted.json'],extra=extra))
        if restored!=plain:raise ValueError('Encryption round trip mismatch')
        return {'roundtrip_verified':True,'encrypted_bytes':len(encrypted),'input_bytes':len(p['secret_text'].encode()),
                'temporary_only':True,'durable_encrypted_storage':False,'key_persisted':False}
    if service == 'vale':
        styles=Path('styles/Verdugo');styles.mkdir(parents=True)
        (styles/'Filler.yml').write_text("extends: existence\nmessage: 'Review unnecessary emphasis.'\nlevel: warning\nignorecase: true\ntokens:\n  - obviamente\n  - simplemente\n  - obviously\n  - simply\n")
        Path('.vale.ini').write_text("StylesPath = styles\nMinAlertLevel = warning\n[*.txt]\nBasedOnStyles = Verdugo\n")
        raw=json.loads(invoke(service,['--no-global','--config','.vale.ini','--output','JSON','--no-exit','--ext','.txt'],p['text'].encode()))
        rows=[r for items in raw.values() for r in (items or [])]
        return {'issues':len(rows),'by_check':dict(sorted(Counter(r['Check'] for r in rows).items())),
                'scope':'fixed filler-word style rule; not a complete editorial review'}
    raise ValueError('Unsupported fixed CLI recipe')

