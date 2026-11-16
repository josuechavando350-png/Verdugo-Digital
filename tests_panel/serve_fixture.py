"""Synthetic E2E fixture only. Clock override is never part of the production API."""
from datetime import date
import json
import os
from pathlib import Path
import sys
import uvicorn
from verdugo import ads,subscriptions
from verdugo.engine import Engine
from verdugo.panel_server import create_app

role=sys.argv[1];port=int(sys.argv[2]);root=Path(os.environ['PANEL_TEST_DIR']);root.mkdir(mode=0o700,parents=True,exist_ok=True);root.chmod(0o700);os.umask(0o077)
clock=root/'clock';clock.write_text('2026-11-16')
subscriptions.today=lambda:date.fromisoformat(clock.read_text().strip())
config=root/'config.json';config.write_text(json.dumps({'tenants':{'cliente-demo':{'services':{}},'nexus':{'services':{}}}}))
state=root/'state.sqlite'
if role=='operator':
    for old in root.glob('state.sqlite*'):old.unlink()
    e=Engine(str(state),json.loads(config.read_text()),'cliente-demo')
    try:
        csv=root/'synthetic.csv';csv.write_text('Day,Campaign,Cost,Clicks,Impressions,Conversions\n'+''.join(f'2026-11-{d:02d},cliente-demo,{200 if d==12 else 35+d*3},{10+d},{200+d*20},{2+d%4}\n' for d in range(1,16)))
        ads.import_file(e,'@'+str(csv),'google',True,dataset='demo')
    finally:e.close()
app=create_app(config,str(state),'synthetic-e2e-token-with-no-real-access',role=role,host='127.0.0.1:'+str(port))
uvicorn.run(app,host='127.0.0.1',port=port,access_log=False,log_level='warning',proxy_headers=False)
