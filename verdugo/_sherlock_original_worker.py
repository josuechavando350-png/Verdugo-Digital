"""Fixed first-party bridge to original Sherlock; only the owned loopback server."""
import json,sys,contextlib,io,socket
from urllib.parse import urlsplit
p=json.loads(sys.stdin.buffer.read(65537));base=p['base'];target=urlsplit(base)
if target.scheme!='http' or target.hostname!='127.0.0.1' or target.path or not 1024<=target.port<=65535:raise ValueError('Owned origin required')
def guard(event,args):
 if event=='socket.connect' and (len(args[1])<2 or args[1][0]!='127.0.0.1' or args[1][1]!=target.port):raise PermissionError('Only owned loopback socket allowed')
 if event=='socket.getaddrinfo' and (args[0]!='127.0.0.1' or args[1]!=target.port):raise PermissionError('Only owned numeric address allowed')
 if event in ('socket.bind','subprocess.Popen','os.system'):raise PermissionError('No servers or child commands')
sys.addaudithook(guard)
from sherlock_project.sherlock import sherlock
from sherlock_project.notify import QueryNotify
rows={r['id']:{'urlMain':base,'url':base+'/case/'+str(r['index'])+'/{}','errorType':r['mode'],'errorMsg':r['marker'],'headers':{'Authorization':'Bearer '+p['token']}} for r in p['responses']}
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):out=sherlock('supplied-brand',rows,QueryNotify(),timeout=5)
result=[]
for row in p['responses']:
 record=out[row['id']];status=str(record['status'].status);http_status=record['http_status']
 if status not in ('Claimed','Available','Unknown','Illegal','WAF') or type(http_status) is not int:raise ValueError('Original classification changed')
 result.append({'id':row['id'],'classification':status,'http_status':http_status})
print(json.dumps({'results':result,'live_accounts_verified':False,'identity_inferred':False,'scope':'Original Sherlock classification over supplied responses served privately; fixed synthetic brand, no public account search'}))
