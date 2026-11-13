"""Native Twenty and erxes adapters. Contacts traverse original authenticated APIs."""
import json
from native_extra_apps import Application, NativeSession


def graphql(app, query, variables=None, *, token=None, client=None, path='/graphql'):
    headers={'Authorization':'Bearer '+token} if token else {}
    value=(client or app.http).call(app.base+path,data={'query':query,'variables':variables or {}},headers=headers)
    if not isinstance(value,dict) or value.get('errors') or not isinstance(value.get('data'),dict):
        # Preserve only error codes, never credentials or application error bodies.
        codes=[]
        if isinstance(value,dict):
            for e in value.get('errors',[])[:3]:
                code=e.get('extensions',{}).get('code','graphql_error')
                if isinstance(code,str) and code.replace('_','').isalnum():codes.append(code[:50])
        raise app.n.AcceptanceError(app.id+'_graphql_'+('_'.join(codes) or 'invalid'))
    return value['data']


class Twenty(Application):
    id='twenty'
    images={'twenty_postgres':'postgres:16-alpine','extra_redis':'redis:7-alpine','twenty':'twentycrm/twenty:latest'}

    def install(self,**ctx):
        self.bind(**ctx);password=self.secret();redispass=self.secret()
        self.password='Vd!'+self.secret();self.n.mask_secret(self.password)
        self.launch('twenty-postgres','twenty_postgres',alias='twenty-postgres',env={
            'POSTGRES_USER':'postgres','POSTGRES_PASSWORD':password,'POSTGRES_DB':'twenty'})
        pg=self.find('twenty-postgres')
        self.wait(lambda:self.docker('exec',pg,'pg_isready','-U','postgres','-d','twenty',timeout=10))
        self.launch('twenty-redis','extra_redis',alias='twenty-redis',env={'REDISCLI_AUTH':redispass},
                    args=('redis-server','--requirepass',redispass,'--appendonly','yes','--maxmemory-policy','noeviction'))
        redis=self.find('twenty-redis')
        self.wait(lambda:self.docker('exec',redis,'redis-cli','ping',timeout=10))
        self.env={'NODE_PORT':'3000','PG_DATABASE_URL':'postgresql://postgres:'+password+'@twenty-postgres:5432/twenty',
            'REDIS_URL':'redis://:'+redispass+'@twenty-redis:6379','SERVER_URL':'http://localhost:3000',
            'APP_SECRET':self.secret(),'ENCRYPTION_KEY':self.secret(),'STORAGE_TYPE':'local','EMAIL_DRIVER':'logger',
            'IS_EMAIL_VERIFICATION_REQUIRED':'false','DISABLE_CRON_JOBS_REGISTRATION':'true',
            'IS_BILLING_ENABLED':'false','IS_MULTIWORKSPACE_ENABLED':'false','NODE_OPTIONS':'--max-old-space-size=1100'}
        self.n.mask_secret(self.env['PG_DATABASE_URL']);self.n.mask_secret(self.env['REDIS_URL'])
        self.base=self.launch('twenty','twenty',port=3000,env=self.env)
        self.wait(lambda:self.http.call(self.base+'/healthz') is not None,seconds=480)
        self.launch('twenty-worker','twenty',env={**self.env,'DISABLE_DB_MIGRATIONS':'true'},args=('yarn','worker:prod'))
        signup=graphql(self,'mutation($e:String!,$p:String!){signUp(email:$e,password:$p){tokens{accessOrWorkspaceAgnosticToken{token}}}}',
                       {'e':'operator@example.invalid','p':self.password},path='/metadata')['signUp']
        agnostic=signup['tokens']['accessOrWorkspaceAgnosticToken']['token'];self.n.mask_secret(agnostic)
        created=graphql(self,'mutation($i:SignUpInNewWorkspaceInput){signUpInNewWorkspace(input:$i){loginToken{token}workspace{id workspaceUrls{customUrl subdomainUrl}}}}',
                        {'i':{'displayName':'Native Acceptance'}},token=agnostic,path='/metadata')['signUpInNewWorkspace']
        self.workspace=created['workspace']['id'];login=created['loginToken']['token'];self.n.mask_secret(login)
        origin=created['workspace'].get('workspaceUrls',{}).get('customUrl') or created['workspace'].get('workspaceUrls',{}).get('subdomainUrl') or self.env['SERVER_URL']
        auth=graphql(self,'mutation($t:String!,$o:String!){getAuthTokensFromLoginToken(loginToken:$t,origin:$o){tokens{accessOrWorkspaceAgnosticToken{token}}}}',
                     {'t':login,'o':origin},path='/metadata')['getAuthTokensFromLoginToken']
        self.token=auth['tokens']['accessOrWorkspaceAgnosticToken']['token'];self.n.mask_secret(self.token)
        self.headers={'Authorization':'Bearer '+self.token}
        self.wait(lambda:self.http.call(self.base+'/rest/people?limit=1',headers=self.headers) is not None,seconds=300)
        self.http.denied(self.base+'/rest/people?limit=1');self.check('rejects_missing_auth')

    def exchange(self,identity):
        self.identity=identity
        value=self.http.call(self.base+'/rest/people',data={'id':identity['event_id'],
            'name':{'firstName':'Native','lastName':'Acceptance'},'jobTitle':identity['route'],
            'emails':{'primaryEmail':'acceptance-'+identity['event_id']+'@example.invalid','additionalEmails':[]}},
            headers=self.headers,statuses=(201,))
        person=value.get('data',{}).get('createPerson',{})
        if person.get('id')!=identity['event_id']:raise self.n.AcceptanceError('twenty_person_creation_mismatch')
        self.wait(self.read);self.check('native_readback')
        self.proof={'person_id':identity['event_id'],'route_read_back':identity['route']}
        return identity['route']

    def read(self):
        row=self.http.call(self.base+'/rest/people/'+self.identity['event_id'],headers=self.headers).get('data',{}).get('person',{})
        return row.get('id')==self.identity['event_id'] and row.get('jobTitle')==self.identity['route']

    def restart(self):
        self.docker('stop',self.find('twenty-worker'),timeout=60)
        super().restart();self.docker('start',self.find('twenty-worker'))

    def verify(self):
        self.wait(lambda:self.http.call(self.base+'/healthz') is not None,seconds=360)
        self.wait(self.read);self.check('after_restart')


