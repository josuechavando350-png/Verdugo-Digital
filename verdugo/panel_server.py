"""Local panel API. Optional FastAPI dependencies; the only state store is Engine."""
from contextlib import contextmanager
import base64
import hashlib
import re
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
from threading import RLock
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .common import VerdugoError, fields, identifier, integer
from .engine import Engine
from . import ads, commercial, local_runtime, product, subscriptions
from .diagnostics import doctor

ROOT = Path(__file__).resolve().parents[1]


def local_token(path):
    path=Path(path).expanduser().absolute()
    parent=path.parent
    if parent.is_symlink(): raise VerdugoError('Token directory cannot be a symlink')
    parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=parent.stat()
    if info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise VerdugoError('Token directory requires owner-only mode 0700')
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError: pass
    else:
        with os.fdopen(fd,'w') as f: f.write(secrets.token_urlsafe(32)+'\n')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o777!=0o600 or info.st_nlink!=1:
            raise VerdugoError('Token requires a regular owner-only mode 0600 file')
        token=f.read(128).strip()
    if len(token)<32 or len(token)>100: raise VerdugoError('Invalid local token')
    return token


def create_app(config_path, state_path, token, role='operator', host='127.0.0.1:8766', assets=None):
    if role not in ('operator','viewer'): raise VerdugoError('Panel requires operator or viewer')
    if not isinstance(token,str) or len(token)<32: raise VerdugoError('Invalid local token')
    config_path=Path(config_path).expanduser()
    if state_path==':memory:': raise VerdugoError('Panel requires persistent Engine state')
    state_path=str(Path(state_path).expanduser())
    csrf=secrets.token_urlsafe(32); lock=RLock()
    folder=Path(assets) if assets else ROOT/'panel/dist'
    hashes=set()
    if folder.is_dir():
        for page in folder.rglob('*.html'):
            for script in re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',page.read_text(),re.S):
                if script.strip(): hashes.add("'sha256-"+base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()+"'")
    script_policy="script-src 'self' "+' '.join(sorted(hashes))
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    # Host must come only from trusted startup configuration, never a query parameter.
    allowed_hosts={host}
    def configuration():
        try:
            cfg=json.loads(config_path.read_text())
            if not isinstance(cfg.get('tenants'),dict): raise ValueError()
            return cfg
        except (OSError,ValueError,TypeError): raise VerdugoError('Configuración local no disponible') from None
    @contextmanager
    def engine(tenant):
        cfg=configuration(); identifier(tenant)
        if tenant not in cfg['tenants']: raise VerdugoError('Cliente no configurado')
        e=Engine(state_path,cfg,tenant,actor='panel-local',role=role)
        try: yield e
        finally:e.close()
    @app.middleware('http')
    async def boundary(request,call_next):
        def rejected(message,status=403): return JSONResponse({'error':message},status_code=status,headers={'Cache-Control':'no-store'})
        request_host=request.headers.get('host','')
        if request_host not in allowed_hosts: return rejected('Host no autorizado')
        origin=request.headers.get('origin')
        if origin:
            parsed=urlsplit(origin)
            if parsed.netloc!=request_host or parsed.scheme not in ('http','https') or parsed.path or parsed.query or parsed.fragment:
                return rejected('Origen no autorizado')
        if request.url.path.startswith('/api/'):
            credential=request.headers.get('x-verdugo-token','')
            if not hmac.compare_digest(credential.encode(),token.encode()): return rejected('Token local requerido',401)
            if request.method not in ('GET','HEAD'):
                if role!='operator': return rejected('Rol operator requerido')
                if not origin or not hmac.compare_digest(request.headers.get('x-verdugo-csrf','').encode(),csrf.encode()): return rejected('Confirmación CSRF requerida')
                if request.headers.get('content-type','').split(';')[0]!='application/json': return rejected('Se requiere JSON',415)
                try: length=int(request.headers.get('content-length','0'))
                except ValueError: return rejected('Tamaño inválido',400)
                if length<0 or length>32768: return rejected('Solicitud demasiado grande',413)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']=f"default-src 'self'; {script_policy}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response
    @app.exception_handler(VerdugoError)
    async def handled(request,exc): return JSONResponse({'error':str(exc)},status_code=400)
    @app.get('/api/session')
    def session(): return {'role':role,'csrf':csrf,'tenants':sorted(configuration()['tenants']),'local_only':True}
    @app.get('/api/clients')
    def clients():
        rows=[]
        for tenant in sorted(configuration()['tenants']):
            with engine(tenant) as e: rows.append(subscriptions.state(e))
        return {'clients':rows,'verification':'operator_declared','role':role}
    @app.post('/api/clients/{tenant}/{action}')
    async def change(tenant:str, action:str, request:Request):
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>32768: return JSONResponse({'error':'Solicitud demasiado grande'},status_code=413)
        try: body=json.loads(raw)
        except (ValueError,UnicodeError): raise VerdugoError('JSON inválido') from None
        fields(body,('confirm',),('label','grace_days','until','months','reason'))
        if body['confirm'] is not True: raise VerdugoError('Confirma explícitamente el cambio')
        allowed={'register':('label','grace_days'),'pay':('until','months'),'pause':('reason',),'resume':()}
        if action not in allowed: raise VerdugoError('Acción no admitida')
        fields(body,('confirm',),allowed[action])
        with lock,engine(tenant) as e:
            if action=='register': return subscriptions.register(e,body.get('label'),body.get('grace_days',0),True)
            if action=='pay': return subscriptions.pay(e,body.get('until'),body.get('months'),True)
            if action=='pause': return subscriptions.pause(e,body.get('reason'),True)
            return subscriptions.resume(e,True)
    @app.get('/api/ads')
    def ads_report(request:Request):
        p=dict(request.query_params); tenant=p.pop('tenant','nexus')
        if 'budget_month' in p:
            try: p['budget_month']=float(p['budget_month'])
            except ValueError: raise VerdugoError('Presupuesto inválido') from None
        with engine(tenant) as e: return ads.report(e,p)
    @app.get('/api/funnel')
    def funnel(tenant:str='nexus',dataset:str='real'):
        with engine(tenant) as e:
            subscriptions.check(e)
            return {'sales':commercial.report(e,{'dataset':dataset}),'ads':ads.report(e,{'dataset':dataset})}
    @app.get('/api/product')
    def status(tenant:str='nexus'):
        with engine(tenant) as e:
            overview=product.overview(e)
            availability=local_runtime.inventory()
            return {'product':overview,'runtime':availability,'doctor':doctor(e)}
    @app.get('/api/events')
    def events(tenant:str='nexus'):
        with engine(tenant) as e:
            rows=e.db.execute('SELECT id,kind,at FROM events WHERE tenant=? ORDER BY id DESC LIMIT 200',(e.tenant,)).fetchall()
            return {'events':[dict(r) for r in rows],'limit':200,'tenant':tenant}
    # Unknown API paths never fall back to the HTML application.
    @app.api_route('/api/{path:path}',methods=['GET','POST','PUT','DELETE','PATCH'])
    def unknown(path:str): return JSONResponse({'error':'Ruta no disponible'},status_code=404)
    if folder.is_dir(): app.mount('/',StaticFiles(directory=folder,html=True),name='panel')
    else:
        @app.get('/')
        def missing(): return JSONResponse({'error':'Construye el panel: npm ci --prefix panel && npm run build --prefix panel'},status_code=503)
    return app


def run(config,state,role,port):
    import uvicorn
    integer(port,1024,65535)
    if not config: raise VerdugoError('Panel requires --config')
    root=Path(os.environ.get('VERDUGO_HOME',str(Path.home()/'.verdugo'))).expanduser()
    path=root/('panel-'+role+'.token')
    token=local_token(path)
    host='127.0.0.1:'+str(port)
    # Private Codespaces forwarding is enabled by the operator in the Ports UI.
    if os.environ.get('CODESPACES')=='true':
        name=os.environ.get('CODESPACE_NAME',''); domain=os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN','')
        import re
        if not re.fullmatch(r'[a-z0-9-]+',name) or not re.fullmatch(r'[a-z0-9.-]+',domain):
            raise VerdugoError('Invalid Codespaces forwarding environment')
        host=name+'-'+str(port)+'.'+domain
    app=create_app(config,state,token,role,host)
    print('Verdugo Panel: http://127.0.0.1:'+str(port)+' · rol '+role,flush=True)
    print('Token privado: '+str(path)+' (cópialo en el panel; nunca en la URL).',flush=True)
    uvicorn.run(app,host='127.0.0.1',port=port,access_log=False,log_level='warning',proxy_headers=False)
