"""Real additional upstream applications; never health-check-only certification.

All services and credentials belong to the disposable internal-network lab.
Business records are created/read through original APIs. Administrative metadata
may be read from a provider's own database to discover its bootstrapped workspace.
"""
from __future__ import annotations
import base64
import http.cookiejar
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class NativeSession:
    def __init__(self, native):
        self.n = native
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            native.NoRedirect(), urllib.request.HTTPCookieProcessor(self.cookies))

    def call(self, url, *, data=None, method=None, headers=None, statuses=(200,), raw=False, body_bytes=None, response_bytes=False):
        u=urllib.parse.urlsplit(url)
        if u.scheme!='http' or u.username or u.password or u.fragment or (
                u.hostname!='127.0.0.1' and u.scheme+'://'+u.netloc not in self.n.NATIVE_ORIGINS):
            raise self.n.AcceptanceError('extra_origin_not_authorized')
        body=None; h=dict(headers or {})
        if body_bytes is not None:
            if data is not None or not isinstance(body_bytes,bytes) or len(body_bytes)>1_048_576:
                raise self.n.AcceptanceError('extra_invalid_binary_body')
            body=body_bytes;h.setdefault('Content-Type','application/octet-stream')
        if data is not None:
            body=json.dumps(data).encode();h.setdefault('Content-Type','application/json')
        req=urllib.request.Request(url,data=body,headers=h,method=method or ('POST' if body is not None else 'GET'))
        try:
            with self.opener.open(req,timeout=20) as r:
                if r.status not in statuses:raise self.n.AcceptanceError('extra_http_status_'+str(r.status))
                value=r.read(1_048_577)
                if len(value)>1_048_576:raise self.n.AcceptanceError('extra_response_too_large')
                if response_bytes:return value
                if raw:return value.decode('utf8')
                return json.loads(value) if value.strip() else {'http_status':r.status}
        except urllib.error.HTTPError as e:
            # Never return a provider's private body or credentials in diagnostics.
            raise self.n.AcceptanceError('extra_http_status_'+str(e.code)) from None
        except (urllib.error.URLError,TimeoutError,ConnectionError):
            raise self.n.AcceptanceError('extra_http_unreachable') from None
        except (json.JSONDecodeError,UnicodeError):
            raise self.n.AcceptanceError('extra_invalid_response') from None

    def denied(self,url,*,data=None):
        clean=NativeSession(self.n)
        try:clean.call(url,data=data,statuses=(200,201,204))
        except self.n.AcceptanceError as e:
            if str(e) in ('extra_http_status_401','extra_http_status_403'):return True
            raise
        raise self.n.AcceptanceError('extra_missing_auth_accepted')


class Application:
    id=''
    images={}
    port=3000
    def __init__(self,native):
        self.n=native;self.http=NativeSession(native);self.services=[];self.proof={}
    def bind(self,*,start,docker,refs,temp,network,report,**_):
        self.start=start;self.docker=docker;self.refs=refs;self.temp=Path(temp);self.network=network;self.report=report
    def find(self,suffix):
        found=self.docker('ps','-a','--filter','network='+self.network,'--filter','name=-'+suffix,'--format','{{.Names}}').splitlines()
        exact=[x for x in found if x.endswith('-'+suffix)]
        if len(exact)!=1:raise self.n.AcceptanceError(self.id+'_container_not_unique')
        return exact[0]
    def launch(self,suffix,key,**kwargs):
        url=self.start(suffix,self.refs[key],**kwargs)
        self.services.append(self.find(suffix));return url
    def refresh(self,suffix,port):
        return self.n.native_origin(json.loads(self.docker('inspect',self.find(suffix)))[0],self.network,port)
    def secret(self):
        value=secrets.token_hex(32);self.n.mask_secret(value);return value
    def check(self,name):self.report['checks'][self.id+'_'+name]=True
    def wait(self,fn,seconds=240):return self.n.wait_until(fn,seconds=seconds)
    def restart(self):
        # Restart the provider's application process; dependent databases retain state.
        self.docker('restart',self.find(self.id),timeout=120)
        self.base=self.refresh(self.id,self.port);self.http=NativeSession(self.n)
    def verify(self):raise NotImplementedError