class Erxes(Application):
    id='erxes';port=4000
    images={'erxes_mongo':'mongo:7','extra_redis':'redis:7-alpine',
        'erxes_core':'erxes/erxes-next-core-api:3.4.21','erxes_gateway':'erxes/erxes-next-gateway:3.4.21',
        'erxes_logs':'erxes/erxes-next-logs:3.4.21','erxes_automations':'erxes/erxes-next-automations:3.4.21'}

    def install(self,**ctx):
        self.bind(**ctx);password=self.secret();self.password='Vd!'+self.secret();self.n.mask_secret(self.password)
        self.launch('erxes-mongo','erxes_mongo',alias='erxes-mongo',args=('mongod','--replSet','rs0','--bind_ip_all'))
        mongo=self.find('erxes-mongo')
        init="try{rs.status()}catch(e){rs.initiate({_id:'rs0',members:[{_id:0,host:'erxes-mongo:27017'}]})};if(!db.hello().isWritablePrimary)quit(1);print('ready')"
        self.wait(lambda:self.docker('exec',mongo,'mongosh','--quiet','--eval',init,timeout=10))
        self.launch('erxes-redis','extra_redis',alias='erxes-redis',env={'REDISCLI_AUTH':password},
                    args=('redis-server','--requirepass',password,'--appendonly','yes'))
        redis=self.find('erxes-redis');self.wait(lambda:self.docker('exec',redis,'redis-cli','ping',timeout=10))
        self.env={'NODE_ENV':'production','VERSION':'os','RELEASE_VERSION':'3.4.21',
            'MONGO_URL':'mongodb://erxes-mongo:27017/erxes?replicaSet=rs0',
            'REDIS_HOST':'erxes-redis','REDIS_PORT':'6379','REDIS_PASSWORD':password,
            'JWT_TOKEN_SECRET':self.secret(),'DOMAIN':'http://localhost:4000','ENABLED_PLUGINS':'',
            'ALLOWED_DOMAINS':'http://localhost:4000','NODE_OPTIONS':'--max-old-space-size=1100'}
        core=self.launch('erxes-core','erxes_core',port=3300,env=self.env)
        self.wait(lambda:self.http.call(core+'/health',raw=True)=='ok',seconds=360)
        self.launch('erxes-logs','erxes_logs',env=self.env)
        self.launch('erxes-automations','erxes_automations',env=self.env)
        self.base=self.launch('erxes','erxes_gateway',port=4000,env=self.env)
        self.wait(lambda:self.http.call(self.base+'/health',raw=True)=='ok',seconds=360)
        self.wait(lambda:graphql(self,'query{__typename}').get('__typename')=='Query',seconds=300)
        created=graphql(self,'mutation($e:String!,$p:String!){usersCreateOwner(email:$e,password:$p,firstName:"Native",lastName:"Acceptance",subscribeEmail:false)}',
                        {'e':'operator@example.invalid','p':self.password})
        if created.get('usersCreateOwner')!='success':raise self.n.AcceptanceError('erxes_owner_creation_failed')
        self.login()

    def login(self):
        result=graphql(self,'mutation($e:String!,$p:String!){login(email:$e,password:$p)}',
                       {'e':'operator@example.invalid','p':self.password})
        if result.get('login')!='loggedIn':raise self.n.AcceptanceError('erxes_login_failed')

    def exchange(self,identity):
        self.identity=identity
        row=graphql(self,'mutation($code:String!,$route:String!,$email:String!){customersAdd(state:"customer",firstName:"Native",lastName:"Acceptance",primaryEmail:$email,code:$code,description:$route){_id code description}}',
            {'code':identity['event_id'],'route':identity['route'],'email':'acceptance-'+identity['event_id']+'@example.invalid'}).get('customersAdd')
        if not isinstance(row,dict) or not isinstance(row.get('_id'),str):raise self.n.AcceptanceError('erxes_contact_creation_failed')
        self.contact_id=row['_id'];self.wait(self.read)
        # Verify a real existing contact cannot be read without the native session.
        try:graphql(self,'query($id:String!){customerDetail(_id:$id){_id code description}}',
                    {'id':self.contact_id},client=NativeSession(self.n))
        except self.n.AcceptanceError as e:
            if str(e) not in ('erxes_graphql_UNAUTHORIZED','erxes_graphql_UNAUTHENTICATED','extra_http_status_401','extra_http_status_403'):raise
        else:raise self.n.AcceptanceError('erxes_missing_auth_accepted')
        self.check('rejects_missing_auth');self.check('native_readback')
        self.proof={'customer_id':self.contact_id,'canonical_event_id':identity['event_id'],'route_read_back':identity['route']}
        return identity['route']

    def read(self):
        row=graphql(self,'query($id:String!){customerDetail(_id:$id){_id code description}}',{'id':self.contact_id}).get('customerDetail')
        return isinstance(row,dict) and row.get('_id')==self.contact_id and row.get('code')==self.identity['event_id'] and row.get('description')==self.identity['route']

    def restart(self):
        self.docker('stop',self.find('erxes'),timeout=60)
        self.docker('restart',self.find('erxes-core'),timeout=90)
        self.docker('start',self.find('erxes'))
        self.base=self.refresh('erxes',4000);self.http=NativeSession(self.n)

    def verify(self):
        self.wait(lambda:graphql(self,'query{__typename}').get('__typename')=='Query',seconds=360)
        self.login();self.wait(self.read);self.check('after_restart')
