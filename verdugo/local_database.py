"""Fixed operations against original ephemeral servers on private Unix sockets.

An administrator can select authenticated 127.0.0.1-only TCP when the host
does not support Unix sockets. Operation callers never choose a destination.

SQLite remains the only durable product state. No network host, SQL, Cypher,
server option, database path or command can be supplied by an operation caller.
"""
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

from .common import VerdugoError, fields, identifier, integer
from .local_native import checked

SPECS = {
    'valkey': ('cache.match', 'native-valkey', 'c98c0e2e6c271a24c829d17b2ed94d64c576c33f'),
    'postgres': ('campaigns.aggregate', 'native-postgres', '18.7'),
    'pgvector': ('vectors.rank', 'native-pgvector', '66accb3af6705ea9975a33f6704f1cde50d99447'),
    'apache-age': ('graph.degrees', 'native-age', '8c7e44fd2a525dedfd3d4e8168921442eb4fce2f'),
}
ENV = 'VERDUGO_DATABASE_ROOT'
LOOPBACK_ENV = 'VERDUGO_DATABASE_LOOPBACK'
PG_ARCHIVE_SHA = '441dfae4280cae3e0425e5f876f80559fb0731c140f1aae22b3e5a54d0411bfd'
MANDATORY = {'valkey': {'bin/valkey-server', 'bin/valkey-cli'},
             'postgres': {'bin/postgres', 'bin/initdb', 'bin/pg_ctl', 'bin/psql', 'share/postgresql/postgres.bki'},
             'pgvector': {'lib/postgresql/vector.so', 'share/postgresql/extension/vector.control'},
             'apache-age': {'lib/postgresql/age.so', 'share/postgresql/extension/age.control'}}


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts
            or any(c in value for c in ('\x00', '\n', '\r'))):
        raise VerdugoError('An absolute administrator database runtime is required')
    return checked(Path(value), directory=True)


def loopback():
    value = os.getenv(LOOPBACK_ENV, '0')
    if value not in ('0', '1'):
        raise VerdugoError('Database loopback mode is an explicit administrator 0/1 setting')
    return value == '1'


