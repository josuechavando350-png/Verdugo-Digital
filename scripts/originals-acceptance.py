"""Authentic Docker applications only; never a loopback fixture pretending to be a provider."""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_MAUTIC='http://127.0.0.1:18080'
BASE_GB='http://127.0.0.1:13100'
PASSWORD=os.environ['LAB_ADMIN_PASSWORD']
EVIDENCE={'schema':1,'commit':os.environ.get('GITHUB_SHA'),'synthetic_data':True,'mocks':False,'environment':'ephemeral-linux-docker','checks':{},'ten_originals_e2e':False,'permanent_deployment':False}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
OPEN=urllib.request.build_opener(NoRedirect)
def request(base,path,body=None,headers=None):
    req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json',**(headers or {})})
    try:
        with OPEN.open(req,timeout=30) as response:
            return response.status,json.load(response)
    except urllib.error.HTTPError as error:
        # Never echo credentials or entire provider responses into public logs.
        raise RuntimeError(f'Provider request failed: {path}, HTTP {error.code}') from None

def main():
    basic=base64.b64encode(('verdugo_lab:'+PASSWORD).encode()).decode()
    headers={'Authorization':'Basic '+basic}
    unique='synthetic-'+os.environ.get('GITHUB_RUN_ID','local')+'@example.invalid'
    status,data=request(BASE_MAUTIC,'/api/contacts/new',{'firstname':'Verdugo','lastname':'Synthetic Acceptance','email':unique,'tags':['verdugo-authentic-lab']},headers)
    assert status in (200,201) and data['contact']['id']>0
    contact_id=data['contact']['id']
    _,readback=request(BASE_MAUTIC,f'/api/contacts/{contact_id}',headers=headers)
    assert readback['contact']['fields']['all']['email']==unique
    EVIDENCE['checks']['mautic_create_and_readback']=True
    print('PASS: authentic Mautic contact POST + GET readback')
    _,registered=request(BASE_GB,'/auth/firsttime',{'email':'operator@example.invalid','name':'Verdugo Laboratory','password':PASSWORD,'companyname':'Verdugo Synthetic Laboratory'})
    assert isinstance(registered.get('token'),str) and len(registered['token'])>20
    _,login=request(BASE_GB,'/auth/login',{'email':'operator@example.invalid','password':PASSWORD})
    assert isinstance(login.get('token'),str) and len(login['token'])>20
    EVIDENCE['checks']['growthbook_account_and_login']=True
    print('PASS: authentic GrowthBook account creation + subsequent login')
    Path('.lab-private/acceptance-state.json').write_text(json.dumps({'mautic_contact_id':contact_id,'email':unique,'growthbook_token':login['token']}))
    EVIDENCE['two_originals_initialized']=True
    EVIDENCE['cross_application_business_flow']=False

if __name__=='__main__':
    try:main()
    finally:
        Path('evidence/originals').mkdir(parents=True,exist_ok=True)
        Path('evidence/originals/acceptance.json').write_text(json.dumps(EVIDENCE,indent=2)+'\n')
        print(json.dumps(EVIDENCE,indent=2))
