"""Original bitsandbytes CPU float32 blockwise quantization diagnostics."""
import hashlib
import json
import math
from pathlib import Path

from .common import VerdugoError, fields, integer
from .local_native import checked
from . import runtime_profile

SPECS = {'bitsandbytes': ('quantization.check', 'bitsandbytes', '0.50.3.dev0')}
CONTRACT = Path(__file__).resolve().parents[1] / 'sources/contracts-quant666.json'
RECEIPT = 'share/verdugo-bitsandbytes/build.json'
PACKAGE = 'lib/python3.12/site-packages'
NATIVE = PACKAGE + '/bitsandbytes/libbitsandbytes_cpu.so'


def home():
    return checked(Path(runtime_profile.interpreter('bitsandbytes')).parent.parent, directory=True)


def verify_build(root, record):
    raw = checked(root / RECEIPT, budget=65536).read_bytes()
    receipt = json.loads(raw)
    if (receipt.get('schema') != 'verdugo.bitsandbytes666.operator-build.v1' or
            any(receipt.get(key) != record[key] for key in
                ('commit', 'archive_sha256', 'build_tools', 'torch_version', 'build_environment'))):
        raise VerdugoError('bitsandbytes source build receipt mismatch')
    package = checked(root / PACKAGE / 'bitsandbytes', directory=True)
    if {p.name for p in package.glob('*.so')} != {'libbitsandbytes_cpu.so'}:
        raise VerdugoError('Unexpected alternate bitsandbytes extension')
    native = checked(root / NATIVE, budget=64*1024*1024).read_bytes()
    actual = hashlib.sha256(native).hexdigest()
    if actual != receipt.get('native_sha256'):
        raise VerdugoError('Compiled bitsandbytes artifact changed')
    digest = hashlib.sha256(raw + CONTRACT.read_bytes() + bytes.fromhex(actual))
    for entry in record['files']:
        if entry['installed_path']:
            actual = hashlib.sha256(checked(root / PACKAGE / entry['installed_path']).read_bytes()).hexdigest()
            if actual != entry['sha256']:
                raise VerdugoError('Installed bitsandbytes interface differs from original source')
            digest.update(bytes.fromhex(actual))
    return digest.hexdigest()


def runtime_state(service):
    operation, distribution, version = SPECS[service]
    present, binding = False, None
    try:
        root = home(); record = json.loads(CONTRACT.read_text())
        artifacts = verify_build(root, record)
        if runtime_profile.versions(service, [distribution, 'torch']) != {distribution: version, 'torch': record['torch_version']}:
            raise VerdugoError('bitsandbytes distribution version mismatch')
        digest = hashlib.sha256(str(root).encode() + artifacts.encode())
        digest.update(checked(root / 'bin/python', budget=64*1024*1024).read_bytes())
        digest.update(checked(root / 'pyvenv.cfg', budget=16384).read_bytes())
        binding, present = digest.hexdigest(), True
    except (OSError, ValueError, KeyError, TypeError, VerdugoError):
        pass
    return {'distribution': distribution, 'expected': version, 'installed': version if present else None,
        'version_matches': present, 'extra_distributions': {}, 'operation': operation,
        'execution_verified': False, 'runtime_binding': binding}



def validate(service, operation, p):
    if service not in SPECS or operation != SPECS[service][0]:
        raise VerdugoError('Unknown fixed quantization operation')
    fields(p, ('dataset', 'values'))
    if p['dataset'] != 'demo':
        raise VerdugoError('Only synthetic numeric vectors supported')
    if not isinstance(p['values'], list) or not 1 <= len(p['values']) <= 512:
        raise VerdugoError('One to 512 bounded integers required')
    for value in p['values']:
        integer(value, -1000, 1000)


