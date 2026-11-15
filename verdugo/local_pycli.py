"""Two fixed original CLI entry points; temporary data and no network."""
from pathlib import Path
import re
from .common import fields, VerdugoError
SPECS = {'dvc': ('data.roundtrip', 'dvc', '3.67.1'),
         'dnstwist': ('domain.variants', 'dnstwist', '20250130')}

def validate(service, operation, p):
    from .local_runtime import string
    if service not in SPECS or operation != SPECS[service][0]: raise VerdugoError('Unsupported fixed Python CLI operation')
    fields(p, ('dataset', 'secret_text' if service == 'dvc' else 'domain'))
    if p['dataset'] not in ('demo','real'): raise VerdugoError('Explicit dataset required')
    if service == 'dvc': string(p['secret_text'],16000)
    elif not isinstance(p['domain'],str) or not re.fullmatch(r'[a-z][a-z0-9]{1,40}\.[a-z]{2,12}',p['domain']):
        raise VerdugoError('Use a bounded ASCII domain without a URL or subdomains')

def run(service,p):
    if service == 'dvc':
        import os, hashlib
        os.environ['DVC_NO_ANALYTICS']='1'
        from dvc.cli import main
        def command(args):
            if main(args) != 0: raise ValueError('Fixed DVC command failed')
        command(['init','--no-scm','--quiet'])
        payload=p['secret_text'].encode()
        file=Path('document.txt');file.write_bytes(payload)
        command(['add','document.txt','--quiet'])
        file.unlink()
        command(['checkout','document.txt.dvc','--quiet'])
        if file.read_bytes()!=payload: raise ValueError('DVC restore mismatch')
        return {'bytes_verified':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
                'roundtrip_verified':True,'remote_configured':False,'durable_backup_created':False}
    if service == 'dnstwist':
        import dnstwist
        rows=dnstwist.run(domain=p['domain'],format='list',fuzzers='omission,transposition')
        if not isinstance(rows,list) or len(rows)>100: raise ValueError('Unexpected domain variants')
        variants=sorted({r['domain'] for r in rows if r['domain']!=p['domain']})
        return {'domains':variants,'count':len(variants),'dns_queried':False,'registration_checked':False}
    raise ValueError('Unsupported fixed Python CLI recipe')
