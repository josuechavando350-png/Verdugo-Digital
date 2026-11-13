"""Original PostHog feature-flag API acceptance, with native authentication.

This initial contract verifies persisted configuration, not the distinct Kafka/
ClickHouse event capture pipeline. No flags or events are seeded in databases.
"""
import base64
import json
import secrets
import time
from native_extra_apps import Application

ADMIN_BOOTSTRAP = r'''
import os, json
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','posthog.settings')
django.setup()
from posthog.models import Organization, Team, User
from posthog.accessible_teams import AccessibleTeams
from posthog.personal_api_key_minting import mint_personal_api_key
if Organization.objects.exists():
    raise RuntimeError('bootstrap_requires_empty_organization')
org=Organization.objects.create(name='Verdugo Native Laboratory')
team=Team.objects.create(organization=org,name='Native integration')
user=User.objects.create_and_join(org,'operator@example.com',os.environ['NATIVE_ADMIN_PASSWORD'],'Native Operator')
minted=mint_personal_api_key(user,label='Native integration',
    scopes=['feature_flag:read','feature_flag:write'],teams=AccessibleTeams.all_for(user))
print('NATIVE_BOOTSTRAP='+json.dumps({'team_id':team.pk,'personal_key':minted.value}))
'''

class PostHog(Application):
    id='posthog';port=8000
    images={'posthog_postgres':'postgres@sha256:f377d590e5474681d4d7838635031a2b50647923b7abfa803ce9b5ff35d5c663',
            'posthog_redis':'redis@sha256:7f7d30b7fdd09467bac58198a1f166dd69789d348d4fe859cccb20e0cf287fbe',
            'posthog_clickhouse':'clickhouse/clickhouse-server@sha256:0152dd511befe6a2c2ef53e930726179669b08116da78500b37c51c96ff5ee77',
            'posthog':'posthog/posthog@sha256:cf9c1e9db55ff215edebd8be261e7c44b2e2af06c592539cb0ca484186b63f7f'}

    def install(self,**ctx):
        self.bind(**ctx);dbpass=self.secret();redispass=self.secret();chpass=self.secret();password=self.secret()
        self.launch('ph-postgres','posthog_postgres',alias='ph-postgres',env={
            'POSTGRES_USER':'postgres','POSTGRES_PASSWORD':dbpass,'POSTGRES_DB':'posthog'})
        pg=self.find('ph-postgres')
        self.wait(lambda:self.docker('exec',pg,'pg_isready','-U','postgres','-d','posthog',timeout=10))
        self.launch('ph-redis','posthog_redis',alias='ph-redis',env={'REDISCLI_AUTH':redispass},
                    args=('redis-server','--requirepass',redispass,'--appendonly','yes','--maxmemory-policy','noeviction'))
        self.wait(lambda:self.docker('exec',self.find('ph-redis'),'redis-cli','ping',timeout=10))
        self.launch('ph-clickhouse','posthog_clickhouse',alias='ph-clickhouse',env={
            'CLICKHOUSE_USER':'default','CLICKHOUSE_PASSWORD':chpass,'CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT':'1'})
        self.wait(lambda:self.docker('exec',self.find('ph-clickhouse'),'clickhouse-client',
            '--password',chpass,'--query','SELECT 1',timeout=10))
        db='postgres://postgres:'+dbpass+'@ph-postgres:5432/posthog'
        redis='redis://:'+redispass+'@ph-redis:6379';self.n.mask_secret(db);self.n.mask_secret(redis)
        env={'DATABASE_URL':db,'REDIS_URL':redis,'SECRET_KEY':self.secret(),
            'ENCRYPTION_SALT_KEYS':secrets.token_hex(16),
            'CLICKHOUSE_HOST':'ph-clickhouse','CLICKHOUSE_DATABASE':'default',
            'CLICKHOUSE_USER':'default','CLICKHOUSE_PASSWORD':chpass,
            'CLICKHOUSE_SECURE':'false','CLICKHOUSE_VERIFY':'false',
            'SITE_URL':'http://localhost:8000','DISABLE_SECURE_SSL_REDIRECT':'true',
            'OPT_OUT_CAPTURE':'true','SELF_CAPTURE':'false','OTEL_SDK_DISABLED':'true',
            'NATIVE_ADMIN_PASSWORD':password,'PYTHONUNBUFFERED':'1'}
        self.n.mask_secret(env['ENCRYPTION_SALT_KEYS'])
        # Run the original Django migration and original production WSGI app. No
        # TEST/E2E flag and no patched authentication or replacement feature store.
        command=('sh','-ec','exec 2>&1; python manage.py migrate --noinput && touch /tmp/native-pg-migrated && exec granian --interface wsgi --host 0.0.0.0 --port 8000 --workers 1 posthog.wsgi:application')
        self.base=self.launch('posthog','posthog',port=8000,env=env,args=command)
        deadline=time.monotonic()+1800
        while True:
            container=self.find('posthog')
            state=json.loads(self.docker('inspect',container))[0]['State']
            if state['Status']!='running':
                raise self.n.AcceptanceError('posthog_startup_exited_'+str(state.get('ExitCode')))
            try:
                self.docker('exec',container,'test','-f','/tmp/native-pg-migrated',timeout=10)
                break
            except self.n.AcceptanceError:
                if time.monotonic()>deadline:raise self.n.AcceptanceError('posthog_migration_timeout')
                time.sleep(2)
        output=self.docker('exec',self.find('posthog'),'python','-c',ADMIN_BOOTSTRAP,timeout=180)
        rows=[line.split('NATIVE_BOOTSTRAP=',1)[1] for line in output.splitlines() if line.startswith('NATIVE_BOOTSTRAP=')]
        if len(rows)!=1:raise self.n.AcceptanceError('posthog_admin_bootstrap_invalid')
        admin=json.loads(rows[0]);self.team=admin.get('team_id');key=admin.get('personal_key')
        if type(self.team)!=int or self.team<1 or not isinstance(key,str) or not key:
            raise self.n.AcceptanceError('posthog_admin_identity_invalid')
        self.n.mask_secret(key);self.headers={'Authorization':'Bearer '+key}
        self.path='/api/projects/'+str(self.team)+'/feature_flags/'
        self.wait(lambda:self.http.call(self.base+self.path,headers=self.headers) is not None,seconds=240)
        self.http.denied(self.base+self.path);self.check('rejects_missing_auth')

    def exchange(self,identity):
        self.identity=identity;self.flag_key='native-'+identity['event_id']
        row=self.http.call(self.base+self.path,data={
            'key':self.flag_key,'name':identity['route'],'active':True,
            'filters':{'groups':[{'properties':[],'rollout_percentage':100}]}},
            headers=self.headers,statuses=(201,))
        self.flag_id=row.get('id')
        if type(self.flag_id)!=int or self.flag_id<1:
            raise self.n.AcceptanceError('posthog_feature_flag_not_created')
        self.wait(self.read);self.check('native_readback')
        self.proof={'feature_flag_id':self.flag_id,'team_id':self.team,'route_read_back':identity['route'],
                    'scope':'original_feature_flag_configuration_api','event_capture_verified':False}
        return identity['route']

    def read(self):
        row=self.http.call(self.base+self.path+str(self.flag_id)+'/',headers=self.headers)
        return (row.get('id')==self.flag_id and row.get('key')==self.flag_key
                and row.get('name')==self.identity['route'] and row.get('active') is True)

    def verify(self):
        self.wait(self.read,seconds=300);self.check('after_restart')