def runtime_state(service):
    operation, distribution, expected = SPECS[service]
    present, binding = False, None
    try:
        home = root()
        raw = checked(home / 'manifest.json', budget=1024*1024).read_bytes()
        manifest = json.loads(raw)
        groups = ['postgres', service] if service in ('pgvector', 'apache-age') else [service]
        h = hashlib.sha256(str(home).encode() + raw + str(loopback()).encode())
        for group in groups:
            record = manifest['programs'][group]
            if record['source_version'] != SPECS[group][2] or record['source_dirty'] is not False:
                raise VerdugoError('Database runtime provenance mismatch')
            if group == 'postgres' and record['archive_sha256'] != PG_ARCHIVE_SHA:
                raise VerdugoError('PostgreSQL archive provenance mismatch')
            files = record['files']
            if not isinstance(files, dict) or not 1 <= len(files) <= 5000 or not MANDATORY[group] <= set(files):
                raise VerdugoError('Incomplete database runtime manifest')
            for name, digest in sorted(files.items()):
                if (not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts
                        or not name.startswith(('bin/', 'lib/', 'share/'))):
                    raise VerdugoError('Invalid runtime manifest path')
                path = checked(home / name, budget=128*1024*1024)
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    raise VerdugoError('Database runtime binary or data changed')
                h.update(name.encode()); h.update(bytes.fromhex(digest))
        binding, present = h.hexdigest(), True
    except (OSError, KeyError, TypeError, ValueError, VerdugoError):
        pass
    return {'distribution': distribution, 'distribution_kind': 'original-native-server',
            'expected': expected, 'installed': expected if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    from .local_runtime import finite, validate as base
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported fixed database operation')
    if service == 'postgres':
        return base('duckdb', 'campaigns.aggregate', p)
    required = {'valkey': ('entries', 'lookup'), 'pgvector': ('rows', 'query', 'limit'),
                'apache-age': ('nodes', 'edges')}[service]
    try:
        fields(p, ('dataset', *required))
    except (TypeError, ValueError) as exc:
        raise VerdugoError('Finite JSON-compatible database input required') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')
    if service == 'valkey':
        if not isinstance(p['entries'], list) or not 1 <= len(p['entries']) <= 50:
            raise VerdugoError('Provide 1..50 cache entries')
        ids = []
        for row in p['entries']:
            fields(row, ('id', 'value')); identifier(row['id']); finite(row['value'], -1e9, 1e9)
            ids.append(row['id'])
        if len(set(ids)) != len(ids):
            raise VerdugoError('Duplicate cache key')
        if not isinstance(p['lookup'], list) or not 1 <= len(p['lookup']) <= 50:
            raise VerdugoError('Provide 1..50 lookup identifiers')
        for value in p['lookup']:
            identifier(value)
    elif service == 'pgvector':
        if not isinstance(p['rows'], list) or not 1 <= len(p['rows']) <= 100:
            raise VerdugoError('Provide 1..100 vectors')
        ids = []
        vectors = [p['query']]
        for row in p['rows']:
            fields(row, ('id', 'vector')); identifier(row['id']); ids.append(row['id']); vectors.append(row['vector'])
        if len(set(ids)) != len(ids):
            raise VerdugoError('Duplicate vector identifier')
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != 3:
                raise VerdugoError('Only three-dimensional vectors are supported')
            for value in vector:
                finite(value, -1000, 1000)
        integer(p['limit'], 1, min(len(ids), 20))
    else:
        if not isinstance(p['nodes'], list) or not 1 <= len(p['nodes']) <= 30:
            raise VerdugoError('Provide 1..30 graph nodes')
        for value in p['nodes']:
            identifier(value)
        if len(set(p['nodes'])) != len(p['nodes']):
            raise VerdugoError('Duplicate graph node')
        if not isinstance(p['edges'], list) or len(p['edges']) > 100:
            raise VerdugoError('At most 100 directed graph edges are supported')
        seen = set()
        for row in p['edges']:
            fields(row, ('source', 'target'))
            if row['source'] not in p['nodes'] or row['target'] not in p['nodes']:
                raise VerdugoError('Graph edge references an unknown node')
            edge = (row['source'], row['target'])
            if edge in seen:
                raise VerdugoError('Duplicate graph edge')
            seen.add(edge)


def native(home, binary, args, env, data=None, timeout=35):
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run([str(home / 'bin' / binary), *args], input=data, stdout=out,
                              stderr=err, env=env, timeout=timeout, check=False, close_fds=True)
        out.seek(0); raw = out.read(1024*1024+1)
        if proc.returncode or len(raw) > 1024*1024:
            raise ValueError('Original database command failed')
        return raw


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise ValueError('Database runtime changed')
    home = root()
    env = {'PATH': str(home / 'bin') + ':' + os.defpath, 'HOME': os.getcwd(), 'TMPDIR': os.getcwd(),
           'LANG': 'C.UTF-8', 'LD_LIBRARY_PATH': str(home / 'lib'), 'PGCONNECT_TIMEOUT': '5'}
    if service == 'valkey':
        return cache(home, env, p)
    return postgres(home, env, service, p)


def cache(home, env, p):
    socket = str(Path.cwd() / 'cache.sock')
    tcp = loopback()
    port, password = 32768 + secrets.randbelow(32768), secrets.token_urlsafe(32)
    settings = ['port ' + str(port if tcp else 0), 'bind 127.0.0.1', 'protected-mode yes',
                'save ""', 'appendonly no', 'maxmemory 33554432', 'maxmemory-policy noeviction']
    if tcp:
        settings += ['requirepass ' + password]
        env = dict(env, VALKEYCLI_AUTH=password)
    else:
        settings += ['unixsocket ' + socket, 'unixsocketperm 700']
    config = Path('cache.conf'); config.write_text('\n'.join(settings)+'\n'); config.chmod(0o600)
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen([str(home/'bin/valkey-server'), str(config)],
            stdout=log, stderr=log, env=env, close_fds=True)
        try:
            deadline = time.monotonic() + 5
            args = ['--json', '-h', '127.0.0.1', '-p', str(port)] if tcp else ['--json', '-s', socket]
            while True:
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise ValueError('Temporary Valkey did not start')
                try:
                    if json.loads(native(home, 'valkey-cli', [*args, 'PING'], env, timeout=2)) == 'PONG':
                        break
                except (ValueError, subprocess.TimeoutExpired):
                    pass
                time.sleep(0.025)
            pairs = [v for row in p['entries'] for v in ('vd:' + row['id'], json.dumps(row['value']))]
            if json.loads(native(home, 'valkey-cli', [*args, 'MSET', *pairs], env)) != 'OK':
                raise ValueError('Original cache rejected input')
            values = json.loads(native(home, 'valkey-cli', [*args, 'MGET', *['vd:'+v for v in p['lookup']]], env))
            if not isinstance(values, list) or len(values) != len(p['lookup']):
                raise ValueError('Original cache result shape changed')
            results = [None if v is None else float(v) for v in values]
            if not all(v is None or math.isfinite(v) and -1e9 <= v <= 1e9 for v in results):
                raise ValueError('Original cache returned invalid data')
            return {'matches': results, 'hits': sum(v is not None for v in results),
                    'misses': sum(v is None for v in results), 'entries': len(p['entries']),
                    'persistent_cache_created': False, 'tcp_listener_enabled': tcp,
                    'listener_scope': 'authenticated_loopback' if tcp else 'private_unix_socket'}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()


def _csv(rows):
    out = io.StringIO(); writer = csv.writer(out, lineterminator='\n'); writer.writerows(rows)
    return out.getvalue() + '\\.\n'


def postgres(home, env, service, p):
    data = Path.cwd() / 'database'
    sockets = Path.cwd() / 'sockets'; sockets.mkdir(mode=0o700)
    tcp = loopback()
    port, password = 32768 + secrets.randbelow(32768), secrets.token_urlsafe(32)
    passfile = Path('database-password'); passfile.write_text(password+'\n'); passfile.chmod(0o600)
    auth = ['-A', 'scram-sha-256', '--pwfile='+str(passfile)] if tcp else ['-A', 'trust']
    native(home, 'initdb', ['-D', str(data), '-U', 'verdugo', *auth, '--no-locale', '--encoding=UTF8', '--no-sync'], env)
    if tcp:
        env = dict(env, PGPASSWORD=password)
    # Startup configuration is first-party fixed text, not caller SQL or flags.
    address = '127.0.0.1' if tcp else ''
    socket_path = '' if tcp else str(sockets)
    (data/'postgresql.conf').write_text("listen_addresses = '"+address+"'\nunix_socket_directories = '"+socket_path+
        "'\nport = "+str(port if tcp else 5432)+"\nunix_socket_permissions = 0700\nshared_buffers = '16MB'\nmax_connections = 5\n"
        "fsync = off\nlogging_collector = off\n")
    # pg_ctl start calls setsid(), escaping Engine's process-group cleanup.
    # Spawn postmaster directly in the worker's group instead. PostgreSQL child
    # processes also monitor postmaster death through their native death pipe.
    log = open('postgres.log', 'wb')
    server = subprocess.Popen([str(home/'bin/postgres'), '-D', str(data)],
                              stdout=log, stderr=log, env=env, close_fds=True)
    try:
        deadline = time.monotonic() + 10
        while True:
            pid_file = data / 'postmaster.pid'
            lines = pid_file.read_text().splitlines() if pid_file.exists() else []
            if lines and lines[-1].strip() == 'ready':
                break
            if server.poll() is not None or time.monotonic() > deadline:
                raise ValueError('Temporary PostgreSQL did not become ready')
            time.sleep(0.025)
        sql, variables = query(service, p)
        connection = ['-h', '127.0.0.1', '-p', str(port)] if tcp else ['-h', str(sockets)]
        raw = native(home, 'psql', ['-X', '-q', '-w', '-A', '-t', *connection, '-U', 'verdugo', '-d', 'postgres',
            '--set=ON_ERROR_STOP=1', *variables], env, sql.encode())
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError('Original database returned an unexpected result')
        if service == 'postgres':
            result['currency'] = p['currency']
        return result | {'temporary_database': True, 'tcp_listener_enabled': tcp,
                         'listener_scope': 'authenticated_loopback' if tcp else 'private_unix_socket',
                         'persistent_database_created': False}
    finally:
        try:
            if server.poll() is None:
                native(home, 'pg_ctl', ['-D', str(data), '-m', 'immediate', '-w', '-t', '10', 'stop'], env)
        finally:
            if server.poll() is None:
                server.kill()
            server.wait(); log.close()


def query(service, p):
    if service == 'postgres':
        sql = ('CREATE TABLE campaigns(channel text, spend bigint, revenue bigint, leads bigint, conversions bigint);\n'
               'COPY campaigns FROM STDIN WITH (FORMAT csv);\n')
        sql += _csv([[r['channel'], r['spend_minor'], r['revenue_minor'], r['leads'], r['conversions']] for r in p['rows']])
        sql += ("SELECT json_build_object('channels', json_agg(row_to_json(c)), 'bank_reconciled', false) FROM "
                '(SELECT channel, sum(spend) AS spend_minor, sum(revenue) AS revenue_minor, '
                'sum(leads) AS leads, sum(conversions) AS conversions FROM campaigns GROUP BY channel ORDER BY channel) c;\n')
        return sql, []
    if service == 'pgvector':
        sql = 'CREATE EXTENSION vector;\nCREATE TABLE items(id text, embedding vector(3));\nCOPY items FROM STDIN WITH (FORMAT csv);\n'
        sql += _csv([[row['id'], json.dumps(row['vector'])] for row in p['rows']])
        sql += ("SELECT json_build_object('matches', json_agg(row_to_json(m)), 'metric', 'l2', 'semantic_relevance_verified', false) "
                "FROM (SELECT id, embedding <-> :'query_vector'::vector AS distance FROM items "
                "ORDER BY distance, id LIMIT :'row_limit'::integer) m;\n")
        return sql, ['--set=query_vector='+json.dumps(p['query']), '--set=row_limit='+str(p['limit'])]
    # Cypher is fixed. JSON values cross a PostgreSQL parameter boundary;
    # no supplied string is interpolated into executable SQL/Cypher.
    sql = ("CREATE EXTENSION age;\nLOAD 'age';\nSET search_path = ag_catalog, public;\n"
           "SELECT create_graph('supplied_graph') IS NOT NULL AS setup_result \\gset\n"
           "PREPARE add_nodes(agtype) AS SELECT * FROM cypher('supplied_graph', $$ UNWIND $nodes AS node CREATE (:Item {name: node}) $$, $1) AS (v agtype);\n"
           "EXECUTE add_nodes(:'nodes_json'::agtype);\n"
           "PREPARE add_edges(agtype) AS SELECT * FROM cypher('supplied_graph', $$ UNWIND $edges AS edge MATCH (a:Item), (b:Item) WHERE a.name = edge.source AND b.name = edge.target CREATE (a)-[:LINK]->(b) $$, $1) AS (v agtype);\n"
           "EXECUTE add_edges(:'edges_json'::agtype);\n"
           "SELECT json_build_object('nodes', json_agg(json_build_object('id', n::text, 'out_degree', degree::text::integer)), 'external_graph_verified', false) "
           "FROM cypher('supplied_graph', $$ MATCH (a:Item) OPTIONAL MATCH (a)-[r:LINK]->() RETURN a.name, count(r) ORDER BY a.name $$) AS (n agtype, degree agtype);\n")
    return sql, ['--set=nodes_json='+json.dumps({'nodes':p['nodes']}), '--set=edges_json='+json.dumps({'edges':p['edges']})]