def run(service, p):
    validate(service, SPECS[service][0], p)
    if not runtime_state(service)['version_matches']:
        raise VerdugoError('Reviewed original bitsandbytes build unavailable')
    import importlib.metadata
    import platform
    import struct
    if platform.machine() != 'x86_64':
        raise VerdugoError('Reviewed CPU build requires Linux x86_64')
    flags = [set(line.partition(':')[2].split()) for line in Path('/proc/cpuinfo').read_text().splitlines()
             if line.startswith('flags')]
    if not flags or any(not {'avx2','fma','f16c','bmi1','bmi2'} <= f or not {'abm','lzcnt'} & f for f in flags):
        raise VerdugoError('Required CPU instruction set unavailable')
    if importlib.metadata.entry_points(group='bitsandbytes.backends'):
        raise VerdugoError('Unreviewed optional backend entry points present')
    import torch
    if torch.__version__ != '2.9.1+cpu' or torch.version.cuda or torch.version.hip or torch._C._has_xpu:
        raise VerdugoError('Reviewed CPU-only Torch required')
    torch.set_num_threads(1)
    from bitsandbytes import functional as functional, cextension
    if (type(cextension.lib) is not cextension.BNBNativeLibrary or
            Path(cextension.lib._lib._name).resolve() != (home() / NATIVE).resolve() or
            not hasattr(cextension.lib._lib, 'cquantize_blockwise_cpu_fp32') or
            not hasattr(cextension.lib._lib, 'cdequantize_blockwise_cpu_fp32')):
        raise VerdugoError('Original CPU native library unavailable')
    source = torch.tensor(p['values'], dtype=torch.float32, device='cpu')
    packed, state = functional.quantize_blockwise(source, blocksize=64, nested=False)
    restored = functional.dequantize_blockwise(packed, state)
    count = source.numel(); blocks = (count + 63)//64
    if (packed.dtype != torch.uint8 or restored.dtype != torch.float32 or
            packed.shape != source.shape or restored.shape != source.shape or
            state.absmax.numel() != blocks or state.code.numel() != 256 or
            state.blocksize != 64 or state.nested or
            any(x.device.type != 'cpu' for x in (packed, restored, state.absmax, state.code)) or
            not torch.isfinite(restored).all().item()):
        raise VerdugoError('Unexpected original blockwise result')
    scales = state.absmax.tolist(); codes = state.code.tolist()
    expected_scales = [max(abs(x) for x in p['values'][i:i+64]) for i in range(0,count,64)]
    if scales != expected_scales or not all(math.isfinite(x) for x in codes):
        raise VerdugoError('Original block scales differ from integer reference')
    reference = [struct.unpack('f', struct.pack('f', codes[index]*scales[i//64]))[0]
                 for i,index in enumerate(packed.tolist())]
    actual = restored.tolist()
    reference_error = max(abs(x-y) for x,y in zip(actual,reference))
    if reference_error > 1e-4:
        raise VerdugoError('Native reconstruction differs from scalar codebook reference')
    errors = [abs(x-y) for x,y in zip(actual,p['values'])]
    array_bytes = packed.numel()*packed.element_size()
    scale_bytes = state.absmax.numel()*state.absmax.element_size()
    code_bytes = state.code.numel()*state.code.element_size()
    total = array_bytes + scale_bytes + code_bytes
    original = source.numel()*source.element_size()
    return {'value_count': count, 'block_count': blocks, 'block_size': 64,
        'original_array_bytes': original, 'quantized_array_bytes': array_bytes,
        'scale_array_bytes': scale_bytes, 'codebook_array_bytes': code_bytes,
        'total_representation_array_bytes': total, 'array_bytes_saved': original-total,
        'object_and_allocator_overhead_included': False,
        'max_absolute_reconstruction_error': max(errors),
        'mean_absolute_reconstruction_error': sum(errors)/count,
        'scalar_reconstruction_max_error': reference_error, 'block_scales_verified': True,
        'native_cpu_path_used': True, 'model_weights_loaded': False,
        'model_accuracy_measured': False, 'speed_benchmarked': False, 'quality_calibrated': False,
        'original_sdk': service, 'sdk_version': SPECS[service][2],
        'source_commit': json.loads(CONTRACT.read_text())['commit'],
        'native_artifact_receipt_verified': True, 'reproducible_binary_build_proven': False,
        'dataset': 'demo', 'dry_run': True, 'llm_calls': 0, 'autonomous_agent': False,
        'external_calls_made': False, 'external_execution_authorized': False,
        'operator_approval_required': True, 'approvals_granted': 0,
        'business_outcome_proven': False}
