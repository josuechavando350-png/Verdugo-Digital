"""Genuine OpenReplay collector -> stream -> DB/sink -> authenticated replay API.

A synthetic protocol client sends a tiny DOM plus a custom event. No session,
event, metadata or replay file is injected into the databases or filesystem.
Browser rendering and S3 archival are distinct scopes and are not inferred.
"""
import hashlib
import json
import time
from pathlib import Path
from native_extra_apps import NativeSession
from native_openreplay import OpenReplay


def uint(value):
    if type(value) is not int or value<0 or value>=2**64:raise ValueError('invalid_protocol_uint')
    result=bytearray()
    while value>=128:result.append((value&127)|128);value>>=7
    result.append(value);return bytes(result)

def text(value):
    encoded=value.encode('utf8')
    if len(encoded)>4096:raise ValueError('protocol_text_too_large')
    return uint(len(encoded))+encoded

def frame(kind,payload=b''):
    if not 0<=kind<128 or len(payload)>65535:raise ValueError('invalid_protocol_frame')
    return bytes([kind])+len(payload).to_bytes(3,'little')+payload

def synthetic_batch(timestamp,identity):
    """Original messages.go/primitives.go version-1 full-batch encoding."""
    location='https://example.com/verdugo-native'
    meta=bytes([81])+uint(1)+uint(0)+uint(0)+uint(timestamp*2)+text(location)
    return meta+b''.join([
        frame(0,uint(timestamp)),
        frame(122,text(location)+text('')+uint(timestamp)+text('Verdugo native capture')),
        frame(5,uint(1024)+uint(768)),
        frame(7),
        frame(8,uint(1)+uint(0)+uint(0)+text('html')+b'\x00'),
        frame(8,uint(2)+uint(1)+uint(0)+text('body')+b'\x00'),
        frame(9,uint(3)+uint(2)+uint(0)),
        frame(14,uint(3)+text(identity['route'])),
        frame(28,text(identity['subject'])),
        frame(30,text('verdugo_route')+text(identity['route'])),
        frame(27,text(identity['event_name'])+text(json.dumps({'route':identity['route'],'event_id':identity['event_id']},separators=(',',':')))),
    ])


