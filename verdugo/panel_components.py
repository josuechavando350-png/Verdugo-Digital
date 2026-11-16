"""Fail-closed panel integration evidence. Does not install or execute dependencies."""
import json
from functools import lru_cache
from pathlib import Path
from .common import VerdugoError
ROOT=Path(__file__).resolve().parents[1]

def validate(root=ROOT):
    root=Path(root)
    def read(path):
        p=root/path
        if p.is_symlink() or not p.is_file() or p.stat().st_size>2*1024*1024: raise VerdugoError('Invalid panel evidence file: '+path)
        return p.read_text(encoding='utf-8')
    try:
        table=json.loads(read('sources/panel.json'))
        expected={r['id'] for r in json.loads(read('sources/connections.json'))['records'] if r['kind']=='componente'}
        rows=table['components']
        if table['schema']!=1 or len(rows)!=len(expected) or {r['id'] for r in rows}!=expected: raise ValueError('Component coverage')
        sources={r['id']:r for f in sorted((root/'sources/parts').glob('*.json')) for r in json.loads(f.read_text())}
        package=json.loads(read('panel/package.json'));lock=json.loads(read('panel/package-lock.json'))['packages']
        deps=package['dependencies']|package['devDependencies'];pyreq=read('panel/requirements.txt').splitlines();pylock=read('panel/constraints.txt').splitlines()
        integrated=set()
        for row in rows:
            if type(row['integrated']) is not bool or not row['reason'].strip():raise ValueError('Integration decision')
            if not row['integrated']:continue
            sid=row['id'];source=row['source'];version=row['version'];name=row['package']
            if source['commit_sha']!=sources[sid]['commit_sha']:raise ValueError('Source commit '+sid)
            original=sources[sid]['repository']
            if source['repository']!=original and not (sid=='driverjs' and original=='kamranahmedse/driver.js' and source['repository']=='nilbuild/driver.js'):raise ValueError('Source repository '+sid)
            if len(source['blob_sha'])!=40 or not source['path'] or not version:raise ValueError('Version source '+sid)
            if row['ecosystem']=='npm':
                if deps.get(name)!=version or lock['']['dependencies'].get(name,lock[''].get('devDependencies',{}).get(name))!=version or lock['node_modules/'+name]['version']!=version:raise ValueError('Package version '+sid)
            elif row['ecosystem']=='python' and sid=='fastapi':
                if name+'=='+version not in pyreq or name+'=='+version not in pylock:raise ValueError('Python version '+sid)
            else:raise ValueError('Unknown package ecosystem')
            usage=row['usage'];body=read(usage['file']);test=row['test']
            if usage['import'] not in body or usage['call'] not in body or test['name'] not in read(test['file']):raise ValueError('Missing usage or test '+sid)
            integrated.add(sid)
        return frozenset(integrated)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise VerdugoError('Panel evidence invalid: '+str(exc)) from None

@lru_cache(maxsize=1)
def integrated_ids():
    return validate()
