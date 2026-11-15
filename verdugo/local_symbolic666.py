"""Bounded original polynomial algebra and in-memory graph reachability."""
import hashlib
import json
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'sympy': ('polynomial.check', 'sympy', '1.15.0.dev3540+gbad9365d7'),
         'rdflib': ('reachability.check', 'rdflib', '8.0.0a0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-symbolic666.json'
PACKAGE = 'lib/python3.12/site-packages'


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = checked(Path(runtime_profile.interpreter(service)).parent.parent, directory=True)
        record = next(r for r in json.loads(CONTRACT.read_text())['records'] if r['id']==service)
        digest = hashlib.sha256(CONTRACT.read_bytes() + str(root).encode())
        expected = {distribution: version}
        files = [{'path':f['installed_path'], 'sha256':f['sha256']}
                 for f in record['files'] if f['installed_path']] + record['generated_files']
        for dependency in record['dependencies']:
            expected[dependency['name']] = dependency['version']
            files += dependency['files']
        for entry in files:
            actual = hashlib.sha256(checked(root/PACKAGE/entry['path'], budget=8*1024*1024).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed symbolic source or dependency changed')
            digest.update(bytes.fromhex(actual))
        if runtime_profile.versions(service, list(expected)) != expected:
            raise VerdugoError('Symbolic distribution version differs')
        digest.update(checked(root/'bin/python', budget=64*1024*1024).read_bytes())
        digest.update(checked(root/'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, StopIteration, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown bounded symbolic operation')
    required = ('coefficients', 'points') if service=='sympy' else ('node_count', 'edges', 'start')
    try:
        fields(p, ('dataset', *required))
    except ValueError as exc:
        raise VerdugoError('Finite JSON symbolic values required') from exc
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic integer inputs supported')
    if service=='sympy':
        for key, size, lo, hi in [('coefficients',6,-20,20),('points',8,-10,10)]:
            values = p[key]
            if not isinstance(values,list) or not 1 <= len(values) <= size:
                raise VerdugoError('Symbolic input length exceeded')
            for value in values: integer(value,lo,hi)
    else:
        integer(p['node_count'],1,8); integer(p['start'],0,p['node_count']-1)
        if not isinstance(p['edges'],list) or len(p['edges'])>16:
            raise VerdugoError('At most sixteen synthetic edges supported')
        for edge in p['edges']:
            if not isinstance(edge,list) or len(edge)!=2:
                raise VerdugoError('An edge must contain two node indices')
            for node in edge: integer(node,0,p['node_count']-1)


def normalize(values):
    i = 0
    while i < len(values)-1 and values[i]==0: i += 1
    return values[i:]


def multiply(a,b):
    out = [0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b): out[i+j] += x*y
    return normalize(out)


def evaluate(values,x):
    result = 0
    for value in values: result = result*x + value
    return result


def polynomial(p):
    from sympy import Poly, Symbol
    coefficients = normalize(p['coefficients'])
    original = Poly.from_list(coefficients,Symbol('synthetic_x'),domain='ZZ')
    derivative = original.diff()
    values = [int(original.eval(x)) for x in p['points']]
    differentiated = [int(derivative.eval(x)) for x in p['points']]
    scalar_derivative = [v*(len(coefficients)-i-1) for i,v in enumerate(coefficients[:-1])] or [0]
    if (values != [evaluate(coefficients,x) for x in p['points']]
            or differentiated != [evaluate(scalar_derivative,x) for x in p['points']]):
        raise VerdugoError('Original algebra disagrees with scalar reference')
    content, factors = original.factor_list()
    reconstructed = [int(content)]
    for factor, multiplicity in factors:
        if type(multiplicity) is not int or not 1<=multiplicity<=5:
            raise VerdugoError('Unexpected original factor multiplicity')
        values_factor = [int(x) for x in factor.all_coeffs()]
        if not 2<=len(values_factor)<=6:
            raise VerdugoError('Unexpected original factor degree')
        for _ in range(multiplicity): reconstructed = multiply(reconstructed,values_factor)
    if normalize(reconstructed)!=coefficients:
        raise VerdugoError('Original factors do not reconstruct the input polynomial')
    return {'scope':'synthetic_univariate_integer_polynomial',
            'degree':None if coefficients==[0] else len(coefficients)-1,
            'evaluation_count':len(values),'evaluations':values,'derivative_evaluations':differentiated,
            'distinct_factors':len(factors),'factor_multiplicities':[m for _,m in factors],
            'independent_evaluation_verified':True,'independent_factor_product_verified':True,
            'irreducibility_independently_proven':False,'expression_strings_parsed':0,
            'predictions_made':0,'real_world_claim_verified':False}


def scalar_reachable(p):
    seen = {p['start']}
    while True:
        expanded = seen | {b for a,b in p['edges'] if a in seen}
        if expanded==seen: return sorted(seen)
        seen = expanded


def reachability(p):
    from rdflib import Graph, URIRef
    from rdflib.plugins.stores.memory import Memory
    nodes = [URIRef('urn:verdugo:synthetic:n'+str(i)) for i in range(p['node_count'])]
    predicate = URIRef('urn:verdugo:synthetic:edge')
    graph = Graph(store=Memory(), identifier=URIRef('urn:verdugo:synthetic:graph'),bind_namespaces='none')
    try:
        for a,b in p['edges']: graph.add((nodes[a],predicate,nodes[b]))
        actual_edges = {(nodes.index(a),nodes.index(b)) for a,_,b in graph.triples((None,predicate,None))}
        expected_edges = {tuple(edge) for edge in p['edges']}
        closure = list(graph.transitive_objects(nodes[p['start']],predicate))
        indices = sorted(nodes.index(node) for node in closure)
        if (actual_edges != expected_edges or len(graph)!=len(expected_edges)
                or len(closure)!=len(set(closure)) or indices!=scalar_reachable(p)):
            raise VerdugoError('Original graph differs from finite adjacency reference')
        return {'scope':'synthetic_in_memory_directed_graph','node_count':p['node_count'],
                'unique_edges':len(graph),'duplicate_edges':len(p['edges'])-len(graph),
                'reachable_indices':indices,'reachable_count':len(indices),'start_included':True,
                'independent_closure_verified':True,'remote_graphs_loaded':0,'sparql_queries_executed':0,
                'raw_rdf_payload_retained':False,'ontology_inference_verified':False}
    finally:
        graph.close()


def run(service,p):
    validate(service,SPECS[service][0],p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Original symbolic runtime is unavailable')
    result = polynomial(p) if service=='sympy' else reachability(p)
    return result | {'original_sdk':service,'sdk_version':SPECS[service][2],'dataset':'demo',
            'llm_calls':0,'model_weights_loaded':False,'autonomous_agent':False,
            'dry_run':True,'external_calls_made':False,'external_execution_authorized':False,
            'operator_approval_required':True,'approvals_granted':0,
            'business_outcome_proven':False,'live_verified':False}
