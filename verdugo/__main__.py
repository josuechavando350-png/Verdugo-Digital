import argparse
import json
from pathlib import Path
import sys
import tempfile
from .adapters import SPECS
from .catalog import catalog, graph
from .common import VerdugoError, encode, identifier
from .engine import Engine
from . import workflow, jobs, reconciliation
from .ingress import make_server
from .bridge import contact_bridge
from .diagnostics import doctor
from .mcp import serve


def read_json(value):
    content = Path(value[1:]).read_text() if value.startswith('@') else value
    if len(content.encode()) > 1024*1024: raise VerdugoError('Input exceeds 1 MiB')
    return json.loads(content)


def template(tenant):
    identifier(tenant)
    services = {}
    for item in catalog():
        sid = item['id']
        services[sid] = {'enabled': False, 'license_reviewed': False, 'version': None}
        if sid in SPECS:
            services[sid].update(base_url='https://example.invalid',
                token_env='VERDUGO_' + tenant.upper() + '_' + sid.upper().replace('-', '_') + '_TOKEN')
    services['chatwoot'].update(account_id=1, inbox_id=1, auth_mode='bearer', result_id_path='payload.contact.id')
    services['twenty'].update(workspace_id='REPLACE_WORKSPACE_ID', result_id_path='data.createPerson.id')
    services['langfuse']['username'] = 'REPLACE_LANGFUSE_PUBLIC_KEY'
    services['posthog']['project_id'] = 1
    services['listmonk']['username'] = 'verdugo-api'
    services['activepieces']['project_id'] = 'REPLACE_PROJECT_ID'
    services['prometheus']['allowed_queries'] = ['up']
    return {'tenants': {tenant: {'services': services, 'ingress': {}}}}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='verdugo', description='Verdugo Digital unified control plane')
    parser.add_argument('--config')
    parser.add_argument('--state', default='.state/verdugo.sqlite3')
    parser.add_argument('--tenant', default='nexus')
    parser.add_argument('--actor', default='local-operator')
    parser.add_argument('--role', choices=['operator', 'viewer', 'approver'], default='operator')
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('status', 'catalog', 'graph', 'mcp', 'demo'): sub.add_parser(name)
    p = sub.add_parser('init'); p.add_argument('--out', default='verdugo.local.json')
    p = sub.add_parser('events'); p.add_argument('--after', type=int, default=0)
    for name in ('plan', 'run', 'workflow', 'bridge'):
        p = sub.add_parser(name); p.add_argument('input', help='JSON text or @path.json')
        if name != 'plan': p.add_argument('--execute', action='store_true')
    p = sub.add_parser('doctor'); p.add_argument('--probe-id', default='configuration-check')
    p.add_argument('--execute', action='store_true')
    p = sub.add_parser('approve'); p.add_argument('key'); p.add_argument('fingerprint')
    p.add_argument('--ttl', type=int, default=600)
    p = sub.add_parser('approve-batch'); p.add_argument('input'); p.add_argument('--ttl', type=int, default=600)
    p = sub.add_parser('queue'); p.add_argument('--limit', type=int, default=50)
    p = sub.add_parser('job'); p.add_argument('job_id')
    p = sub.add_parser('job-plan'); p.add_argument('job_id')
    p = sub.add_parser('worker'); p.add_argument('--execute', action='store_true')
    p = sub.add_parser('job-resume'); p.add_argument('job_id'); p.add_argument('--execute', action='store_true')
    sub.add_parser('reconciliation-list')
    p = sub.add_parser('reconcile'); p.add_argument('input'); p.add_argument('--execute', action='store_true')
    p = sub.add_parser('ingress-local'); p.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    engine = None
    try:
        if args.cmd == 'init':
            with open(args.out, 'x') as f: f.write(json.dumps(template(args.tenant), indent=2)+'\n')
            print(encode({'created': args.out, 'registered': 100, 'enabled': 0})); return 0
        if args.cmd == 'catalog': print(encode(catalog())); return 0
        if args.cmd == 'graph': print(encode(graph(SPECS))); return 0
        if args.cmd == 'demo':
            with tempfile.TemporaryDirectory(prefix='verdugo-demo-') as directory:
                engine = Engine(Path(directory)/'demo.sqlite3')
                spec = json.loads((Path(__file__).parent.parent/'examples'/'demo.json').read_text())
                result = workflow.run(engine, spec, execute=True)
                print(encode({'synthetic_only': True, 'external_calls': 0, 'workflow': result}))
                return 0 if result['state'] == 'succeeded' else 1
        config = json.loads(Path(args.config).read_text()) if args.config else None
        engine = Engine(args.state, config, args.tenant, args.actor, args.role)
        if args.cmd == 'ingress-local':
            if args.state == ':memory:' or args.role != 'operator':
                raise VerdugoError('Local ingress requires persistent state and operator role')
            engine.close(); engine = None
            factory = lambda: Engine(args.state, config, args.tenant, args.actor, args.role)
            with make_server(factory, args.port) as server:
                print(encode({'local_acceptance_only': True, 'bind': server.server_address,
                              'public_deployment': False}), flush=True)
                server.serve_forever()
            return 0
        if args.cmd == 'mcp': serve(engine); return 0
        if args.cmd == 'status': result = engine.status()
        elif args.cmd == 'events': result = engine.events(args.after)
        elif args.cmd == 'queue': result = jobs.overview(engine, args.limit)
        elif args.cmd == 'job': result = jobs.get(engine, args.job_id)
        elif args.cmd == 'job-plan': result = jobs.plan(engine, args.job_id)['plan']
        elif args.cmd == 'worker': result = jobs.work(engine, args.execute)
        elif args.cmd == 'job-resume':
            result = jobs.resume(engine, args.job_id) if args.execute else {'state': 'planned', 'job': jobs.get(engine, args.job_id)}
        elif args.cmd == 'reconciliation-list': result = reconciliation.pending(engine)
        elif args.cmd == 'reconcile':
            result = reconciliation.confirm(engine, read_json(args.input)) if args.execute else {
                'state': 'planned', 'note': 'Human evidence not applied; --execute and approver role required'}
        elif args.cmd == 'approve': result = engine.approve(args.key, args.fingerprint, args.ttl)
        elif args.cmd == 'approve-batch':
            batch = read_json(args.input)
            if isinstance(batch, dict): batch = batch['approval_batch']
            result = engine.approve_many(batch, args.ttl)
        elif args.cmd == 'bridge': result = contact_bridge(engine, read_json(args.input), args.execute)
        elif args.cmd == 'doctor': result = doctor(engine, args.probe_id, args.execute)
        elif args.cmd == 'plan': result = engine.plan(read_json(args.input))
        elif args.cmd == 'run': result = engine.execute(read_json(args.input), args.execute)
        else: result = workflow.run(engine, read_json(args.input), args.execute)
        print(encode(result))
        return 1 if isinstance(result, dict) and result.get('state') in ('failed', 'uncertain', 'paused', 'awaiting_approval', 'incomplete', 'not_configured', 'blocked', 'dead', 'pending') else 0
    except (VerdugoError, ValueError, OSError, TypeError) as exc:
        print(encode({'error': str(exc)}), file=sys.stderr)
        return 2
    finally:
        if engine is not None: engine.close()


if __name__ == '__main__':
    raise SystemExit(main())
