"""Private recovery sets and local readiness, without remote actions or auto-resume."""
from contextlib import closing
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import stat
import time

from . import __version__, backups, tenants
from .common import VerdugoError, encode, identifier

FILES = ('config.json', 'estado.sqlite3')


def _operator(role):
    if role != 'operator': raise VerdugoError('Operator role required for maintenance')


def _directory(path):
    path = Path(path).expanduser().absolute()
    if path.is_symlink(): raise VerdugoError('Directorio privado sin enlaces requerido')
    return backups._private_dir(path)


def _config(path):
    backups._inspect(path)
    data = tenants._read(path)
    if not data['tenants']: raise VerdugoError('Configuración sin clientes')
    for name, cfg in data['tenants'].items():
        identifier(name)
        if not isinstance(cfg, dict): raise VerdugoError('Configuración de cliente inválida')
        for key in ('services', 'ingress'):
            values = cfg.get(key, {})
            if not isinstance(values, dict) or any(not isinstance(v, dict) for v in values.values()):
                raise VerdugoError('Configuración de servicios inválida')
    return data


def _write(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(encode(data) + '\n'); stream.flush(); os.fsync(stream.fileno())


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def pending(db):
    conversions = 0
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='cycle_uploads'").fetchone():
        conversions = db.execute("SELECT COUNT(*) FROM cycle_uploads WHERE state IN ('running','uncertain','exporting','exported')").fetchone()[0]
    return {
        'unresolved_conversions': conversions,
        'unresolved_runs': db.execute("SELECT COUNT(*) FROM runs WHERE state IN ('running','uncertain')").fetchone()[0],
        'unfinished_jobs': db.execute("SELECT COUNT(*) FROM jobs WHERE state != 'succeeded'").fetchone()[0],
    }


def verify_set(directory):
    root = _directory(directory)
    if {p.name for p in root.iterdir()} != set(FILES) | {'manifest.json'}:
        raise VerdugoError('Respaldo incompleto o con archivos inesperados')
    path = backups._inspect(root/'manifest.json')
    if path.stat().st_size > 8192: raise VerdugoError('Manifiesto de respaldo inválido')
    try:
        manifest = json.loads(path.read_text())
        if (manifest['schema'] != 1 or not isinstance(manifest['version'], str)
                or len(manifest['version']) > 50 or set(manifest['sha256']) != set(FILES)
                or type(manifest['created_at']) not in (int, float)
                or not 0 < manifest['created_at'] <= time.time() + 300): raise ValueError()
        for name in FILES:
            member = backups._inspect(root/name)
            if backups._digest(member) != manifest['sha256'][name]: raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise VerdugoError('Respaldo alterado o manifiesto inválido') from None
    _config(root/'config.json')
    report = backups.verify(root/'estado.sqlite3')
    with closing(sqlite3.connect((root/'estado.sqlite3').as_uri()+'?mode=ro&immutable=1', uri=True)) as db:
        counts = pending(db)
    return {'state': 'verified_recovery_set', 'created_at': manifest['created_at'],
            'version': manifest['version'], 'bytes': report['bytes'], **counts,
            'restore_allowed': not any(counts.values()), 'encrypted': False,
            'external_calls_made': False, 'restoration_tested': False}


def create_set(engine, config_path, destination=None):
    _operator(engine.role)
    if engine.state_path == ':memory:': raise VerdugoError('Persistent state required')
    path = Path(config_path).expanduser().absolute()
    # Same lock as tenant creation: a new tenant cannot appear between config and DB snapshots.
    fd = os.open(path.with_name(path.name+'.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, 'r+') as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise VerdugoError('Bloqueo de configuración inválido')
        os.fchmod(lock.fileno(), 0o600); fcntl.flock(lock, fcntl.LOCK_EX)
        config = _config(path)
        if config != engine.config: raise VerdugoError('La configuración cambió; vuelve a intentar el respaldo')
        if destination is None:
            folder = Path(engine.state_path).parent/'respaldos.local'
            folder.mkdir(mode=0o700, exist_ok=True)
            _directory(folder)
            destination = folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4))
        destination = Path(destination).expanduser().absolute()
        _directory(destination.parent)
        destination.mkdir(mode=0o700)  # Exclusive; never overwrites any existing directory.
        try:
            _write(destination/'config.json', config)
            backups.create(engine, str(destination/'estado.sqlite3'))
            manifest = {'schema': 1, 'version': __version__, 'created_at': time.time(),
                        'sha256': {name: backups._digest(destination/name) for name in FILES}}
            _write(destination/'manifest.json', manifest)
            _sync_dir(destination); _sync_dir(destination.parent)
            result = verify_set(destination)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return result | {'state': 'created_recovery_set', 'saved_directory': str(destination),
                     'contains_personal_data': True, 'includes_environment_secrets': False,
                     'includes_runtime_profiles': False}


def restore_set(source, destination, role='operator', execute=False):
    _operator(role)
    if type(execute) is not bool: raise VerdugoError('execute debe ser booleano')
    source = _directory(source)
    result = verify_set(source)
    expected = json.loads((source/'manifest.json').read_text())['sha256']
    if not result['restore_allowed']:
        raise VerdugoError('Conciliación offline requerida: hay ejecuciones inciertas o trabajos sin cerrar')
    destination = Path(destination).expanduser().absolute()
    _directory(destination.parent)
    if destination.exists() or destination.is_symlink(): raise VerdugoError('La recuperación requiere un directorio nuevo')
    if not execute: return result | {'state': 'planned', 'services_enabled': 0, 'external_calls_made': False}
    destination.mkdir(mode=0o700)
    try:
        config = _config(source/'config.json')
        if backups._digest(source/'config.json') != expected['config.json']:
            raise VerdugoError('La configuración del respaldo cambió')
        # Restore is a separate offline workspace. Never carry forward provider/ingress activation.
        for cfg in config['tenants'].values():
            for key in ('services', 'ingress'):
                for service in cfg.get(key, {}).values(): service['enabled'] = False
        _write(destination/'config.json', config)
        state = destination/'estado.sqlite'
        with (source/'estado.sqlite3').open('rb') as stream:
            fd = os.open(state, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as target:
                shutil.copyfileobj(stream, target); target.flush(); os.fsync(target.fileno())
        # Verify copied bytes, then independently recheck pending work before changing approvals.
        if backups._digest(state) != expected['estado.sqlite3']:
            raise VerdugoError('La copia restaurada no coincide')
        backups.verify(state)
        with closing(sqlite3.connect(state)) as db:
            if any(pending(db).values()): raise VerdugoError('Conciliación offline requerida')
            db.execute('UPDATE plans SET approved_by=NULL,expires=NULL')
            db.commit()
        backups.verify(state)
        _write(destination/'recuperacion.json', {'version': __version__, 'restored_at': time.time(),
               'services_enabled': 0, 'approvals_cleared': True, 'external_calls_made': False})
        _sync_dir(destination); _sync_dir(destination.parent)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return {'state': 'restored_offline', 'saved_directory': str(destination), 'services_enabled': 0,
            'approvals_cleared': True, 'tokens_copied': False, 'external_calls_made': False,
            'runtime_profiles_restored': False, 'operator_review_required': True}


def readiness(engine, config_path, assets):
    checks = []
    def add(key, ok, label): checks.append({'id': key, 'ok': bool(ok), 'label': label})
    try: _config(Path(config_path).expanduser()); private = True
    except (OSError, VerdugoError): private = False
    add('private_config', private, 'Configuración privada y válida')
    try:
        backups._inspect(engine.state_path)
        valid = engine.db.execute('PRAGMA quick_check').fetchone()[0] == 'ok' and not engine.db.execute('PRAGMA foreign_key_check').fetchone()
    except (OSError, sqlite3.DatabaseError, VerdugoError): valid = False
    add('state_integrity', valid, 'Base de datos privada e íntegra')
    add('panel_built', (Path(assets)/'index.html').is_file(), 'Panel compilado')
    counts = pending(engine.db)
    add('reconciliation', not any(counts.values()), 'Sin ejecuciones inciertas ni trabajos pendientes')
    last_backup = None
    folder = Path(engine.state_path).parent/'respaldos.local'
    try:
        _directory(folder)
        candidates = sorted(folder.iterdir(), key=lambda p: p.name, reverse=True)
        # A damaged most recent set must not be concealed by an older healthy one.
        if candidates: last_backup = verify_set(candidates[0])
    except (OSError, ValueError, sqlite3.DatabaseError, VerdugoError): pass
    add('recent_backup', last_backup is not None and 0 <= time.time()-last_backup['created_at'] <= 86400,
        'Respaldo íntegro de las últimas 24 horas')
    return {'state': 'local_checks_passed' if all(c['ok'] for c in checks) else 'attention_required',
            'version': __version__, 'checks': checks, 'pending': counts,
            'last_backup_at': last_backup['created_at'] if last_backup else None,
            'scope': 'local_installation', 'live_verified': 0, 'external_calls_made': False,
            'commercial_results_verified': False, 'restoration_tested_on_this_host': False}
