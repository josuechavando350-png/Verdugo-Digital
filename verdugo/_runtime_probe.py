"""Fixed metadata-only probe for an operator-provisioned dependency environment."""
from importlib import metadata
import json
import resource
import sys

resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
resource.setrlimit(resource.RLIMIT_FSIZE, (8192, 8192))


def guard(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind',
                 'socket.getaddrinfo', 'socket.gethostbyname'):
        raise PermissionError('No network in runtime metadata probe')


sys.addaudithook(guard)
result = {}
for distribution in sys.argv[1:]:
    try:
        result[distribution] = metadata.version(distribution)
    except metadata.PackageNotFoundError:
        result[distribution] = None
print(json.dumps(result))
