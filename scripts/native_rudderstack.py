"""Authentic RudderStack transport for the native acceptance laboratory.

No replacement gateway or destination mock: the original server, transformer,
and PostgreSQL forward a track event into the original Countly HTTP API.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.parse
import uuid
from pathlib import Path

# Official references are resolved to immutable IDs and recorded before execution.
# First successful execution must publish its observed digest lock before production use.
IMAGES = {
    'rudder_postgres': 'postgres:15-alpine',
    'rudder_server': 'rudderlabs/rudder-server:latest',
    'rudder_transformer': 'rudderstack/rudder-transformer:latest',
}


def workspace_config(write_key, countly_key, countly_origin):
    parsed = urllib.parse.urlsplit(countly_origin)
    if parsed.hostname != 'countly.native.invalid' or parsed.port != 3001 or parsed.scheme != 'http' or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('invalid_native_destination_origin')
    if not isinstance(write_key, str) or len(write_key) < 32 or not isinstance(countly_key, str) or len(countly_key) < 8:
        raise ValueError('invalid_temporary_keys')
    destination = {
        'id': 'vd-native-countly-http', 'name': 'Countly authentic native API',
        'enabled': True, 'isProcessorEnabled': True, 'workspaceId': 'vd-native-workspace',
        'transformations': [], 'revisionId': 'native-acceptance-1',
        'destinationDefinition': {
            'id': 'vd-native-http-definition', 'name': 'HTTP', 'displayName': 'HTTP',
            'config': {'supportedMessageTypes': ['track'], 'supportsRouterTransform': False},
        },
        'config': {
            'apiUrl': countly_origin + '/i', 'auth': 'noAuth', 'method': 'POST',
            'format': 'FORM', 'isBatchingEnabled': False, 'isDefaultMapping': False,
            'connectionMode': {'web': 'cloud', 'cloud': 'cloud'},
            'propertiesMapping': [
                {'from': '$.properties.native_app_key', 'to': '$.app_key'},
                {'from': '$.userId', 'to': '$.device_id'},
                {'from': '$.properties.native_events', 'to': '$.events'},
            ],
        },
    }
    return {
        'workspaceId': 'vd-native-workspace', 'enableMetrics': False,
        'sources': [{
            'id': 'vd-native-http-source', 'name': 'Verdugo Native Source',
            'enabled': True, 'workspaceId': 'vd-native-workspace', 'writeKey': write_key,
            'sourceDefinition': {'id': 'vd-native-source-definition', 'name': 'Javascript', 'category': 'browser', 'type': 'web'},
            'config': {}, 'destinations': [destination],
        }],
    }


class RudderStackTransport:
    """A disposable native transport; acceptance is gated by downstream readback."""
    images = IMAGES

    def __init__(self, native):
        self.native = native
        self.names = []
        self.base = None
        self.write_key = None
        self.countly_app = None
        self.docker = None
        self.report = None
        self.network = None

    def install(self, *, start, docker, refs, temp, network, report, countly_origin, countly_app):
        n = self.native
        self.docker, self.report, self.network = docker, report, network
        self.write_key = secrets.token_hex(32)
        db_password = secrets.token_hex(32)
        n.mask_secret(self.write_key)
        n.mask_secret(db_password)
        self.countly_app = countly_app
        config = workspace_config(self.write_key, countly_app['key'], countly_origin)
        path = Path(temp) / 'rudder-workspace.json'
        path.write_text(json.dumps(config), encoding='utf8')
        # This file is mounted read-only into the disposable container. The host parent
        # is private 0700; no user credentials are included and it is removed on exit.
        path.chmod(0o644)
        start('rudder-postgres', refs['rudder_postgres'], alias='rudder-postgres', env={
            'POSTGRES_USER': 'rudder', 'POSTGRES_DB': 'jobsdb', 'POSTGRES_PASSWORD': db_password})
        pg = self._find('rudder-postgres')
        n.wait_until(lambda: docker('exec', pg, 'pg_isready', '-U', 'rudder', '-d', 'jobsdb', timeout=10))
        start('rudder-transformer', refs['rudder_transformer'], alias='rudder-transformer', port=9090, env={
            'NODE_OPTIONS': '--max-old-space-size=768', 'LOG_LEVEL': 'warn',
            'DISABLE_INTEGRATION_CACHE': 'true',
        })
        self.base = start('rudder-server', refs['rudder_server'], port=8080, env={
            'JOBS_DB_HOST': 'rudder-postgres', 'JOBS_DB_USER': 'rudder',
            'JOBS_DB_PORT': '5432', 'JOBS_DB_DB_NAME': 'jobsdb',
            'JOBS_DB_PASSWORD': db_password, 'JOBS_DB_SSL_MODE': 'disable',
            'DEST_TRANSFORM_URL': 'http://rudder-transformer:9090',
            'RSERVER_BACKEND_CONFIG_CONFIG_FROM_FILE': 'true',
            'RSERVER_BACKEND_CONFIG_CONFIG_JSONPATH': '/etc/rudderstack/workspaceConfig.json',
            'RSERVER_ENABLE_STATS': 'false', 'RSERVER_DIAGNOSTICS_ENABLE_DIAGNOSTICS': 'false',
            'RSERVER_WAREHOUSE_MODE': 'off', 'LOG_LEVEL': 'WARN',
            'GOMAXPROCS': '2', 'GOMEMLIMIT': '900MiB',
        }, mounts=[(str(path), '/etc/rudderstack/workspaceConfig.json')])
        self.names = [self._find('rudder-server'), self._find('rudder-transformer'), pg]
        n.wait_until(lambda: n.request(self.base + '/health') is not None)
        # Real gateway authentication, not an HTTP fixture or a control-plane-only check.
        try:
            n.request(self.base + '/v1/track', data={'userId': 'synthetic', 'event': 'must-not-ingest'}, expect_json=False)
        except n.AcceptanceError as exc:
            if str(exc) not in ('http_status_401', 'http_status_403'):
                raise
        else:
            raise n.AcceptanceError('rudderstack_missing_auth_accepted')
        report['checks']['rudderstack_rejects_missing_auth'] = True

    def _find(self, suffix):
        # Only current-network labelled containers created by the native harness.
        ids = self.docker('ps', '-a', '--filter', 'network=' + self.network,
                          '--filter', 'name=-' + suffix, '--format', '{{.Names}}').splitlines()
        exact = [name for name in ids if name.endswith('-' + suffix)]
        if len(exact) != 1:
            raise self.native.AcceptanceError('native_transport_container_not_unique')
        return exact[0]

    def deliver(self, params, event_id):
        events = json.loads(params['events'])
        if len(events) != 1:
            raise self.native.AcceptanceError('native_transport_requires_one_event')
        auth = 'Basic ' + base64.b64encode((self.write_key + ':').encode()).decode()
        self.native.mask_secret(auth)
        payload = {
            'userId': params['device_id'], 'event': events[0]['key'], 'messageId': event_id,
            'properties': {'native_app_key': params['app_key'], 'native_events': params['events']},
            'context': {'library': {'name': 'verdugo-native-acceptance', 'version': '1.0.0'}},
        }
        ack = self.native.request(self.base + '/v1/track', data=payload,
                                  headers={'Authorization': auth}, expect_json=False)
        if ack.get('http_status') != 200 or ack.get('body', '').strip() != 'OK':
            raise self.native.AcceptanceError('rudderstack_gateway_not_accepted')
        self.report['checks']['rudderstack_gateway_accepted'] = True
        # This means only gateway acceptance. The caller must verify the real Countly
        # event AND route before classifying the native transport as integrated.
        return {'result': 'Success'}

    def verify_after_restart(self, *, countly_origin, route):
        n = self.native
        info = json.loads(self.docker('inspect', self.names[0]))[0]
        self.base = n.native_origin(info, self.network, 8080)
        n.wait_until(lambda: n.request(self.base + '/health') is not None)
        event_id = str(uuid.uuid4())
        event_key = 'vd_rudder_restart_' + hashlib.sha256(event_id.encode()).hexdigest()[:20]
        params = {
            'app_key': self.countly_app['key'], 'device_id': hashlib.sha256(event_id.encode()).hexdigest(),
            'events': json.dumps([{'key': event_key, 'count': 1, 'segmentation': {'route': route, 'source': 'rudderstack-restart'}}]),
        }
        self.deliver(params, event_id)
        auth_query = urllib.parse.urlencode({'api_key': self.countly_app['admin_key'], 'app_id': self.countly_app['_id']})
        def observed():
            value = n.request(countly_origin + '/o/analytics/events?' + auth_query)
            rows = value.get('all', [])
            return any(r.get('_id') == event_key and r.get('c') == 1 for r in rows)
        n.wait_until(observed, seconds=180)
        query = urllib.parse.urlencode({'api_key': self.countly_app['admin_key'], 'app_id': self.countly_app['_id'],
                                        'method': 'events', 'event': event_key, 'segmentation': 'route'})
        n.wait_until(lambda: route in n.request(countly_origin + '/o?' + query).get('meta', {}).get('route', []), seconds=120)
        self.report['checks']['rudderstack_delivery_after_restart'] = True
