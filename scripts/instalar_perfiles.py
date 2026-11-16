"""Explicit operator installer. Never imported or launched by Engine/MCP."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import venv

ROOT = Path(__file__).resolve().parents[1]


def profiles():
    result={}
    for req in sorted((ROOT/'requirements').glob('runtime*.txt')):
        if '.constraints.' in req.name: continue
        name=req.stem.removeprefix('runtime-') if req.stem!='runtime' else 'runtime'
        constraint=req.with_suffix('.constraints.txt')
        if not constraint.is_file(): raise RuntimeError('Falta constraints: '+req.name)
        result[name]=(req,constraint,'VERDUGO_'+name.upper().replace('-','_')+'_PYTHON')
    return result


def private_dir(path):
    if path.is_symlink(): raise RuntimeError('El directorio privado no puede ser un enlace')
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.stat().st_uid!=os.getuid(): raise RuntimeError('Directorio de otro usuario')
    path.chmod(0o700)


def main(argv=None):
    available=profiles()
    parser=argparse.ArgumentParser(); parser.add_argument('--perfil',action='append',choices=available)
    args=parser.parse_args(argv)
    if sys.version_info[:2]!=(3,12): raise SystemExit('Los perfiles fijados requieren Python 3.12; usa PYTHON=python3.12')
    os.umask(0o077)
    home=Path(os.environ.get('VERDUGO_HOME',str(Path.home()/'.verdugo'))).expanduser().absolute()
    private_dir(home); root=home/'runtimes'; private_dir(root)
    results=[]
    for name in args.perfil or available:
        req,constraint,env=available[name]; dest=root/name; private_dir(dest)
        started=time.monotonic(); log=home/(name+'-install.log')
        try:
            if shutil.disk_usage(root).free < 5*1024**3: raise RuntimeError('Menos de 5 GiB libres: instalación detenida para proteger el disco')
            with log.open('w') as output:
                print('Instalando perfil '+name,flush=True)
                venv.EnvBuilder(with_pip=True,symlinks=False).create(dest)
                py=dest/'bin'/'python'; py.chmod(0o700)
                for command in ([str(py),'-m','pip','install','--disable-pip-version-check','--no-cache-dir','--retries','0','--timeout','30','-r',str(req),'-c',str(constraint)],
                                [str(py),'-m','pip','check']):
                    subprocess.run(command,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=1800)
            state='installed'
        except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
            state='failed'
            print('FALLÓ '+name+': '+str(exc),file=sys.stderr)
            if log.exists(): print(log.read_text(errors='replace')[-4000:],file=sys.stderr)
        size=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file() and not p.is_symlink())
        results.append({'profile':name,'state':state,'seconds':round(time.monotonic()-started,2),'bytes':size})
        (dest/'installed.json').write_text(json.dumps({'state':state,'requirements_sha256':__import__('hashlib').sha256(req.read_bytes()+constraint.read_bytes()).hexdigest()}))
        (home/'perfiles-install.json').write_text(json.dumps({'environment':'Codespaces' if os.environ.get('CODESPACES')=='true' else 'local','profiles':results},indent=2)+'\n')
    # Preserve previously installed, still pinned profiles when installing a selection.
    exports=[]
    for name,(req,constraint,env) in available.items():
        marker=root/name/'installed.json'
        if not marker.exists(): continue
        info=json.loads(marker.read_text())
        expected=__import__('hashlib').sha256(req.read_bytes()+constraint.read_bytes()).hexdigest()
        if info.get('state')=='installed' and info.get('requirements_sha256')==expected:
            value=str(root/name/'bin'/'python'); exports.append('export '+env+'='+shlex.quote(value)); os.environ[env]=value
        else: os.environ.pop(env,None)
    env_path=home/'perfiles.env'
    env_path.write_text('\n'.join(exports)+'\n'); env_path.chmod(0o600)
    result=subprocess.run([sys.executable,'-m','verdugo','--state',':memory:','runtime-check'],cwd=ROOT,capture_output=True,text=True)
    (home/'runtime-check.json').write_text(result.stdout)
    try:
        inventory=json.loads(result.stdout)
        print(f"Rutas locales con versiones disponibles: {inventory['matching_installations']}/{inventory['implemented']}. Metadatos, no certificación de ejecución.")
    except ValueError:
        print('runtime-check falló: '+result.stderr,file=sys.stderr); return 1
    print('Carga los perfiles con: source '+shlex.quote(str(env_path)))
    return int(any(r['state']=='failed' for r in results))


if __name__=='__main__': raise SystemExit(main())
