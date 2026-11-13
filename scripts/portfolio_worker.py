#!/usr/bin/env python3
"""Bounded, network-disabled bridge to ORIGINAL Python libraries.

Only local transformations/signature validation; never sends ads, calls or money.
No URL/file-path inputs, model downloads, plugins or provider credentials in JSON.
The Node control plane can invoke one request over stdin and receive one receipt.
"""
from __future__ import annotations
import importlib.metadata
import importlib.util
import io
import json
import os
import socket
import sys
import time

DISTRIBUTIONS = {
    'email.validate': ('email-validator', 'email_validator'),
    'document.convert_html': ('markitdown', 'markitdown'),
    'text.segment_es': ('spacy', 'spacy'),
    'stripe.verify_signature': ('stripe', 'stripe'),
    'twilio.verify_signature': ('twilio', 'twilio'),
}
MAX_INPUT = 65_536

class WorkerError(Exception):
    pass

def shape(value, required):
    if type(value) is not dict or set(value) != set(required):
        raise WorkerError('invalid_fields')

def bounded_text(value, maximum=20000):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or '\x00' in value:
        raise WorkerError('invalid_text')
    return value

def deny_network(*args, **kwargs):
    raise WorkerError('network_disabled_in_local_worker')

def disable_network():
    # Defense in depth; CI also asserts that our operations do not make HTTP calls.
    # This is not an OS sandbox and is not advertised as one.
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network

def installed():
    values = []
    for operation, (distribution, module) in DISTRIBUTIONS.items():
        try:
            version = importlib.metadata.version(distribution)
            present = importlib.util.find_spec(module) is not None
        except (ImportError, importlib.metadata.PackageNotFoundError):
            version, present = None, False
        values.append({'operation': operation, 'distribution': distribution,
                       'version': version, 'package_present': present,
                       'live_provider_verified': False})
    return {'operations': values, 'outbound_network': False,
            'all_fifty_integrated': False, 'availability_is_not_execution_evidence': True}

def operation(name, data):
    if name not in DISTRIBUTIONS:
        raise WorkerError('operation_not_implemented')
    distribution, module = DISTRIBUTIONS[name]
    try:
        version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        raise WorkerError('dependency_not_installed') from None
    if name == 'email.validate':
        shape(data, ['email'])
        from email_validator import validate_email, EmailNotValidError
        try:
            # No DNS, SMTP probing or mailbox availability claim.
            value = validate_email(bounded_text(data['email'], 254), check_deliverability=False)
        except EmailNotValidError:
            raise WorkerError('invalid_email') from None
        result = {'email': value.normalized, 'syntax_valid': True,
                  'mailbox_verified': False, 'consent_inferred': False}
    elif name == 'document.convert_html':
        shape(data, ['html'])
        from markitdown import MarkItDown, StreamInfo
        text = bounded_text(data['html'], 24000)
        # Explicit HTML stream, no filenames/URLs or auto-discovery plugins.
        converter = MarkItDown(enable_plugins=False)
        converted = converter.convert_stream(io.BytesIO(text.encode('utf-8')),
                    stream_info=StreamInfo(mimetype='text/html', extension='.html'))
        markdown = getattr(converted, 'markdown', None)
        if markdown is None:
            markdown = converted.text_content
        if not isinstance(markdown, str) or len(markdown) > 48000:
            raise WorkerError('invalid_conversion_output')
        result = {'markdown': markdown, 'source_type': 'provided_html',
                  'external_sources_fetched': False, 'legal_accuracy_verified': False}
    elif name == 'text.segment_es':
        shape(data, ['text'])
        import spacy
        nlp = spacy.blank('es')
        nlp.add_pipe('sentencizer')
        doc = nlp(bounded_text(data['text']))
        result = {'sentences': [s.text for s in doc.sents], 'tokens': len(doc),
                  'language': 'es', 'pipeline': 'blank_es_sentencizer',
                  'trained_ner_model': False, 'buying_intent_inferred': False}
    elif name == 'stripe.verify_signature':
        shape(data, ['raw_body', 'signature'])
        import stripe
        secret = os.environ.get('VERDUGO_STRIPE_WEBHOOK_SECRET', '')
        if not secret.startswith('whsec_') or len(secret) < 24:
            raise WorkerError('stripe_signing_secret_required')
        raw = bounded_text(data['raw_body'], 24000)
        signature = bounded_text(data['signature'], 4096)
        try:
            stamps = [int(v[2:]) for v in signature.split(',') if v.startswith('t=')]
            if len(stamps) != 1 or abs(time.time() - stamps[0]) > 300:
                raise ValueError('timestamp')
            event = stripe.Webhook.construct_event(raw.encode('utf-8'), signature, secret, tolerance=300).to_dict()
        except Exception:
            raise WorkerError('invalid_stripe_signature') from None
        # Only authentication evidence, never counts as a bank reconciliation.
        result = {'provider_event_id': event.get('id'), 'provider_event_type': event.get('type'),
                  'signature_valid': True, 'live_mode': event.get('livemode') is True,
                  'payment_reconciled': False}
    else:
        shape(data, ['parameters', 'signature'])
        from twilio.request_validator import RequestValidator
        from urllib.parse import urlsplit
        token = os.environ.get('VERDUGO_TWILIO_AUTH_TOKEN', '')
        public_url = os.environ.get('VERDUGO_TWILIO_WEBHOOK_URL', '')
        parsed = urlsplit(public_url)
        if len(token) < 24 or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query:
            raise WorkerError('twilio_signing_configuration_required')
        params = data['parameters']
        if type(params) is not dict or len(params) > 60 or any(not isinstance(k, str) or not isinstance(v, str) or len(k)>100 or len(v)>2000 for k,v in params.items()):
            raise WorkerError('invalid_twilio_parameters')
        if not RequestValidator(token).validate(public_url, params, bounded_text(data['signature'], 1024)):
            raise WorkerError('invalid_twilio_signature')
        result = {'signature_valid': True, 'call_sid': params.get('CallSid'),
                  'call_status': params.get('CallStatus'), 'outbound_call_placed': False}
    return {'operation': name, 'distribution': distribution, 'version': version,
            'result': result, 'execution': 'original_library',
            'live_provider_verified': False, 'external_side_effects': False}

def main():
    disable_network()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise WorkerError('body_too_large')
        message = json.loads(raw)
        shape(message, ['operation', 'data'])
        result = installed() if message['operation']=='capabilities' and message['data']=={} else operation(message['operation'], message['data'])
        print(json.dumps({'ok': True, **result}, ensure_ascii=False))
        return 0
    except WorkerError as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 2
    except (ValueError, TypeError):
        print(json.dumps({'ok': False, 'error': 'invalid_json_or_input'}))
        return 2
    except Exception:
        # Never expose raw provider errors, stack traces, user data or secrets.
        print(json.dumps({'ok': False, 'error': 'native_operation_failed'}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