class OpenReplayCapture(OpenReplay):
    images={**OpenReplay.images,
        'or_redis':'redis@sha256:7f7d30b7fdd09467bac58198a1f166dd69789d348d4fe859cccb20e0cf287fbe',
        'or_http':'public.ecr.aws/p1t3u8a3/http:v1.28.0',
        'or_db':'public.ecr.aws/p1t3u8a3/db:v1.28.0',
        'or_sink':'public.ecr.aws/p1t3u8a3/sink:v1.28.0',
        'or_api':'public.ecr.aws/p1t3u8a3/api:v1.28.0'}

    def install(self,**ctx):
        super().install(**ctx)
        redispass=self.secret()
        self.launch('or-redis','or_redis',alias='or-redis',env={'REDISCLI_AUTH':redispass},
                    args=('redis-server','--requirepass',redispass,'--appendonly','yes','--maxmemory-policy','noeviction'))
        self.wait(lambda:self.docker('exec',self.find('or-redis'),'redis-cli','ping',timeout=10))
        directory=self.temp/'openreplay-capture'
        directory.mkdir(mode=0o777);directory.chmod(0o777)
        # The writable child contains only synthetic replay bytes. Its parent is
        # private 0700 and the harness rejects every mount outside that parent.
        pg='postgres://postgres:'+self.native_env['pg_password']+'@or-postgres:5432/postgres?sslmode=disable'
        redis='redis://:'+redispass+'@or-redis:6379';self.n.mask_secret(pg);self.n.mask_secret(redis)
        self.capture_env={
            'POSTGRES_STRING':pg,'REDIS_STRING':redis,'REDIS_CACHE_ENABLED':'false',
            'CLICKHOUSE_STRING':'or-clickhouse:9000/default','CLICKHOUSE_HTTP_STRING':'or-clickhouse:8123/default',
            'CLICKHOUSE_USERNAME':'default','CLICKHOUSE_PASSWORD':self.native_env['ch_password'],
            'CH_USERNAME':'default','CH_PASSWORD':self.native_env['ch_password'],
            'CH_MAX_OPEN_CONNS':'3','CH_MAX_IDLE_CONNS':'2','CH_SEND_WORKERS':'1','COMMIT_BATCH_TIMEOUT':'1s',
            'JWT_SECRET':self.native_env['JWT_SECRET'],'JWT_SPOT_SECRET':self.native_env['JWT_SPOT_SECRET'],
            'JWT_MCP_SECRET':self.native_env['JWT_MCP_SECRET'],'JWT_MCP_ALGORITHM':'HS512',
            'JWT_ISSUER':'OpenReplay','TOKEN_SECRET':self.secret(),'JWT_EXPIRATION':'3600s',
            'AWS_ACCESS_KEY_ID':self.native_env['S3_KEY'],'AWS_SECRET_ACCESS_KEY':self.native_env['S3_SECRET'],
            'AWS_ENDPOINT':'http://127.0.0.1:9','AWS_REGION':'us-east-1','BUCKET_NAME':'mobs',
            'FS_DIR':'/mnt/efs','FS_ULIMIT':'100','SYNC_WORKERS':'2','SYNC_INTERVAL':'1s',
            'CACHE_ASSETS':'false','ASSETS_ORIGIN':'http://127.0.0.1:9','RECORD_CANVAS':'false',
            'ASSIST_URL':'http://127.0.0.1:9/assist/%s','ASSIST_REQUEST_TIMEOUT':'1s',
            'GOMAXPROCS':'2','GOMEMLIMIT':'512MiB','HTTP_PORT':'8080','LOGLEVEL':'warn'}
        self.capture_names=['or-db','or-sink','or-api','or-http']
        for name in self.capture_names:
            url=self.launch(name,name.replace('-','_'),port=8080 if name in ('or-api','or-http') else 8888,
                            env=self.capture_env,writable_dirs=[(str(directory),'/mnt/efs')])
            health=self.refresh(name,8888)
            self.wait(lambda u=health:self.http.call(u+'/health').get('status')=='pass',seconds=240)
            if name=='or-api':self.replay_api=url
            if name=='or-http':self.collector=url

    def exchange(self,identity):
        super().exchange(identity)
        project=self.http.call(self.base+'/projects/'+str(self.project_id),headers=self.headers)['data']
        project_key=project.get('projectKey')
        if not isinstance(project_key,str) or not project_key:raise self.n.AcceptanceError('openreplay_project_key_missing')
        self.n.mask_secret(project_key)
        self.http.call(self.base+'/'+str(self.project_id)+'/metadata',data={'key':'verdugo_route'},headers=self.headers)
        timestamp=int(time.time()*1000)
        started=self.http.call(self.collector+'/v1/web/start',data={
            'projectKey':project_key,'trackerVersion':'16.1.0','timestamp':timestamp,'timezone':'UTC',
            'userID':identity['subject'],'width':1024,'height':768,'reset':True,'doNotRecord':False},
            headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'})
        self.session_id=started.get('sessionID');token=started.get('token')
        if not isinstance(self.session_id,str) or not self.session_id.isdigit() or not isinstance(token,str):
            raise self.n.AcceptanceError('openreplay_collector_start_failed')
        if str(started.get('projectID'))!=str(self.project_id):raise self.n.AcceptanceError('openreplay_collector_project_mismatch')
        self.n.mask_secret(token)
        payload=synthetic_batch(timestamp,identity)
        self.http.call(self.collector+'/v1/web/i',body_bytes=payload,headers={'Authorization':'Bearer '+token},raw=True)
        self.http.denied(self.replay_api+f'/{self.project_id}/sessions/{self.session_id}/events')
        self.wait(self.read_capture,seconds=240)
        self.proof.update(scope='original_collector_db_sink_replay_api',session_id=self.session_id,
            session_capture_verified=True,recorded_dom_readback_verified=True,
            synthetic_protocol_client=True,browser_render_verified=False,object_storage_archive_verified=False,
            protocol_batch_sha256=hashlib.sha256(payload).hexdigest())
        self.check('collector_session_and_event_readback');self.check('native_dom_file_readback')
        return identity['route']

    def read_capture(self):
        prefix=self.replay_api+f'/{self.project_id}/sessions/{self.session_id}'
        replay=self.http.call(prefix+'/replay',headers=self.headers).get('data',{})
        if (str(replay.get('sessionId'))!=self.session_id or replay.get('projectId')!=self.project_id
                or replay.get('userId')!=self.identity['subject']
                or replay.get('metadata',{}).get('verdugo_route')!=self.identity['route']):return False
        data=self.http.call(prefix+'/events',headers=self.headers).get('data',{})
        matches=[e for e in data.get('userEvents',[]) if e.get('name')==self.identity['event_name']
                 and e.get('properties',{}).get('route')==self.identity['route']
                 and e.get('properties',{}).get('event_id')==self.identity['event_id']]
        if len(matches)!=1:return False
        dom=self.http.call(self.replay_api+f'/{self.project_id}/unprocessed/{self.session_id}/dom.mob',
                           headers=self.headers,response_bytes=True)
        if not dom.startswith(b'\xff'*7) or self.identity['route'].encode() not in dom:return False
        self.dom_hash=hashlib.sha256(dom).hexdigest()
        return True

    def restart(self):
        self.docker('stop',self.find('or-http'),self.find('or-api'),self.find('or-db'),self.find('or-sink'),timeout=120)
        self.docker('restart',self.find('or-redis'),timeout=60)
        self.wait(lambda:self.docker('exec',self.find('or-redis'),'redis-cli','ping',timeout=10))
        self.docker('start',*[self.find(name) for name in self.capture_names])
        super().restart()

    def verify(self):
        super().verify()
        for name in self.capture_names:
            health=self.refresh(name,8888)
            self.wait(lambda u=health:self.http.call(u+'/health').get('status')=='pass',seconds=240)
        self.replay_api=self.refresh('or-api',8080);self.collector=self.refresh('or-http',8080)
        before=self.dom_hash
        self.wait(self.read_capture,seconds=240)
        if self.dom_hash!=before:raise self.n.AcceptanceError('openreplay_dom_changed_on_restart')
        self.proof['dom_sha256']=self.dom_hash
        self.check('capture_and_dom_after_restart')
