#!/usr/bin/env bash
# No subscriptions, production secrets, marketing sends, or mock provider servers.
set -euo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
[[ "${VERDUGO_LAB_CONFIRM:-}" == 'synthetic-only' ]] || { echo 'Set VERDUGO_LAB_CONFIRM=synthetic-only to authorize the isolated test.' >&2; exit 2; }
command -v docker >/dev/null
command -v python3 >/dev/null
docker compose version
export COMPOSE_PROJECT_NAME="verdugo-originals-${GITHUB_RUN_ID:-local}"
mkdir -p .lab-private evidence/originals
chmod 700 .lab-private
# Refuse reuse: fixture accounts and volumes belong to one acceptance attempt.
[[ ! -e .lab-private/environment ]] || { echo 'A laboratory configuration already exists; refuse to overwrite.' >&2; exit 2; }
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
    subprocess.run(['docker','pull',ref],check=True)
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
  "${DC[@]}" ps -a --format json > evidence/originals/containers.json 2>/dev/null || true
  "${DC[@]}" logs --no-color --tail 100 > .lab-private/service-logs.txt 2>&1 || true
  if [[ "$code" != 0 ]]; then
    python3 - <<'PY'
import os
from pathlib import Path
s=Path('.lab-private/service-logs.txt').read_text(errors='replace')
for k,v in os.environ.items():
    if k.startswith('LAB_') and len(v)>5:s=s.replace(v,'[REDACTED]')
print(s[-18000:])
PY
  fi
  "${DC[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
  exit "$code"
}
trap cleanup EXIT
"${DC[@]}" up -d
python3 - <<'PY'
import time,urllib.request,urllib.error
for url in ['http://127.0.0.1:18080','http://127.0.0.1:13100/healthcheck']:
    for _ in range(90):
        try:
            with urllib.request.urlopen(url,timeout=5) as r:
                if r.status==200:break
        except (OSError,urllib.error.URLError):pass
        time.sleep(5)
    else:raise RuntimeError('Original service did not become ready: '+url)
    print('Original endpoint ready:',url)
PY
"${DC[@]}" exec -T --user www-data mautic sh -c 'cd /var/www/html && php bin/console mautic:install http://localhost:18080 --admin_email=operator@example.invalid --admin_username=verdugo_lab --admin_password="$LAB_ADMIN_PASSWORD" --admin_firstname=Verdugo --admin_lastname=Laboratory --no-interaction'
python3 scripts/originals-acceptance.py