class Dittofeed(Application):
    id='dittofeed'
    images={'extra_postgres':'postgres@sha256:fc41cfa8a90c09e84dd723ee764be4b2f59ba6c98b1e5b3fca540adddf68a5ba',
            'ditto_clickhouse':'clickhouse/clickhouse-server@sha256:cd450891db46cc6ffe313ca2b0fb7dbfb897a6873ca74a724cbe050a2cf62621',
            'ditto_temporal':'temporalio/auto-setup@sha256:b8bdd2208877ba6178bd9e46e162590965b170577659f4b1add95d9f1a69a5c2',
            'dittofeed':'dittofeed/dittofeed-lite@sha256:f8e55e9469892434b8e9afe2953d023da70772df67dd98ae742f4f07f9ea6617'}

    def install(self,**ctx):
        self.bind(**ctx)
        password=self.secret();self.password=self.secret();chpass=self.secret();session=self.secret()
        self.launch('ditto-postgres','extra_postgres',alias='ditto-postgres',env={
            'POSTGRES_PASSWORD':password,'POSTGRES_USER':'postgres','POSTGRES_DB':'dittofeed'})
        pg=self.find('ditto-postgres')
        self.wait(lambda:self.docker('exec',pg,'pg_isready','-U','postgres','-d','dittofeed',timeout=10))
        self.launch('ditto-clickhouse','ditto_clickhouse',alias='ditto-clickhouse',env={
            'CLICKHOUSE_USER':'dittofeed','CLICKHOUSE_PASSWORD':chpass,'CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT':'1'})
        ch=self.find('ditto-clickhouse')
        self.wait(lambda:self.docker('exec',ch,'clickhouse-client','--user','dittofeed','--password',chpass,'--query','SELECT 1',timeout=15))
        self.launch('ditto-temporal','ditto_temporal',alias='ditto-temporal',port=7233,env={
            'DB':'postgresql','DB_PORT':'5432','POSTGRES_USER':'postgres','POSTGRES_PWD':password,
            'POSTGRES_SEEDS':'ditto-postgres','SKIP_DEFAULT_NAMESPACE_CREATION':'false'})
        temporal=self.find('ditto-temporal')
        self.wait(lambda:self.docker('exec',temporal,'tctl','--address','ditto-temporal:7233','cluster','health',timeout=15))
        self.wait(lambda:self.docker('exec',temporal,'tctl','--address','ditto-temporal:7233','--namespace','default','namespace','describe',timeout=15))
        self.base=self.launch('dittofeed','dittofeed',port=3000,env={
            'NODE_ENV':'production','WORKSPACE_NAME':'Native','AUTH_MODE':'single-tenant',
            'SECRET_KEY':session,'PASSWORD':self.password,'SESSION_COOKIE_SECURE':'false',
            'DATABASE_USER':'postgres','DATABASE_PASSWORD':password,'DATABASE_HOST':'ditto-postgres','DATABASE_PORT':'5432',
            'CLICKHOUSE_HOST':'http://ditto-clickhouse:8123','CLICKHOUSE_USER':'dittofeed','CLICKHOUSE_PASSWORD':chpass,
            'TEMPORAL_ADDRESS':'ditto-temporal:7233','BOOTSTRAP':'true','BOOTSTRAP_EVENTS':'false',
            'DASHBOARD_API_BASE':'http://localhost:3000','DASHBOARD_URL':'http://localhost:3000',
            'NODE_OPTIONS':'--max-old-space-size=1000','LOG_CONFIG':'false'})
        self.wait(lambda:self.http.call(self.base+'/api/') is not None,seconds=360)
        # Discover only the app's bootstrap-created administrative workspace, not events.
        sql='SELECT id FROM "Workspace" WHERE name=\'Native\' LIMIT 1'
        self.workspace=self.wait(lambda:self.docker('exec',pg,'psql','-U','postgres','-d','dittofeed','-tAc',sql,timeout=10),seconds=240).strip()
        import uuid
        try:uuid.UUID(self.workspace)
        except ValueError:raise self.n.AcceptanceError('dittofeed_workspace_invalid') from None
        self.login()
        keys=self.http.call(self.base+'/api/settings/write-keys?'+urllib.parse.urlencode({'workspaceId':self.workspace}))
        if not isinstance(keys,list) or not keys:raise self.n.AcceptanceError('dittofeed_write_key_missing')
        entry=keys[0]
        self.write_key='Basic '+base64.b64encode((entry['secretId']+':'+entry['writeKeyValue']).encode()).decode()
        self.n.mask_secret(entry['writeKeyValue']);self.n.mask_secret(self.write_key)
        self.http.denied(self.base+'/api/events?'+urllib.parse.urlencode({'workspaceId':self.workspace,'limit':1}))
        self.check('rejects_missing_auth')

    def login(self):
        self.http.call(self.base+'/api/public/single-tenant/login',data={'password':self.password})

    def exchange(self,identity):
        self.identity=identity
        self.http.call(self.base+'/api/public/apps/track',data={
            'userId':identity['subject'],'event':identity['event_name'],'messageId':identity['event_id'],
            'properties':{'route':identity['route'],'mautic_contact':identity['contact_id']}},
            headers={'Authorization':self.write_key},statuses=(200,204))
        self.wait(self.read,seconds=180);self.check('native_readback')
        self.proof={'message_id':identity['event_id'],'route_read_back':identity['route']}
        return identity['route']

    def read(self):
        i=self.identity
        query=urllib.parse.urlencode({'workspaceId':self.workspace,'messageId':i['event_id'],'limit':10})
        value=self.http.call(self.base+'/api/events?'+query)
        rows=value.get('events',[])
        matching=[r for r in rows if r.get('messageId')==i['event_id'] and r.get('userId')==i['subject']]
        if len(matching)!=1:return False
        props=matching[0].get('traits','{}');props=json.loads(props) if isinstance(props,str) else props
        return props.get('route')==i['route'] and matching[0].get('event')==i['event_name']

    def verify(self):
        self.wait(lambda:self.http.call(self.base+'/api/') is not None)
        self.login();self.wait(self.read);self.check('after_restart')


REGISTRY={'dittofeed':Dittofeed}
