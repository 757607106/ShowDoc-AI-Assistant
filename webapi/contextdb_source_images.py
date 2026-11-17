"""Serve only images explicitly referenced by an authorized Markdown or HTML source."""
import hashlib
import base64
import binascii
from html import unescape
from ipaddress import ip_address
import re
import socket
import tempfile
from urllib.parse import unquote_to_bytes, urljoin, urlsplit

from bs4 import BeautifulSoup
from flask import send_file
import marko
import requests
from requests.adapters import HTTPAdapter

from governance.store import StoreError
from webapi.contextdb_preview import _source_detail

MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
SOURCE_FORMATS = {'md', 'markdown', 'mdown', 'mkd', 'mdx', 'html', 'htm', 'xhtml'}


def _read_body(response, limit):
    data = bytearray()
    for part in response.iter_content(chunk_size=64 * 1024):
        data.extend(part)
        if len(data) > limit:
            raise StoreError('源文件或图片过大，请下载原件查看', 413)
    return bytes(data)


def source_images(client, document_id, knowledge_base_id=None):
    detail = _source_detail(client, document_id, knowledge_base_id)
    extension = (detail.get('name') or '').rsplit('.', 1)[-1].lower()
    if extension not in SOURCE_FORMATS:
        return {}
    url = detail.get('download_url')
    if not isinstance(url, str) or urlsplit(url).scheme != 'https':
        raise StoreError('官方未返回可读取的原件', 409)
    try:
        with requests.get(url, headers={'Accept-Encoding': 'identity'}, stream=True,
                          timeout=client.timeout, allow_redirects=False) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise StoreError('原件暂时无法读取，请刷新重试', 502)
            text = _read_body(response, MAX_SOURCE_BYTES).decode('utf-8-sig')
    except UnicodeDecodeError:
        raise StoreError('源文件不是可解析的 UTF-8 文本，请下载原件查看', 415) from None
    except requests.RequestException:
        raise StoreError('原件暂时无法读取，请刷新重试', 502) from None
    base = (detail.get('metadata') or {}).get('url') or ''
    return extract_source_images(text, extension, base if isinstance(base, str) else '')


def extract_source_images(text, extension, base=''):
    images = {}

    def add(value, description='', decode_entities=True):
        if not isinstance(value, str):
            return
        url = urljoin(unescape(base), (unescape(value) if decode_entities else value).strip())
        try:
            scheme = urlsplit(url).scheme
            if scheme == 'data' and url.lower().startswith('data:image/'):
                normalized = url
            elif scheme in ('http', 'https'):
                normalized = requests.Request('GET', url).prepare().url
            else:
                return
        except (ValueError, requests.RequestException):
            return
        key = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        images.setdefault(key, {'url': normalized, 'description': description})

    def html_images(source):
        for image in BeautifulSoup(source, 'html.parser').find_all('img', src=True):
            if not image.find_parent(['script', 'style', 'template']):
                add(image['src'], image.get('alt') or '', decode_entities=False)

    def walk(node):
        if isinstance(node, marko.inline.Image):
            add(node.dest, ''.join(child.children for child in node.children if isinstance(child.children, str)))
        elif isinstance(node, marko.block.HTMLBlock):
            html_images(node.body)
        elif isinstance(node, marko.inline.InlineHTML):
            html_images(node.children)
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            for child in children:
                walk(child)

    if extension in ('html', 'htm', 'xhtml'):
        html_images(text)
    else:
        walk(marko.parse(text))
    return images


def _public_address(url):
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or '').rstrip('.').lower()
        if (len(url) > 8192 or '\\' in url or any(ord(char) < 32 for char in url)
                or parsed.scheme not in ('http', 'https') or not hostname
                or parsed.username or parsed.password or hostname in ('localhost', 'localhost.localdomain')
                or hostname.endswith('.local')):
            raise ValueError('invalid target')
        addresses = [result[4][0] for result in socket.getaddrinfo(hostname,
            parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)]
        if not addresses or any(not ip_address(address).is_global for address in addresses):
            raise ValueError('non-public target')
    except (ValueError, OSError):
        raise StoreError('出于安全原因，无法访问该来源图片地址', 403) from None
    return addresses[0]


class PublicImageAdapter(HTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        address = _public_address(request.url)
        host, options = self.build_connection_pool_key_attributes(request, verify, cert)
        parsed = urlsplit(request.url)
        request.headers['Host'] = parsed.netloc
        if host['scheme'] == 'https':
            options.update(server_hostname=parsed.hostname, assert_hostname=parsed.hostname)
        host['host'] = address
        return self.poolmanager.connection_from_host(**host, pool_kwargs=options)


def _image_response(raw, mime):
    if not raw:
        raise StoreError('来源图片内容为空，请下载原件核对', 502)
    output = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
    try:
        output.write(raw)
        output.seek(0)
        response = send_file(output, mimetype=mime, conditional=False)
    except Exception:
        output.close()
        raise
    response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                             'Content-Security-Policy': 'sandbox'})
    response.call_on_close(output.close)
    return response


def _embedded_image(value):
    try:
        header, payload = value.split(',', 1)
        mime = header[5:].split(';', 1)[0].lower()
        if not re.fullmatch(r'image/[a-z0-9.+-]+', mime):
            raise ValueError('invalid image mime')
        raw = (base64.b64decode(re.sub(r'\s+', '', payload), validate=True)
               if 'base64' in header.lower().split(';')[1:] else unquote_to_bytes(payload))
    except (ValueError, binascii.Error):
        raise StoreError('内嵌图片编码无效，请下载原件核对', 415) from None
    if len(raw) > MAX_IMAGE_BYTES:
        raise StoreError('内嵌图片过大，请下载原件查看', 413)
    return _image_response(raw, mime)


def source_image_response(client, document_id, image_key, knowledge_base_id=None):
    if len(image_key) != 64 or any(char not in '0123456789abcdef' for char in image_key):
        raise StoreError('来源图片标识无效', 400)
    image = source_images(client, document_id, knowledge_base_id).get(image_key)
    if not image:
        raise StoreError('原件未引用该图片，请刷新来源资料', 404)
    url = image['url']
    if url.lower().startswith('data:image/'):
        return _embedded_image(url)
    try:
        for hop in range(6):
            with requests.Session() as session:
                session.trust_env = False
                session.mount('http://', PublicImageAdapter())
                session.mount('https://', PublicImageAdapter())
                with session.get(url, stream=True, allow_redirects=False, timeout=client.timeout,
                                 headers={'Accept': 'image/*', 'Accept-Encoding': 'identity'}) as upstream:
                    if upstream.status_code in (301, 302, 303, 307, 308):
                        location = upstream.headers.get('Location')
                        if not location or hop == 5:
                            raise StoreError('来源图片重定向不可用，请下载原件查看', 502)
                        url = urljoin(url, location)
                        continue
                    if upstream.status_code == 413:
                        raise StoreError('来源图片过大，请下载原件查看', 413)
                    upstream.raise_for_status()
                    mime = upstream.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
                    if not mime.startswith('image/'):
                        raise StoreError('来源地址未返回图片，请下载原件核对', 415)
                    raw = _read_body(upstream, MAX_IMAGE_BYTES)
                    return _image_response(raw, mime)
    except requests.RequestException:
        raise StoreError('来源图片读取失败，请刷新后重试', 502) from None
