"""Two bounded calls to unmodified original R sources; never an R console."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from .common import VerdugoError, fields
from .local_native import checked

SPECS = {
    'pricesensitivitymeter': ('prices.survey', 'bundled-r:pricesensitivitymeter', '8188de1e95fa0f407073677f6f88baec2f43c8d4'),
    'robyn': ('media.transform', 'bundled-r:robyn', 'aab4226ed5e40196cdbd82ff7fbbff55e91e1f58'),
}
ENV = 'VERDUGO_R_ROOT'
ROOT = Path(__file__).with_name('vendor')
WORKER = Path(__file__).with_name('_r_worker.R')
CONTRACT = Path(__file__).with_name('r_contract.json')
PRICES = ('toocheap', 'cheap', 'expensive', 'tooexpensive')


def contract():
    return json.loads(CONTRACT.read_text())


def root():
    value = os.getenv(ENV)
    if (not value or not Path(value).is_absolute() or '..' in Path(value).parts
            or any(c in value for c in ('\x00', '\n', '\r'))):
        raise VerdugoError('An absolute administrator R runtime is required')
    return checked(Path(value), directory=True)


def source_path(service):
    folder = checked(ROOT / service, directory=True)
    for name, digest in contract()['sources'][service].items():
        raw = checked(folder / name, budget=256 * 1024).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise VerdugoError('Pinned original R source or license changed')
    return folder


def runtime_state(service):
    operation, distribution, expected = SPECS[service]
    present, binding = False, None
    try:
        home = root()
        source_path(service)
        h = hashlib.sha256(str(home).encode() + CONTRACT.read_bytes())
        for name, digest in contract()['runtime_files'].items():
            raw = checked(home / name, budget=64 * 1024 * 1024).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise VerdugoError('Pinned R runtime changed')
            h.update(name.encode()); h.update(bytes.fromhex(digest))
        if not os.access(home / 'usr/lib/R/bin/exec/R', os.X_OK):
            raise VerdugoError('R interpreter is not executable')
        binding, present = h.hexdigest(), True
    except (OSError, ValueError, KeyError, VerdugoError):
        pass
    return {'distribution': distribution, 'distribution_kind': 'bundled-original-r-source',
            'expected': expected, 'installed': expected if present else None,
            'version_matches': present, 'extra_distributions': {}, 'operation': operation,
            'execution_verified': False, 'runtime_binding': binding}


def validate(service, operation, p):
    from .local_runtime import finite
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unsupported original R operation')
    required = ('currency', 'responses') if service == 'pricesensitivitymeter' else ('spend', 'theta', 'alpha', 'gamma')
    try:
        fields(p, ('dataset', *required))
    except (TypeError, ValueError) as exc:
        raise VerdugoError('Finite JSON-compatible R input is required') from exc
    if p['dataset'] not in ('demo', 'real'):
        raise VerdugoError('An explicit dataset is required')
    if service == 'pricesensitivitymeter':
        if p['currency'] not in ('MXN', 'USD', 'EUR'):
            raise VerdugoError('An explicit supported currency is required')
        rows = p['responses']
        if not isinstance(rows, list) or not 5 <= len(rows) <= 100:
            raise VerdugoError('Provide 5..100 supplied survey responses')
        for row in rows:
            fields(row, PRICES)
            values = [finite(row[key], 0, 10**9) for key in PRICES]
            if any(a >= b for a, b in zip(values, values[1:])):
                raise VerdugoError('Survey price thresholds must be strictly increasing')
    else:
        if not isinstance(p['spend'], list) or not 2 <= len(p['spend']) <= 100:
            raise VerdugoError('Provide 2..100 nonnegative spending observations')
        for value in p['spend']:
            finite(value, 0, 10**9)
        if not any(p['spend']):
            raise VerdugoError('At least one positive spend is required')
        finite(p['theta'], 0, 0.99); finite(p['alpha'], 0.1, 10); finite(p['gamma'], 0.01, 1)


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise ValueError('R runtime changed')
    home, source = root(), source_path(service)
    if service == 'pricesensitivitymeter':
        keys, rows = PRICES, p['responses']
    else:
        keys = ('spend', 'theta', 'alpha', 'gamma')
        rows = [dict(spend=v, theta=p['theta'], alpha=p['alpha'], gamma=p['gamma']) for v in p['spend']]
    with open('input.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
    r_home = home / 'usr/lib/R'
    env = {'PATH': os.defpath, 'HOME': os.getcwd(), 'TMPDIR': os.getcwd(), 'LANG': 'C.UTF-8',
           'R_HOME': str(r_home), 'R_DEFAULT_PACKAGES': 'utils,stats,methods',
           'LD_LIBRARY_PATH': str(r_home / 'lib') + ':' + str(home / 'usr/lib/x86_64-linux-gnu'),
           'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run([str(r_home / 'bin/exec/R'), '--vanilla', '--slave', '-f', str(WORKER),
                               '--args', service, str(source)],
                              stdout=out, stderr=err, env=env, timeout=45, check=False, close_fds=True)
        if proc.returncode:
            raise ValueError('Original R operation failed')
    output = checked(Path('output.csv'), budget=64 * 1024).read_text()
    result = list(csv.DictReader(output.splitlines()))
    if service == 'pricesensitivitymeter':
        names = ('sample', 'invalid', 'lower', 'upper', 'idp', 'opp')
        if len(result) != 1 or set(result[0]) != set(names):
            raise ValueError('Unexpected original survey output')
        values = {key: float(result[0][key]) for key in names}
        if not all(math.isfinite(v) and 0 <= v <= 10**9 for v in values.values()):
            raise ValueError('Nonfinite original survey output')
        if values['sample'] != len(rows) or values['invalid'] != 0:
            raise ValueError('Original survey rejected supplied rows')
        return {'responses': len(rows), 'currency': p['currency'],
                'acceptable_range': {'lower': values['lower'], 'upper': values['upper']},
                'indifference_point': values['idp'], 'optimal_price_point': values['opp'],
                'method': 'unweighted Van Westendorp; original range; minimum intersection',
                'scope': 'descriptive intersections in supplied survey; OPP is not a revenue optimum',
                'representative_sample_verified': False, 'revenue_optimum_verified': False}
    if len(result) != len(rows) or any(set(row) != {'adstock', 'saturation'} for row in result):
        raise ValueError('Unexpected original media output')
    adstock = [float(row['adstock']) for row in result]
    saturation = [float(row['saturation']) for row in result]
    if (not all(math.isfinite(v) and 0 <= v <= 10**11 for v in adstock)
            or not all(math.isfinite(v) and 0 <= v <= 1 for v in saturation)):
        raise ValueError('Nonfinite original media output')
    return {'adstock': adstock, 'saturation': saturation, 'periods': len(rows),
            'parameters_supplied': True, 'model_fitted': False,
            'causal_effect_demonstrated': False, 'budget_optimized': False}
