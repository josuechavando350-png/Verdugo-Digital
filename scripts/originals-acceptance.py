"""Acceptance against authentic applications installed by the Docker laboratory.

Only generated example.invalid contacts; all HTTP destinations are private container
addresses discovered from this run's isolated Docker network. Provider writes are never retried automatically. Authentication bootstrap is
performed through the original APIs, never by directly inserting fake DB rows.
"""
import base64
import json
import ipaddress
import urllib.parse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

def lab_origin(name):
    value = os.environ[name]
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != 'http' or not parsed.hostname or
            not ipaddress.ip_address(parsed.hostname).is_private or
            parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('Invalid discovered laboratory origin')
    return value

BASE_MAUTIC = lab_origin('LAB_MAUTIC_BASE')
BASE_GB = lab_origin('LAB_GROWTHBOOK_BASE')
STATE_PATH = Path('.lab-private/acceptance-state.json')
EVIDENCE_PATH = Path('evidence/originals/acceptance.json')
PASSWORD = os.environ.get('LAB_ADMIN_PASSWORD', '')
SECRETS = [PASSWORD]
EVIDENCE = {
    'schema': 2, 'commit': os.environ.get('GITHUB_SHA'),
    'synthetic_data': True, 'mock_providers': False,
    'environment': 'ephemeral-linux-docker', 'checks': {},
    'ten_originals_e2e': False, 'permanent_deployment': False,
    'android_verified': False,
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def redact(message):
    for value in SECRETS:
        if value:
            message = message.replace(value, '[REDACTED]')
    return message[:500]


def request(base, path, body=None, headers=None):
    if base not in (BASE_GB, BASE_MAUTIC) or not path.startswith('/'):
        raise ValueError('Unapproved laboratory endpoint')
    req = urllib.request.Request(
        base + path, data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', **(headers or {})},
    )
    try:
        with OPEN.open(req, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        # Only the short error message is retained, never a complete response.
        message = ''
        try:
            parsed = json.loads(error.read(8192))
            if isinstance(parsed, dict):
                message = str(parsed.get('message', ''))
        except (ValueError, OSError):
            pass
        raise RuntimeError(f'{path}: HTTP {error.code}; {redact(message)}') from None


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    EVIDENCE['checks'][name] = True
    print('PASS:', name, flush=True)


def negative_auth():
    for base, path in [(BASE_MAUTIC, '/api/contacts'), (BASE_GB, '/api/v1/features')]:
        req = urllib.request.Request(base + path)
        try:
            with OPEN.open(req, timeout=15) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        check(('mautic' if base == BASE_MAUTIC else 'growthbook') + '_rejects_missing_auth', status in (401, 403))


def bootstrap():
    if not PASSWORD or STATE_PATH.exists():
        raise RuntimeError('Require fresh isolated lab and nonempty generated password')
    _, registered = request(BASE_GB, '/auth/firsttime', {
        'email': 'operator@example.invalid', 'name': 'Verdugo Laboratory',
        'password': PASSWORD, 'companyname': 'Verdugo Synthetic Laboratory',
    })
    check('growthbook_original_account_created', isinstance(registered.get('token'), str))
    _, login = request(BASE_GB, '/auth/login', {'email': 'operator@example.invalid', 'password': PASSWORD})
    token = login['token']
    SECRETS.append(token)
    auth = {'Authorization': 'Bearer ' + token}
    _, user = request(BASE_GB, '/user', headers=auth)
    check('growthbook_original_account_readback', len(user['organizations']) == 1)
    auth['X-Organization'] = user['organizations'][0]['id']
    _, created = request(BASE_GB, '/keys', {'type': 'admin', 'description': 'Ephemeral synthetic acceptance only'}, auth)
    key = created['key']['key']
    SECRETS.append(key)
    check('growthbook_original_api_key_created', isinstance(key, str) and len(key) > 20)
    rest_auth = {'Authorization': 'Bearer ' + key}
    feature_id = 'verdugo-acceptance-routing'
    route = 'verdugo-original-route'
    _, created_feature = request(BASE_GB, '/api/v1/features', {
        'id': feature_id, 'valueType': 'string', 'defaultValue': route,
        'description': 'Synthetic route shared with authentic Mautic',
        'owner': 'operator@example.invalid',
        'project': registered.get('projectId', ''),
    }, rest_auth)
    check('growthbook_original_feature_write', created_feature['feature']['id'] == feature_id)
    _, feature = request(BASE_GB, '/api/v1/features/' + feature_id, headers=rest_auth)
    route_from_upstream = feature['feature']['defaultValue']
    check('growthbook_original_feature_readback', route_from_upstream == route)
    basic = base64.b64encode(('verdugo_lab:' + PASSWORD).encode()).decode()
    SECRETS.append(basic)
    mautic_auth = {'Authorization': 'Basic ' + basic}
    unique = 'synthetic-' + os.environ.get('GITHUB_RUN_ID', 'local') + '@example.invalid'
    status, contact = request(BASE_MAUTIC, '/api/contacts/new', {
        'firstname': 'Verdugo', 'lastname': 'Synthetic Acceptance', 'email': unique,
        'tags': [route_from_upstream],
    }, mautic_auth)
    check('mautic_original_contact_write', status in (200, 201) and contact['contact']['id'] > 0)
    state = {'mautic_contact_id': contact['contact']['id'], 'email': unique,
             'growthbook_key': key, 'feature_id': feature_id, 'route': route}
    STATE_PATH.write_text(json.dumps(state))
    STATE_PATH.chmod(0o600)
    verify_state(state, 'initial')
    negative_auth()
    EVIDENCE['authentic_cross_application_flow'] = True
    EVIDENCE['bounded_flow'] = 'GrowthBook stored feature -> bridge -> Mautic contact tag -> native API readback'


def verify_state(state, stage):
    key = state['growthbook_key']
    SECRETS.append(key)
    _, feature = request(BASE_GB, '/api/v1/features/' + state['feature_id'], headers={'Authorization': 'Bearer ' + key})
    route = feature['feature']['defaultValue']
    check('growthbook_' + stage + '_readback', route == state['route'])
    basic = base64.b64encode(('verdugo_lab:' + PASSWORD).encode()).decode()
    SECRETS.append(basic)
    _, result = request(BASE_MAUTIC, '/api/contacts/' + str(state['mautic_contact_id']), headers={'Authorization': 'Basic ' + basic})
    contact = result['contact']
    check('mautic_' + stage + '_contact_readback', contact['fields']['all']['email'] == state['email'])
    tags = contact.get('tags', [])
    if isinstance(tags, dict):
        tags = list(tags.values())
    values = [t.get('tag') if isinstance(t, dict) else t for t in tags]
    check('cross_application_' + stage + '_tag_matches', route in values)


def main():
    global EVIDENCE
    if '--after-restart' in sys.argv:
        EVIDENCE = json.loads(EVIDENCE_PATH.read_text())
        state = json.loads(STATE_PATH.read_text())
        verify_state(state, 'after_restart')
        EVIDENCE['persistent_cross_application_flow'] = True
    else:
        bootstrap()


if __name__ == '__main__':
    try:
        main()
    finally:
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(json.dumps(EVIDENCE, indent=2) + '\n')
        print(json.dumps(EVIDENCE, indent=2), flush=True)
