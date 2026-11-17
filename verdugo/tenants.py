"""Explicit, serialized local tenant creation shared by CLI and operator panel."""
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile

from .common import VerdugoError, identifier


def _read(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 5*1024*1024:
                raise VerdugoError('Configuración local inválida')
            data = json.load(stream)
        if not isinstance(data, dict) or not isinstance(data.get('tenants'), dict):
            raise VerdugoError('Configuración local inválida')
        return data
    except (OSError, ValueError):
        raise VerdugoError('No se puede leer la configuración local') from None


def add(config_path, name, role='operator', execute=False):
    if role != 'operator': raise VerdugoError('Operator role required to create a tenant')
    if type(execute) is not bool: raise VerdugoError('execute debe ser booleano')
    identifier(name)
    path = Path(config_path).expanduser().absolute()
    def prepare():
        data = _read(path)
        if name in data['tenants']: raise VerdugoError('Tenant already exists')
        return data
    result = {'tenant': name, 'services_enabled': 0, 'subscription_required': True,
              'external_calls_made': False}
    if not execute:
        prepare()
        return result | {'state': 'planned'}
    # A separate lock survives the atomic config replacement. All product entry
    # points use it; no fixed .tmp file can be followed or overwritten.
    lock_path = path.with_name(path.name + '.lock')
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, 'r+') as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise VerdugoError('Archivo de bloqueo local inválido')
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = prepare()
        from .__main__ import template
        data['tenants'][name] = template(name)['tenants'][name] | {'subscription_required': True}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.verdugo-config-', delete=False) as stream:
                temporary = Path(stream.name)
                os.fchmod(stream.fileno(), 0o600)
                json.dump(data, stream, indent=2)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
    return result | {'state': 'applied'}
