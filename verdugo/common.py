import hashlib
import json
import re


class VerdugoError(Exception):
    """A public, credential-free operational error."""


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise VerdugoError('Invalid identifier')
    return value


def fields(params, required=(), optional=()):
    if not isinstance(params, dict):
        raise VerdugoError('Parameters must be an object')
    missing = set(required) - params.keys()
    extra = params.keys() - set(required) - set(optional)
    if missing or extra:
        raise VerdugoError('Invalid fields: missing=%s extra=%s' %
                           (sorted(missing), sorted(extra)))
    if len(encode(params).encode()) > 32768:
        raise VerdugoError('Parameters exceed 32 KiB')


def text(value, maximum=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise VerdugoError('Invalid text value')
    if any(ord(c) < 32 for c in value):
        raise VerdugoError('Control characters are not allowed')
    return value


def integer(value, low=0, high=10**12):
    if type(value) is not int or not low <= value <= high:
        raise VerdugoError('Invalid integer range')
    return value


def sanitize(value, secrets=()):
    """Remove credentials, not business PII. State still requires protected storage."""
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if any(x in k.lower() for x in
                ('token', 'secret', 'password', 'authorization', 'api_key', 'apikey', 'api-key'))
                else sanitize(v, secrets)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, '[REDACTED]')
        return value
    return value
