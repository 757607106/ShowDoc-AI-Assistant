"""Connect native model clients to the configured origin and its validated address."""
import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlsplit
from functools import cached_property

import httpx

from governance.store import StoreError


def _model_address(host, port):
    host = host.rstrip('.').lower()
    entries = [item.strip().lower() for var in ('SSRF_WHITELIST', 'SSRF_WHITELIST_EXTRA')
               for item in os.getenv(var, '').split(',') if item.strip()]
    if host in entries or any(item.startswith('*.') and host.endswith(item[1:]) for item in entries):
        return host
    nets = [ipaddress.ip_network(item, strict=False) for item in entries if '/' in item]
    def listed(ip):
        return any(ip in net for net in nets)
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal and listed(literal):
        return host
    if literal or os.getenv('SSRF_DNS_WHITELIST_ONLY', '').lower() in ('true', '1'):
        raise StoreError('模型服务地址需要加入 SSRF_WHITELIST_EXTRA', 400)
    if (port in {22, 23, 25, 445, 3389, 5432, 3306, 6379, 27017, 9200, 2379, 2380, 8500, 4001}
            or host in ('localhost', 'kubernetes', 'kubernetes.default', 'kubernetes.default.svc', 'metadata.tencentyun.com')
            or host.endswith(('.local', '.localhost', '.internal', '.corp', '.lan', '.home', '.localdomain', '.svc.cluster.local', '.pod.cluster.local'))):
        raise StoreError('模型服务地址需要加入 SSRF_WHITELIST_EXTRA', 400)
    addresses = [ipaddress.ip_address(addr[4][0]) for addr in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]
    if not addresses or any((not ip.is_global or ip.is_multicast) and not listed(ip) for ip in addresses):
        raise StoreError('私有模型服务地址需要加入 SSRF_WHITELIST_EXTRA', 400)
    return str(addresses[0])


def validate_model_address(base_url):
    url = urlsplit(base_url)
    try:
        _model_address(url.hostname, url.port or (443 if url.scheme == 'https' else 80))
    except OSError as exc:
        raise StoreError('模型服务地址无法解析', 400) from exc


class ModelTransport(httpx.BaseTransport, httpx.AsyncBaseTransport):
    def __init__(self, base_url, http=httpx):
        self.http = http
        self.origin = http.URL(base_url)

    @cached_property
    def sync(self):
        return self.http.HTTPTransport()

    @cached_property
    def asynchronous(self):
        return self.http.AsyncHTTPTransport()

    def pinned(self, request):
        url = request.url
        if (url.scheme, url.netloc) != (self.origin.scheme, self.origin.netloc):
            raise StoreError('模型地址与配置的服务端点不一致', 400)
        address = _model_address(url.host, url.port or (443 if url.scheme == 'https' else 80))
        # Pin the dial target after DNS validation and keep TLS verification and Host on the configured name.
        return self.http.Request(request.method, url.copy_with(host=address), headers=request.headers, stream=request.stream,
                                 extensions={**request.extensions, 'sni_hostname': url.host})

    def handle_request(self, request):
        return self.sync.handle_request(self.pinned(request))

    async def handle_async_request(self, request):
        return await self.asynchronous.handle_async_request(await asyncio.to_thread(self.pinned, request))

    def close(self):
        if 'sync' in self.__dict__:
            self.sync.close()

    async def aclose(self):
        if 'asynchronous' in self.__dict__:
            await self.asynchronous.aclose()
