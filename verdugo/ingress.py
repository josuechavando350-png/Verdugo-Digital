"""Signed canonical events. Not a native provider webhook adapter or public server."""
import hashlib
import hmac
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from .common import VerdugoError, digest, encode, fields, identifier, integer, text
from . import jobs

MAX_BODY = 32768
WINDOW = 300


class IngressError(VerdugoError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def secret(cfg):
    name = cfg['secret_env']
    if not isinstance(name, str) or not re.fullmatch(r'VERDUGO_[A-Z0-9_]+', name):
        raise IngressError('Source credential unavailable', 503)
    value = os.environ.get(name, '')
    if not 32 <= len(value) <= 8192 or any(not 33 <= ord(c) <= 126 for c in value):
        raise IngressError('Source credential unavailable', 503)
    return value.encode('ascii')


def signature(key, tenant, source, timestamp, body):
    """Outbound signers must use the exact raw body and this context-bound format."""
    message = ('verdugo/v1\n%s\n%s\n%s\n' % (tenant, source, timestamp)).encode()+body
    return 'sha256='+hmac.new(key, message, hashlib.sha256).hexdigest()


def parse(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError('Duplicate JSON field')
            out[key] = value
        return out
    def invalid(value): raise ValueError('Nonfinite JSON')
    try:
        return json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IngressError('Invalid bounded JSON') from exc


def accept(engine, source, body, timestamp, supplied):
    jobs.require_operator(engine)
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY:
        raise IngressError('Invalid body size', 413)
    try: cfg = jobs.route(engine, source)
    except VerdugoError as exc: raise IngressError('Event source unavailable', 403) from exc
    if not isinstance(timestamp, str) or not re.fullmatch(r'[0-9]{1,12}', timestamp):
        raise IngressError('Invalid authentication', 401)
    if abs(time.time()-int(timestamp)) > WINDOW:
        raise IngressError('Expired authentication', 401)
    if not isinstance(supplied, str) or not re.fullmatch(r'sha256=[0-9a-f]{64}', supplied):
        raise IngressError('Invalid authentication', 401)
    if not hmac.compare_digest(signature(secret(cfg), engine.tenant, source, timestamp, body), supplied):
        raise IngressError('Invalid authentication', 401)
    envelope = parse(body)
    try:
        fields(envelope, ('id', 'type', 'data'))
        event_id = identifier(envelope['id'])
        if envelope['type'] != 'contact.submitted': raise VerdugoError('Unsupported event type')
        data = envelope['data']
        fields(data, ('external_id', 'first_name', 'email'), ('last_name',))
        external_id = identifier(data['external_id'])
        first = text(data['first_name'], 100)
        last = text(data['last_name'], 100) if 'last_name' in data else ''
        email = text(data['email'], 254)
        if email.count('@') != 1 or ' ' in email: raise VerdugoError('Invalid email')
    except (VerdugoError, ValueError, TypeError, RecursionError) as exc:
        raise IngressError('Event schema rejected') from exc
    lead_id = 'in-' + digest([engine.tenant, source, external_id])[:40]
    payload = {'lead_id': lead_id, 'first_name': first, 'last_name': last,
               'email': email, 'dataset': cfg['dataset']}
    job_id = 'evt-' + digest([engine.tenant, source, event_id])[:40]
    body_hash, now = hashlib.sha256(body).hexdigest(), time.time()
    with engine.transaction():
        old = engine.db.execute('SELECT * FROM inbox WHERE tenant=? AND source=? AND event_id=?',
                                (engine.tenant, source, event_id)).fetchone()
        if old:
            if old['body_hash'] != body_hash: raise IngressError('Event ID conflicts with accepted content', 409)
            return {'state': 'accepted', 'job_id': old['job_id'], 'duplicate': True, 'external_calls_made': False}
        pending = engine.db.execute("SELECT COUNT(*) FROM jobs WHERE tenant=? AND source=? AND state!='succeeded'",
                                    (engine.tenant, source)).fetchone()[0]
        if pending >= cfg.get('max_pending', 100): raise IngressError('Source queue capacity reached', 429)
        engine.db.execute('INSERT INTO inbox VALUES(?,?,?,?,?,?)',
                          (engine.tenant, source, event_id, body_hash, job_id, now))
        engine.db.execute('INSERT INTO jobs(tenant,id,source,route_hash,handler,payload,state,max_attempts,available,created,updated) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?)', (engine.tenant, job_id, source, jobs.route_hash(cfg), cfg['handler'],
            encode(payload), 'pending', cfg.get('max_attempts', 3), now, now, now))
        engine.event(job_id, 'event.accepted', {'source': source, 'event_id': event_id, 'body_hash': body_hash})
    return {'state': 'accepted', 'job_id': job_id, 'duplicate': False, 'external_calls_made': False}


def make_server(engine_factory, port=8765):
    """Development/acceptance only, hard-bound to IPv4 loopback; one Engine per request."""
    integer(port, 0, 65535)
    class Handler(BaseHTTPRequestHandler):
        server_version = 'VerdugoLocalIngress/0.3'
        sys_version = ''
        def setup(self):
            self.request.settimeout(5)
            super().setup()
        def log_message(self, *args): pass
        def reply(self, status, document):
            body = encode(document).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True
        def do_GET(self): self.reply(405, {'error': 'POST required'})
        def do_POST(self):
            engine = None
            try:
                match = re.fullmatch(r'/v1/events/([A-Za-z0-9_-]{1,100})', self.path)
                if not match: raise IngressError('Unknown route', 404)
                for name in ('Content-Length', 'Content-Type', 'X-Verdugo-Timestamp', 'X-Verdugo-Signature'):
                    if len(self.headers.get_all(name, [])) != 1: raise IngressError('Required unique headers missing')
                if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Encoding'):
                    raise IngressError('Encoded requests are unsupported')
                if self.headers['Content-Type'].lower() != 'application/json':
                    raise IngressError('application/json required', 415)
                value = self.headers['Content-Length']
                if not re.fullmatch(r'[0-9]{1,6}', value) or not 0 < int(value) <= MAX_BODY:
                    raise IngressError('Invalid body size', 413)
                body = self.rfile.read(int(value))
                if len(body) != int(value): raise IngressError('Incomplete body')
                engine = engine_factory()
                result = accept(engine, match[1], body, self.headers['X-Verdugo-Timestamp'], self.headers['X-Verdugo-Signature'])
                self.reply(200 if result['duplicate'] else 202, result)
            except IngressError as exc:
                self.reply(exc.status, {'error': str(exc)})
            except Exception:
                self.reply(503, {'error': 'Receiver unavailable; retry using the same event ID'})
            finally:
                if engine is not None: engine.close()
    return HTTPServer(('127.0.0.1', port), Handler)
