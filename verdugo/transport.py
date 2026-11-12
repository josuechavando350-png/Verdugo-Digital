"""HTTPS with pinned DNS resolution, no redirects/proxies, bounded response size."""
import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit
from .common import VerdugoError, encode
from . import marketing_reads

MAX_RESPONSE = 1024 * 1024


class TransportError(VerdugoError):
    pass


def resolve(host, port, allow_private=False, allow_loopback=False):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    for family, kind, proto, _, addr in addresses:
        ip = ipaddress.ip_address(addr[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        permitted = ip.is_global or (allow_loopback and ip.is_loopback) or (
            allow_private and ip.is_private and not ip.is_loopback
            and not ip.is_link_local and not ip.is_unspecified and not ip.is_reserved)
        if not permitted or ip.is_multicast or ip.is_link_local:
            raise TransportError('Destination address is not permitted')
    if not addresses:
        raise TransportError('No destination address')
    return addresses[0]


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, address, tls, timeout=10):
        super().__init__(host, port, timeout=timeout)
        self.address, self.tls = address, tls

    def connect(self):
        family, kind, proto, _, address = self.address
        sock = socket.socket(family, kind, proto)
        sock.settimeout(self.timeout)
        try:
            sock.connect(address)
            self.sock = ssl.create_default_context().wrap_socket(
                sock, server_hostname=self.host) if self.tls else sock
        except Exception:
            sock.close()
            raise


def send(request, cfg):
    p = request['public']
    u = urlsplit(p['url'])
    port = u.port or (443 if u.scheme == 'https' else 80)
    connection = None
    try:
        addr = resolve(u.hostname, port,
                       cfg.get('allow_private_network') is True,
                       cfg.get('allow_local_http') is True)
        connection = PinnedHTTP(u.hostname, port, addr, u.scheme == 'https')
        path = u.path + ('?' + u.query if u.query else '')
        if (p['service'], p['operation']) == ('matomo', 'visits.summary'):
            data = marketing_reads.form_bytes(request)
        else:
            data = encode(p['body']).encode() if p['body'] is not None else None
        connection.request(p['method'], path, body=data, headers=request['headers'])
        response = connection.getresponse()
        # No retries for mutations. No redirect following, including same-host redirects.
        if not 200 <= response.status < 300:
            raise TransportError('Upstream HTTP %s; response body omitted' % response.status)
        if p['service'] in marketing_reads.SPECS and response.status != 200:
            raise TransportError('Marketing reads require a synchronous HTTP 200 response')
        if request['mutates'] and response.status not in (200, 201):
            raise TransportError('Write response is not a completed synchronous operation')
        if response.getheader('Content-Encoding', 'identity') != 'identity':
            raise TransportError('Compressed responses are not accepted')
        body = response.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            raise TransportError('Upstream response exceeds 1 MiB')
        if not body: return {'http_status': response.status}
        try:
            return json.loads(body)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise TransportError('Upstream did not return valid bounded JSON') from exc
    except TransportError:
        raise
    except (OSError, ValueError, http.client.HTTPException) as exc:
        # Never expose upstream URLs, headers or arbitrary exception strings with secrets.
        raise TransportError('Upstream transport failed (%s)' % type(exc).__name__) from exc
    finally:
        if connection is not None: connection.close()
