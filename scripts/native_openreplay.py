"""Original OpenReplay project API, with authentic schema/authentication.

This is a bounded configuration contract, NOT a session-recording acceptance.
The current profile deliberately does not claim that collector/storage playback
has been deployed. No project/session/business record is seeded into databases.
"""
import hashlib
import json
from pathlib import Path
from native_extra_apps import Application, NativeSession

SOURCE_SHA='046f5988e130f42d0fe8a0fefe47a7f93a12b6e0'
ROOT=Path(__file__).resolve().parents[1]


def source_schema(native, name):
    root=ROOT/'upstream'/'openreplay'
    actual=native.command(['git','-C',str(root),'rev-parse','HEAD'])
    if actual!=SOURCE_SHA:raise native.AcceptanceError('openreplay_schema_source_revision_mismatch')
    if name not in ('init_pg_schema.sql','init_ch_schema.sql'):
        raise native.AcceptanceError('unexpected_schema_name')
    path=root/'scripts'/'docker-compose'/'migration-files'/name
    if path.is_symlink() or not path.is_file():raise native.AcceptanceError('openreplay_schema_missing')
    return path.read_text(encoding='utf8')


class OpenReplay(Application):
    id='openreplay';port=8000
    images={'openreplay_postgres':'postgres@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065',
            'openreplay_clickhouse':'clickhouse/clickhouse-server@sha256:0152dd511befe6a2c2ef53e930726179669b08116da78500b37c51c96ff5ee77',
            'openreplay':'public.ecr.aws/p1t3u8a3/chalice@sha256:bfd06b3e47b9d0ffc95b637903c45bfe50eef0933c91758a5c17158013369668'}

    def install(self,**ctx):
        self.bind(**ctx);dbpass=self.secret();chpass=self.secret();self.password=self.secret()
        schemas={k:source_schema(self.n,k) for k in ('init_pg_schema.sql','init_ch_schema.sql')}
        self.report.setdefault('source_checksums',{})['openreplay']={
            'commit':SOURCE_SHA,**{k:hashlib.sha256(v.encode()).hexdigest() for k,v in schemas.items()}}
        self.launch('or-postgres','openreplay_postgres',alias='or-postgres',env={
            'POSTGRES_USER':'postgres','POSTGRES_PASSWORD':dbpass,'POSTGRES_DB':'postgres'})
        pg=self.find('or-postgres')
        self.wait(lambda:self.docker('exec',pg,'pg_isready','-U','postgres','-d','postgres',timeout=10))
        self.docker('exec','-i',pg,'psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1',
                    input_text=schemas['init_pg_schema.sql'],timeout=180)
        self.launch('or-clickhouse','openreplay_clickhouse',alias='or-clickhouse',env={
            'CLICKHOUSE_USER':'default','CLICKHOUSE_PASSWORD':chpass,'CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT':'1'})
        ch=self.find('or-clickhouse')
        self.wait(lambda:self.docker('exec',ch,'clickhouse-client','--password',chpass,'--query','SELECT 1',timeout=10))
        self.docker('exec','-i',ch,'clickhouse-client','--password',chpass,'--multiquery',
                    input_text=schemas['init_ch_schema.sql'],timeout=180)
        # Administrative bootstrap only, avoiding signup's outbound telemetry.
        # The subsequent login uses the actual original password verifier and JWTs.
        sql="""BEGIN;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.users) THEN RAISE EXCEPTION 'bootstrap_requires_empty_users'; END IF; END $$;
INSERT INTO public.tenants(name,opt_out) VALUES ('Native Acceptance',true);
WITH owner AS (INSERT INTO public.users(email,role,name,weekly_report)
 VALUES ('operator@example.com','owner','Native Operator',false) RETURNING user_id)
INSERT INTO public.basic_authentication(user_id,password)
 SELECT user_id,crypt('%s',gen_salt('bf',12)) FROM owner;
COMMIT;""" % self.password
        self.docker('exec','-i',pg,'psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1',input_text=sql,timeout=30)
        env={key:self.secret() for key in ('JWT_SECRET','JWT_REFRESH_SECRET','JWT_SPOT_SECRET',
              'JWT_SPOT_REFRESH_SECRET','JWT_MCP_SECRET','ASSIST_JWT_SECRET','ASSIST_KEY')}
        env.update({'pg_host':'or-postgres','pg_dbname':'postgres','pg_user':'postgres','pg_password':dbpass,'pg_port':'5432',
            'ch_host':'or-clickhouse','ch_user':'default','ch_password':chpass,'ch_port':'9000','ch_port_http':'8123',
            'JWT_ALGORITHM':'HS512','JWT_MCP_ALGORITHM':'HS512','JWT_ISSUER':'OpenReplay',
            'JWT_EXPIRATION':'3600','JWT_REFRESH_EXPIRATION':'7200','JWT_SPOT_EXPIRATION':'3600',
            'JWT_SPOT_REFRESH_EXPIRATION':'7200','ASSIST_JWT_EXPIRATION':'3600',
            'ASSIST_URL':'http://localhost:9001?key=%s','SITE_URL':'http://localhost:8000',
            'EMAIL_HOST':'','EMAIL_FROM':'operator@example.com','S3_HOST':'http://localhost:9000',
            'S3_KEY':self.secret(),'S3_SECRET':self.secret(),'sessions_region':'us-east-1',
            'sessions_bucket':'sessions','sourcemaps_bucket':'sourcemaps','js_cache_bucket':'assets',
            'ASSIST_RECORDS_BUCKET':'assist','IOS_VIDEO_BUCKET':'sessions','root_path':'',
            'PG_MINCONN':'1','PG_MAXCONN':'3','PG_AIO_MINCONN':'1','PG_AIO_MAXCONN':'3',
            'CH_MINCONN':'1','CH_MAXCONN':'2','LOGLEVEL':'WARNING','LISTEN_PORT':'8000','LOCAL_DEV':'false'})
        self.native_env=dict(env)
        self.base=self.launch('openreplay','openreplay',port=8000,env=env)
        self.wait(lambda:self.http.call(self.base+'/signup').get('data',{}).get('tenants') is True,seconds=360)
        self.login();self.http.call(self.base+'/projects',headers=self.headers)
        self.http.denied(self.base+'/projects');self.check('rejects_missing_auth')

    def login(self):
        value=self.http.call(self.base+'/login',data={'email':'operator@example.com','password':self.password})
        token=value.get('jwt')
        if not isinstance(token,str) or not token:raise self.n.AcceptanceError('openreplay_native_login_failed')
        self.n.mask_secret(token);self.headers={'Authorization':'Bearer '+token}

    def exchange(self,identity):
        self.identity=identity
        value=self.http.call(self.base+'/projects',data={'name':identity['route'],'platform':'web'},headers=self.headers)
        self.project_id=value.get('data',{}).get('projectId')
        if type(self.project_id)!=int or self.project_id<1:raise self.n.AcceptanceError('openreplay_project_creation_failed')
        self.wait(self.read);self.check('native_readback')
        self.proof={'project_id':self.project_id,'route_read_back':identity['route'],
                    'scope':'original_project_configuration_api','session_capture_verified':False}
        return identity['route']

    def read(self):
        row=self.http.call(self.base+'/projects/'+str(self.project_id),headers=self.headers).get('data',{})
        return row.get('projectId')==self.project_id and row.get('name')==self.identity['route'] and row.get('platform')=='web'

    def verify(self):
        self.wait(lambda:self.http.call(self.base+'/signup').get('data',{}).get('tenants') is True)
        self.login();self.wait(self.read);self.check('after_restart')
