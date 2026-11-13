"""Original-library acceptance with synthetic data. Never contacts provider APIs."""
import base64
import hashlib
import hmac
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portfolio_worker',ROOT/'scripts/portfolio_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
REQUIRE=os.environ.get('REQUIRE_PORTFOLIO_NATIVE')=='1'

def dependency(test,package):
    try:return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        if REQUIRE:test.fail('Original dependency missing: '+package)
        test.skipTest('Original dependency not installed locally: '+package)

class OriginalLibraryAcceptance(unittest.TestCase):
    def test_no_shell_or_unimplemented_operation(self):
        with self.assertRaisesRegex(worker.WorkerError,'operation_not_implemented'):
            worker.operation('shell.exec',{'command':'echo nope'})

    def test_original_email_normalization_without_dns(self):
        dependency(self,'email-validator')
        with patch.object(worker.socket,'getaddrinfo',side_effect=AssertionError('DNS forbidden')):
            r=worker.operation('email.validate',{'email':'contacto@EXAMPLE.com'})
        self.assertEqual(r['result']['email'],'contacto@example.com')
        self.assertFalse(r['result']['mailbox_verified'])
        self.assertFalse(r['result']['consent_inferred'])
        with self.assertRaises(worker.WorkerError):worker.operation('email.validate',{'email':'not email'})

    def test_original_markitdown_converts_provided_html_without_network(self):
        dependency(self,'markitdown')
        with patch.object(worker.socket.socket,'connect',side_effect=AssertionError('network forbidden')):
            r=worker.operation('document.convert_html',{'html':'<h1>Empresa sintética</h1><p>Abre una oficina.</p>'})
        self.assertIn('Empresa sintética',r['result']['markdown'])
        self.assertIn('Abre una oficina',r['result']['markdown'])
        self.assertFalse(r['result']['external_sources_fetched'])
        with self.assertRaises(worker.WorkerError):worker.operation('document.convert_html',{'url':'https://example.com'})

    def test_original_spacy_uses_spanish_pipeline_not_fabricated_intent(self):
        dependency(self,'spacy')
        r=worker.operation('text.segment_es',{'text':'Abre una sucursal. Requiere revisión comercial.'})
        self.assertEqual(len(r['result']['sentences']),2)
        self.assertFalse(r['result']['trained_ner_model'])
        self.assertFalse(r['result']['buying_intent_inferred'])
        self.assertEqual(r['execution'],'original_library')

    def test_original_stripe_sdk_accepts_valid_signature_not_payment_proof(self):
        dependency(self,'stripe')
        raw=json.dumps({'id':'evt_synthetic_verdugo','object':'event','type':'checkout.session.completed','livemode':False,'data':{'object':{'id':'cs_synthetic'}}},separators=(',',':'))
        secret='whsec_synthetic_only_not_a_live_secret_123456789'
        now=int(time.time())
        sig=hmac.new(secret.encode(),(str(now)+'.'+raw).encode(),hashlib.sha256).hexdigest()
        with patch.dict(os.environ,{'VERDUGO_STRIPE_WEBHOOK_SECRET':secret}):
            r=worker.operation('stripe.verify_signature',{'raw_body':raw,'signature':f't={now},v1={sig}'})
            self.assertTrue(r['result']['signature_valid']);self.assertFalse(r['result']['payment_reconciled'])
            for bad_raw,bad_sig in [(raw+' ',f't={now},v1={sig}'),(raw,f't={now-600},v1={sig}'),(raw,f't={now+600},v1={sig}')]:
                with self.assertRaises(worker.WorkerError):worker.operation('stripe.verify_signature',{'raw_body':bad_raw,'signature':bad_sig})
        with patch.dict(os.environ,{'VERDUGO_STRIPE_WEBHOOK_SECRET':''}):
            with self.assertRaisesRegex(worker.WorkerError,'stripe_signing_secret_required'):
                worker.operation('stripe.verify_signature',{'raw_body':raw,'signature':f't={now},v1={sig}'})

    def test_original_twilio_sdk_verifies_callback_but_never_places_call(self):
        dependency(self,'twilio')
        url='https://example.invalid/verdugo/call';secret='synthetic_twilio_token_123456789012345'
        params={'CallSid':'CA'+'0'*32,'CallStatus':'completed'}
        signed=url+''.join(k+params[k] for k in sorted(params))
        signature=base64.b64encode(hmac.new(secret.encode(),signed.encode(),hashlib.sha1).digest()).decode()
        with patch.dict(os.environ,{'VERDUGO_TWILIO_AUTH_TOKEN':secret,'VERDUGO_TWILIO_WEBHOOK_URL':url}):
            r=worker.operation('twilio.verify_signature',{'parameters':params,'signature':signature})
            self.assertTrue(r['result']['signature_valid']);self.assertFalse(r['result']['outbound_call_placed'])
            with self.assertRaises(worker.WorkerError):worker.operation('twilio.verify_signature',{'parameters':{**params,'CallStatus':'wrong'},'signature':signature})

    def test_native_network_guard_is_fail_closed(self):
        with self.assertRaisesRegex(worker.WorkerError,'network_disabled'):
            worker.deny_network('https://example.invalid')

    def test_capabilities_never_claim_live_integration(self):
        result=worker.installed();self.assertFalse(result['all_fifty_integrated'])
        self.assertTrue(all(r['live_provider_verified'] is False for r in result['operations']))

if __name__=='__main__':unittest.main()
