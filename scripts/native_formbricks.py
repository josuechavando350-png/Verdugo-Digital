"""Native Formbricks survey/response acceptance, not a replacement survey server.

Only temporary organization/workspace/API-key metadata is bootstrapped. Survey
and response records must be created and read using the original management API.
SpiceDB runs the original authorization engine; authorization is never disabled.
"""
import json
import secrets
from native_extra_apps import Application

ADMIN_BOOTSTRAP = r'''
const {prisma} = await import('/home/nextjs/packages/database/dist/index.js');
const {createHash} = await import('node:crypto');
const ids = JSON.parse(process.env.NATIVE_FB_IDS);
const key = process.env.NATIVE_FB_KEY;
try {
  if(await prisma.organization.count() !== 0) throw Error('bootstrap_requires_empty_instance');
  await prisma.$transaction(async p => {
    await p.organization.create({data:{id:ids.org,name:'Verdugo Native Laboratory'}});
    await p.organizationBilling.create({data:{organizationId:ids.org,
      limits:{workspaces:1,monthly:{responses:50}},stripeCustomerId:null,usageCycleAnchor:new Date()}});
    await p.workspace.create({data:{id:ids.workspace,name:'Native Integration',organizationId:ids.org}});
    await p.apiKey.create({data:{id:ids.key,label:'Ephemeral native acceptance',
      hashedKey:createHash('sha256').update(key).digest('hex'),organizationId:ids.org,
      organizationAccess:{accessControl:{read:false,write:false}}}});
    await p.apiKeyWorkspace.create({data:{apiKeyId:ids.key,workspaceId:ids.workspace,permission:'manage'}});
  });
  console.log(JSON.stringify({workspace:ids.workspace,administrative_only:true}));
} finally {await prisma.$disconnect();}
'''

