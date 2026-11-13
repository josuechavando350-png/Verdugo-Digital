#!/usr/bin/env python3
"""Extend the accepted four-original circuit; never sum separate runs as a joint pass."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_base',HERE/'native-pair-acceptance.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
from native_rudderstack import RudderStackTransport
from native_provider_registry import REGISTRY

BASE={'growthbook','mautic','rudderstack','countly'}
SIX={'posthog','erxes','dittofeed','openreplay','twenty','formbricks'}

class ExtendedTransport:
    def __init__(self, selected):
        if not selected or len(selected)!=len(set(selected)) or any(p not in REGISTRY for p in selected):
            raise native.AcceptanceError('unknown_or_duplicate_original_extension')
        self.apps=[REGISTRY[p](native) for p in selected]
        self.rudder=RudderStackTransport(native)
        self.images=dict(self.rudder.images)
        for app in self.apps:
            for name,image in app.images.items():
                if name in self.images and self.images[name]!=image:raise native.AcceptanceError('image_name_collision')
                self.images[name]=image
        self.report=None
    def install(self,**ctx):
        self.report=ctx['report'];self.rudder.install(**ctx)
        for app in self.apps:
            print('NATIVE_EXTRA_STAGE=install_'+app.id,flush=True);app.install(**ctx)
    def deliver(self,params,event_id):
        event=json.loads(params['events'])[0]
        identity={'event_id':event_id,'event_name':event['key'],'subject':params['device_id'],
                  'route':event['segmentation']['route'],'contact_id':event['segmentation']['contact']}
        for app in self.apps:
            print('NATIVE_EXTRA_STAGE=exchange_'+app.id,flush=True)
            if app.exchange(identity)!=identity['route']:raise native.AcceptanceError(app.id+'_route_mismatch')
        # Only data that every selected original actually accepted reaches the destination.
        return self.rudder.deliver(params,event_id)
    def restart(self):
        self.rudder.restart()
        for app in self.apps:
            print('NATIVE_EXTRA_STAGE=restart_'+app.id,flush=True);app.restart()
    def verify_after_restart(self,**ctx):
        self.rudder.verify_after_restart(**ctx)
        for app in self.apps:
            # Base harness resets its exact-origin allowlist; restore only inspected own containers.
            app.base=app.refresh(app.id,app.port)
            print('NATIVE_EXTRA_STAGE=verify_'+app.id,flush=True);app.verify()
        self.report['extra_proof']={a.id:a.proof for a in self.apps}


def enforce_extended(report,selected,base_check):
    for provider in selected:
        for phase in ('rejects_missing_auth','native_readback','after_restart'):
            if report['checks'].get(provider+'_'+phase) is not True:
                raise native.AcceptanceError('incomplete_extra_acceptance_'+provider+'_'+phase)
    base_check(report)
    report['verified_originals']+=list(selected)
    all_api_contracts=set(report['verified_originals'])==BASE|SIX and len(report['verified_originals'])==10
    report['all_ten_native_api_contracts_verified']=all_api_contracts
    # A project/flag configuration API does not prove the primary event/session
    # capture pipelines. Do not turn limited metadata tests into full acceptance.
    proof=report.get('extra_proof',{})
    report['all_ten_integrated']=bool(all_api_contracts
        and proof.get('posthog',{}).get('event_capture_verified') is True
        and proof.get('openreplay',{}).get('session_capture_verified') is True)
    report['production_ready']=False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--providers',nargs='+',required=True,choices=sorted(REGISTRY))
    p.add_argument('--output',default='native-extensions.json')
    args=p.parse_args()
    report=native.evidence_base(True,True)
    report.update(scope='ephemeral_four_plus_original_extensions',requested_extensions=args.providers)
    base_check=native.require_all_checks
    native.require_all_checks=lambda r:enforce_extended(r,args.providers,base_check)
    try:
        transport=ExtendedTransport(args.providers)
        native.run_acceptance(report,include_growthbook=True,transport=transport);code=0
    except native.AcceptanceError as e:report.update(status='blocked_or_failed',error=str(e));code=2
    except Exception as e:report.update(status='failed',error='unexpected_'+type(e).__name__);code=1
    finally:native.require_all_checks=base_check
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return code

if __name__=='__main__':sys.exit(main())
