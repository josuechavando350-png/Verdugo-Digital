#!/usr/bin/env bash
# Original software only. Ephemeral acceptance, never a production deployment.
set -euo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
[[ "${VERDUGO_LAB_CONFIRM:-}" == 'synthetic-only' ]] || { echo 'Set VERDUGO_LAB_CONFIRM=synthetic-only.' >&2; exit 2; }
command -v docker >/dev/null
command -v python3 >/dev/null
docker compose version
export COMPOSE_PROJECT_NAME="verdugo-originals-${GITHUB_RUN_ID:-local}"
mkdir -p .lab-private evidence/originals
chmod 700 .lab-private
[[ ! -e .lab-private/environment ]] || { echo 'Refuse to overwrite an existing laboratory.' >&2; exit 2; }
python3 - <<'PY'
import secrets
from pathlib import Path
p=Path('.lab-private/environment')
names=['LAB_DB_ROOT_PASSWORD','LAB_DB_PASSWORD','LAB_MONGO_PASSWORD','LAB_JWT_SECRET','LAB_ENCRYPTION_KEY','LAB_ADMIN_PASSWORD']
values={k:secrets.token_hex(32) for k in names}
values['LAB_ADMIN_PASSWORD']='VdA1_'+values['LAB_ADMIN_PASSWORD']
p.write_text(''.join(f'export {k}={v}\n' for k,v in values.items()))
p.chmod(0o600)
for v in values.values(): print('::add-mask::'+v)
PY
source .lab-private/environment
python3 - <<'PY'
import json, subprocess
from pathlib import Path
refs={'MYSQL_IMAGE':'mysql:8.4','MONGO_IMAGE':'mongo:7.0','MAUTIC_IMAGE':'mautic/mautic:latest','GROWTHBOOK_IMAGE':'growthbook/growthbook:5.2.0'}
resolved={}
for key,ref in refs.items():
    print('Resolving official image:',ref,flush=True)
    subprocess.run(['docker','pull',ref],check=True,timeout=600)
    info=json.loads(subprocess.check_output(['docker','image','inspect',ref]))[0]
    digests=info.get('RepoDigests',[])
    if not digests: raise RuntimeError('No registry digest for '+ref)
    digest=digests[0]
    resolved[key]={'requested_tag':ref,'resolved_image':digest,'image_id':info['Id']}
    with Path('.lab-private/images').open('a') as f:f.write(f'export {key}={digest}\n')
    Path('evidence/originals/images.json').write_text(json.dumps(resolved,indent=2)+'\n')
PY
source .lab-private/images
DC=(docker compose -f deploy/originals/compose.yml)
cleanup() {
  code=$?
  trap - EXIT
  "${DC[@]}" ps -a --format json > .lab-private/containers.json 2>/dev/null || true
  "${DC[@]}" logs --no-color --tail 80 > .lab-private/service-logs.txt 2>&1 || true
  if [[ "$code" != 0 ]]; then
    python3 - <<'PY'
import os
from pathlib import Path
s=Path('.lab-private/service-logs.txt').read_text(errors='replace')
for k,v in os.environ.items():
    if k.startswith('LAB_') and len(v)>5:s=s.replace(v,'[REDACTED]')
print(s[-24000:])
PY
  fi
  "${DC[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
  exit "$code"
}
trap cleanup EXIT
"${DC[@]}" config --quiet
"${DC[@]}" up -d
# Wait for the upstream entrypoint to create its real config before installing.
for i in $(seq 1 60); do
  if "${DC[@]}" exec -T mautic test -f /var/www/html/config/local.php; then break; fi
  [[ "$i" != 60 ]] || { echo 'Mautic entrypoint never initialized.' >&2; exit 1; }
  sleep 2
done
"${DC[@]}" exec -T --user www-data mautic sh -c 'cd /var/www/html && php bin/console mautic:install http://localhost:18080 --admin_email=operator@example.invalid --admin_username=verdugo_lab --admin_password="$LAB_ADMIN_PASSWORD" --admin_firstname=Verdugo --admin_lastname=Laboratory --no-interaction'
# Explicit original Mautic config; its Docker template only supplies DB fields.
"${DC[@]}" exec -T --user www-data mautic php -r '$f="/var/www/html/config/local.php"; include $f; $parameters["api_enabled"]=true; $parameters["api_enable_basic_auth"]=true; $parameters["mailer_dsn"]="null://null"; file_put_contents($f,"<?php\n\$parameters = ".var_export($parameters,true).";\n");'
"${DC[@]}" exec -T --user www-data mautic sh -c 'cd /var/www/html && php bin/console cache:clear --env=prod --no-interaction'
# Internal-only networks do not publish host ports. Discover only this run's IPs.
python3 - <<'PYCODE'
import ipaddress, json, os, subprocess
from pathlib import Path
project=os.environ['COMPOSE_PROJECT_NAME']
network=project+'_lab'
for service,var,port in [('mautic','LAB_MAUTIC_BASE',80),('growthbook','LAB_GROWTHBOOK_BASE',3100)]:
    cid=subprocess.check_output(['docker','compose','-f','deploy/originals/compose.yml','ps','-q',service],text=True).strip()
    info=json.loads(subprocess.check_output(['docker','inspect',cid]))[0]
    nets=info['NetworkSettings']['Networks']
    if set(nets)!={network}:raise RuntimeError('Unexpected laboratory network')
    address=nets[network]['IPAddress']
    if not ipaddress.ip_address(address).is_private:raise RuntimeError('Non-private container')
    with Path('.lab-private/origins').open('a') as f:f.write(f'export {var}=http://{address}:{port}\n')
PYCODE
source .lab-private/origins
wait_originals() {
python3 - <<'PYCODE'
import base64,os,time,urllib.request,urllib.error
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
auth='Basic '+base64.b64encode(('verdugo_lab:'+os.environ['LAB_ADMIN_PASSWORD']).encode()).decode()
for url,headers in [(os.environ['LAB_MAUTIC_BASE']+'/api/contacts?limit=1',{'Authorization':auth}),(os.environ['LAB_GROWTHBOOK_BASE']+'/healthcheck',{})]:
    end=time.monotonic()+120
    last=''
    while time.monotonic()<end:
        try:
            with opener.open(urllib.request.Request(url,headers=headers),timeout=3) as r:
                if r.status==200:break
        except (OSError,urllib.error.URLError) as e:last=type(e).__name__
        time.sleep(2)
    else:raise RuntimeError('Original service not ready: '+url+' '+last)
    print('Original API ready:',url,flush=True)
PYCODE
}
wait_originals
python3 scripts/originals-acceptance.py
# Stop/restart every application and DB, keeping named volumes. No state reseeding.
"${DC[@]}" stop
"${DC[@]}" up -d
wait_originals
python3 scripts/originals-acceptance.py --after-restart