class Formbricks(Application):
    id='formbricks'
    images={'formbricks_postgres':'pgvector/pgvector:pg18',
            'formbricks_redis':'valkey/valkey:8-alpine',
            'formbricks_spicedb':'authzed/spicedb:v1.57.0',
            'formbricks':'ghcr.io/formbricks/formbricks:latest'}

    def install(self,**ctx):
        self.bind(**ctx)
        password=self.secret();redispass=self.secret();authzed=self.secret()
        self.launch('fb-postgres','formbricks_postgres',alias='fb-postgres',env={
            'POSTGRES_USER':'postgres','POSTGRES_PASSWORD':password,'POSTGRES_DB':'formbricks'})
        pg=self.find('fb-postgres')
        self.wait(lambda:self.docker('exec',pg,'pg_isready','-U','postgres','-d','formbricks',timeout=10))
        self.docker('exec',pg,'psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1','-c','CREATE DATABASE spicedb;')
        self.launch('fb-redis','formbricks_redis',alias='fb-redis',env={'REDISCLI_AUTH':redispass},
                    args=('valkey-server','--requirepass',redispass,'--appendonly','yes','--maxmemory-policy','noeviction'))
        self.wait(lambda:self.docker('exec',self.find('fb-redis'),'valkey-cli','ping',timeout=10))
        conn='postgresql://postgres:'+password+'@fb-postgres:5432/spicedb?sslmode=disable'
        self.n.mask_secret(conn)
        spenv={'SPICEDB_DATASTORE_ENGINE':'postgres','SPICEDB_DATASTORE_CONN_URI':conn,
               'SPICEDB_GRPC_PRESHARED_KEY':authzed,'SPICEDB_TELEMETRY_ENDPOINT':'','SPICEDB_LOG_LEVEL':'warn'}
        self.launch('fb-spicedb-migrate','formbricks_spicedb',env=spenv,args=('datastore','migrate','head'))
        def migrated():
            state=json.loads(self.docker('inspect',self.find('fb-spicedb-migrate')))[0]['State']
            if state['Status']=='exited':
                if state['ExitCode']!=0:raise self.n.AcceptanceError('formbricks_authz_migration_failed')
                return True
            return False
        self.wait(migrated)
        self.launch('fb-spicedb','formbricks_spicedb',alias='fb-spicedb',env=spenv,args=('serve',))
        self.wait(lambda:self.docker('exec',self.find('fb-spicedb'),'/usr/local/bin/grpc_health_probe','-addr=localhost:50051',timeout=10))
        authsecret=self.secret();db='postgresql://postgres:'+password+'@fb-postgres:5432/formbricks?schema=public'
        redis='redis://:'+redispass+'@fb-redis:6379';self.n.mask_secret(db);self.n.mask_secret(redis)
        env={'DATABASE_URL':db,'WEBAPP_URL':'http://localhost:3000','BETTER_AUTH_URL':'http://localhost:3000',
             'BETTER_AUTH_SECRET':authsecret,'NEXTAUTH_SECRET':authsecret,'ENCRYPTION_KEY':self.secret(),
             'CRON_SECRET':self.secret(),'REDIS_URL':redis,'AUTHZED_ENABLED':'true',
             'AUTHZED_ENDPOINT':'fb-spicedb:50051','AUTHZED_TOKEN':authzed,'AUTHZED_INSECURE':'true',
             'AUTHZED_SYSTEM_KEY':'formbricks','AUTHZED_CONSISTENCY':'fully_consistent',
             'HUB_API_KEY':self.secret(),'HUB_API_URL':'http://localhost:8080',
             'CUBEJS_API_SECRET':self.secret(),'CUBEJS_API_URL':'http://localhost:4000',
             'EMAIL_VERIFICATION_DISABLED':'1','PASSWORD_RESET_DISABLED':'1','TELEMETRY_DISABLED':'1',
             'NODE_OPTIONS':'--max-old-space-size=1100','LOG_LEVEL':'warn'}
        # Hub/Cube analytics are not exercised by this bounded API profile. No fake
        # service answers these ports, and no outbound workflow is configured.
        self.base=self.launch('formbricks','formbricks',port=3000,env=env)
        self.wait(lambda:self.http.call(self.base+'/health').get('status')=='ok',seconds=480)
        self.api_key=self.secret()
        ids={name:'c'+secrets.token_hex(12) for name in ('org','workspace','key')}
        self.workspace=ids['workspace']
        output=self.docker('exec','-e','NATIVE_FB_IDS='+json.dumps(ids),'-e','NATIVE_FB_KEY='+self.api_key,
                           self.find('formbricks'),'node','--input-type=module','-e',ADMIN_BOOTSTRAP,timeout=90)
        if json.loads(output).get('workspace')!=self.workspace:
            raise self.n.AcceptanceError('formbricks_admin_bootstrap_failed')
        # Official operator CLI writes its canonical schema and derives permissions
        # from the real administrative metadata; no permissive replacement policy.
        result=json.loads(self.docker('exec',self.find('formbricks'),'formbricks-authzed','upgrade','prepare',timeout=180))
        if result.get('status') not in ('prepared','ready'):
            raise self.n.AcceptanceError('formbricks_authzed_not_prepared')
        self.headers={'x-api-key':self.api_key}
        self.http.call(self.base+'/api/v1/management/surveys',headers=self.headers)
        self.http.denied(self.base+'/api/v1/management/surveys');self.check('rejects_missing_auth')

    def exchange(self,identity):
        self.identity=identity;self.question='q'+secrets.token_hex(11)
        survey=self.http.call(self.base+'/api/v1/management/surveys',data={
            'workspaceId':self.workspace,'name':'Native '+identity['event_id'],'type':'link','status':'inProgress',
            'questions':[{'id':self.question,'type':'openText','headline':{'default':'Integration route'},'required':True}],
            'blocks':[]},headers=self.headers,statuses=(200,201))
        self.survey_id=survey.get('data',{}).get('id')
        if not isinstance(self.survey_id,str):raise self.n.AcceptanceError('formbricks_survey_not_created')
        response=self.http.call(self.base+'/api/v1/management/responses',data={
            'workspaceId':self.workspace,'surveyId':self.survey_id,'finished':True,
            'data':{self.question:identity['route']}},headers=self.headers,statuses=(200,201))
        self.response_id=response.get('data',{}).get('id')
        if not isinstance(self.response_id,str):raise self.n.AcceptanceError('formbricks_response_not_created')
        self.wait(self.read);self.check('native_readback')
        self.proof={'survey_id':self.survey_id,'response_id':self.response_id,'route_read_back':identity['route'],
                    'scope':'management_survey_response_api_not_full_analytics'}
        return identity['route']

    def read(self):
        survey=self.http.call(self.base+'/api/v1/management/surveys/'+self.survey_id,headers=self.headers).get('data',{})
        response=self.http.call(self.base+'/api/v1/management/responses/'+self.response_id,headers=self.headers).get('data',{})
        return (survey.get('id')==self.survey_id and survey.get('name')=='Native '+self.identity['event_id']
                and response.get('id')==self.response_id and response.get('surveyId')==self.survey_id
                and response.get('data',{}).get(self.question)==self.identity['route'])

    def verify(self):
        self.wait(lambda:self.http.call(self.base+'/health').get('status')=='ok',seconds=360)
        self.wait(self.read);self.check('after_restart')
