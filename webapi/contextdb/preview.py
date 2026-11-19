"""Read official source files and media through the current member's permissions."""
from ipaddress import ip_address
import re
from urllib.parse import urlsplit

from flask import Response, request
import requests

from governance.store import StoreError
from integrations.contextdb import ContextDBError


def _source_detail(client, document_id, knowledge_base_id=None):
    detail = client.get_document(knowledge_base_id, document_id, with_download_url=True)
    if not isinstance(detail, dict):
        raise StoreError('官方未返回可读取的文档详情', 502)
    if knowledge_base_id and detail.get('knowledge_base_id') != knowledge_base_id:
        raise StoreError('文档不属于当前知识库', 404)
    if detail.get('id', document_id) != document_id:
        raise StoreError('官方文档身份不匹配', 502)
    return detail


def _download_response(client, url, content_type=None):
    # The URL must come from an authenticated official response, never a browser parameter.
    try:
        if not isinstance(url, str) or any(ord(char) < 32 for char in url):
            raise ValueError('invalid signed URL')
        parsed = urlsplit(url)
        hostname = parsed.hostname or ''
        if parsed.scheme != 'https' or not hostname or parsed.username or parsed.password or '\\' in url:
            raise ValueError('invalid signed URL')
        if hostname.lower().rstrip('.') == 'localhost':
            raise ValueError('local signed URL')
        try:
            address = ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError('private signed URL')
    except (TypeError, ValueError):
        raise StoreError('官方未返回有效的资源下载地址', 502) from None
    headers = {'Accept-Encoding': 'identity'}
    if request.headers.get('Range'):
        byte_range = request.headers['Range']
        if not re.fullmatch(r'bytes=(?:\d+-\d*|-\d+)', byte_range):
            raise StoreError('不支持该资源范围请求', 416)
        headers['Range'] = byte_range
    upstream = None
    try:
        # A separate request prevents member keys, session cookies and redirects from crossing hosts.
        upstream = requests.get(url, headers=headers, timeout=client.timeout, stream=True, allow_redirects=False)
        if upstream.status_code in (413, 416):
            upstream.close()
            message = '资源过大，请下载原件查看' if upstream.status_code == 413 else '该资源范围不可用，请重新加载'
            raise StoreError(message, upstream.status_code)
        upstream.raise_for_status()
        if upstream.status_code not in (200, 206):
            upstream.close()
            raise StoreError('官方资源未返回可下载的内容', 502)
    except requests.RequestException:
        if upstream is not None:
            upstream.close()
        raise ContextDBError('官方资源读取失败，请刷新后重试') from None

    def content():
        try:
            yield from upstream.iter_content(chunk_size=64 * 1024)
        finally:
            upstream.close()

    response = Response(content(), status=upstream.status_code,
        content_type=content_type or upstream.headers.get('Content-Type', 'application/octet-stream'))
    for name in ('Content-Range', 'Content-Length', 'Accept-Ranges', 'ETag', 'Last-Modified'):
        if name in upstream.headers and not (name == 'Content-Length' and upstream.headers.get('Content-Encoding')):
            response.headers[name] = upstream.headers[name]
    response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                             'Content-Security-Policy': 'sandbox'})
    response.call_on_close(upstream.close)
    return response


def document_response(client, document_id, knowledge_base_id=None):
    detail = _source_detail(client, document_id, knowledge_base_id)
    if not detail.get('download_url'):
        raise StoreError('官方未返回源文件下载地址', 409)
    return _download_response(client, detail['download_url'], detail.get('mime_type'))


def asset_response(client, asset_id):
    if not isinstance(asset_id, str) or not asset_id.strip() or len(asset_id) > 512:
        raise StoreError('缺少有效的 asset_id', 400)
    try:
        upstream = client._session.get(client.base_url + '/v1/knowledge/assets',
            params={'asset_id': asset_id}, headers=client._headers(), timeout=client.timeout,
            allow_redirects=False)
        try:
            if upstream.status_code != 302:
                client._payload(upstream)
                raise StoreError('官方未返回资产下载地址', 502)
            url = upstream.headers.get('Location')
        finally:
            upstream.close()
    except requests.RequestException:
        raise ContextDBError('官方资产读取失败，请稍后重试') from None
    return _download_response(client, url)


def attachment_response(client, document_id, chunk_index, attachment_index, knowledge_base_id=None):
    _source_detail(client, document_id, knowledge_base_id)
    result = client._request('GET', '/v1/knowledge/documents/chunks', params={
        'document_id': document_id, 'offset': chunk_index, 'limit': 1})
    if not isinstance(result, dict):
        raise StoreError('官方未返回可读取的原文切片', 502)
    chunks = result.get('chunks') or []
    if not isinstance(chunks, list):
        raise StoreError('官方未返回有效的原文切片', 502)
    if result.get('document_id', document_id) != document_id or len(chunks) != 1:
        raise StoreError('原文附件已不可用，请刷新文档', 404)
    chunk = chunks[0]
    if not isinstance(chunk, dict) or chunk.get('chunk_index') != chunk_index:
        raise StoreError('原文切片已变化，请刷新文档', 409)
    attachments = chunk.get('attachments') or []
    if not isinstance(attachments, list):
        raise StoreError('官方未返回有效的原文附件', 502)
    if attachment_index >= len(attachments):
        raise StoreError('原文附件已不可用，请刷新文档', 404)
    attachment = attachments[attachment_index]
    if (not isinstance(attachment, dict) or attachment.get('type') not in ('image', 'audio', 'video')
            or not attachment.get('download_url')):
        raise StoreError('官方未返回可用的附件下载地址', 409)
    return _download_response(client, attachment['download_url'])
