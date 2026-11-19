"""Source image references are exact, authorized and fetched through pinned public DNS."""
from io import BytesIO
from unittest.mock import MagicMock, Mock

import pytest
import requests
from urllib3 import PoolManager
from urllib3.response import HTTPResponse

from governance.store import StoreError
import webapi.contextdb.source_images as images


def original(body):
    response = MagicMock(status_code=200)
    response.__enter__.return_value = response
    response.iter_content.return_value = [body]
    return response


@pytest.fixture
def source_images(monkeypatch, authenticated_client):
    client = Mock(timeout=5)
    client.get_document.return_value = {'id': 'doc', 'knowledge_base_id': 'kb', 'name': '原件.md',
        'metadata': {'url': 'https://docs.example/guide/page'}, 'download_url': 'https://files.example/source'}
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: client)
    source = original(b'![chart](http://images.example/a.png?a=1&amp;b=2)')
    fetch_source = Mock(return_value=source)
    monkeypatch.setattr(images.requests, 'get', fetch_source)
    monkeypatch.setattr(images.socket, 'getaddrinfo', lambda host, port, **kwargs: [
        (2, 1, 6, '', ('93.184.216.34', port))])
    connection = Mock(host='93.184.216.34')
    connection.urlopen.side_effect = lambda *args, **kwargs: HTTPResponse(
        body=BytesIO(b'\x89PNG\r\n\x1a\nimage'), status=200, headers={'Content-Type': 'image/png'}, preload_content=False)
    pools = Mock(return_value=connection)
    monkeypatch.setattr(PoolManager, 'connection_from_host', lambda self, **kwargs: pools(**kwargs))
    return authenticated_client, client, fetch_source, connection, pools


def test_source_image_parser_handles_markdown_references_html_entities_and_relative_paths():
    text = '![图][picture]\n\n[picture]: ../image.png?a=1&amp;b=2\n\n<img src="../image.png?a=1&amp;b=2" alt="duplicate">\n\n```md\n![example](https://ignored.example/code.png)\n```'
    result = images.extract_source_images(text, 'md', 'https://docs.example/guide/page')
    assert len(result) == 1
    assert next(iter(result.values())) == {'url': 'https://docs.example/image.png?a=1&b=2', 'description': '图'}
    html = images.extract_source_images('<img src="/图.png" alt="截图"><img src="javascript:alert(1)"><template><img src="https://ignored.example/template"></template>',
        'html', 'https://docs.example/page')
    assert len(html) == 1 and next(iter(html.values()))['url'] == 'https://docs.example/%E5%9B%BE.png'
    encoded = images.extract_source_images('<img src="https://images.example/a?x=1&amp;amp;y=2">', 'html')
    assert next(iter(encoded.values()))['url'] == 'https://images.example/a?x=1&amp;y=2'


def test_manifest_does_not_expose_urls_and_proxy_uses_only_exact_source_reference(source_images):
    http, client, fetch_source, connection, pools = source_images
    manifest = http.get('/api/contextdb/documents/doc/source-images?knowledge_base_id=kb')
    assert manifest.status_code == 200
    item = manifest.json['data']['images'][0]
    assert set(item) == {'image_key', 'description'} and len(item['image_key']) == 64
    assert 'http' not in manifest.get_data(as_text=True)
    response = http.get('/api/contextdb/documents/doc/source-images/' + item['image_key'] + '?knowledge_base_id=kb&url=http://evil.example/')
    assert response.status_code == 200 and response.data.startswith(b'\x89PNG')
    assert response.mimetype == 'image/png' and response.headers['Cache-Control'] == 'no-store'
    assert connection.urlopen.call_args.kwargs['headers']['Host'] == 'images.example'
    assert 'X-API-Key' not in connection.urlopen.call_args.kwargs['headers']
    assert 'Cookie' not in connection.urlopen.call_args.kwargs['headers']
    assert pools.call_args.kwargs['host'] == '93.184.216.34'
    assert all(call.args == ('kb', 'doc') for call in client.get_document.call_args_list)
    assert fetch_source.call_args.kwargs['allow_redirects'] is False
    response.close()


def test_wrong_scope_or_unknown_hash_never_fetches_an_external_image(source_images):
    http, _, _, connection, _ = source_images
    assert http.get('/api/contextdb/documents/doc/source-images?knowledge_base_id=other').status_code == 404
    assert http.get('/api/contextdb/documents/doc/source-images/' + '0' * 64 + '?url=http://images.example/a.png').status_code == 404
    assert http.get('/api/contextdb/documents/doc/source-images/not-a-hash').status_code == 400
    connection.urlopen.assert_not_called()


@pytest.mark.parametrize('addresses', [['127.0.0.1'], ['10.0.0.1'], ['::1'], ['169.254.169.254'],
    ['93.184.216.34', '192.168.1.1']])
def test_private_dns_is_blocked_even_when_crawler_private_urls_are_enabled(source_images, monkeypatch, addresses):
    http, _, _, connection, _ = source_images
    monkeypatch.setenv('WEB_CRAWLER_ALLOW_PRIVATE_URLS', 'true')
    monkeypatch.setattr(images.socket, 'getaddrinfo', lambda host, port, **kwargs: [
        (2, 1, 6, '', (address, port)) for address in addresses])
    key = http.get('/api/contextdb/documents/doc/source-images').json['data']['images'][0]['image_key']
    response = http.get('/api/contextdb/documents/doc/source-images/' + key)
    assert response.status_code == 403
    connection.urlopen.assert_not_called()


def test_redirects_are_revalidated_and_cannot_reach_private_networks(source_images, monkeypatch):
    http, _, _, connection, pools = source_images
    connection.urlopen.side_effect = lambda *args, **kwargs: HTTPResponse(body=BytesIO(b''), status=302,
        headers={'Location': 'http://127.0.0.1/private'}, preload_content=False)
    monkeypatch.setattr(images.socket, 'getaddrinfo', lambda host, port, **kwargs: [
        (2, 1, 6, '', ('127.0.0.1' if host == '127.0.0.1' else '93.184.216.34', port))])
    key = http.get('/api/contextdb/documents/doc/source-images').json['data']['images'][0]['image_key']
    assert http.get('/api/contextdb/documents/doc/source-images/' + key).status_code == 403
    assert connection.urlopen.call_count == pools.call_count == 1


def test_https_connections_pin_the_checked_ip_and_keep_certificate_hostname(monkeypatch):
    monkeypatch.setattr(images.socket, 'getaddrinfo', lambda host, port, **kwargs: [
        (2, 1, 6, '', ('93.184.216.34', port))])
    adapter = images.PublicImageAdapter()
    adapter.poolmanager = Mock()
    request = requests.Request('GET', 'https://images.example/a.png').prepare()
    adapter.get_connection_with_tls_context(request, True)
    params = adapter.poolmanager.connection_from_host.call_args.kwargs
    assert params['host'] == '93.184.216.34' and params['scheme'] == 'https'
    assert params['pool_kwargs']['server_hostname'] == params['pool_kwargs']['assert_hostname'] == 'images.example'
    assert request.headers['Host'] == 'images.example'


@pytest.mark.parametrize('status,mime,raw,expected', [(200, 'text/html', b'<html>login</html>', 415),
    (413, 'image/png', b'', 413), (200, 'image/png', b'too large', 413)])
def test_non_images_and_oversized_images_fail_explicitly(source_images, monkeypatch, status, mime, raw, expected):
    http, _, _, connection, _ = source_images
    monkeypatch.setattr(images, 'MAX_IMAGE_BYTES', 5)
    connection.urlopen.side_effect = lambda *args, **kwargs: HTTPResponse(body=BytesIO(raw), status=status,
        headers={'Content-Type': mime}, preload_content=False)
    key = http.get('/api/contextdb/documents/doc/source-images').json['data']['images'][0]['image_key']
    assert http.get('/api/contextdb/documents/doc/source-images/' + key).status_code == expected


def test_original_failures_do_not_claim_empty_images_or_expose_url_secrets(source_images):
    http, _, fetch_source, _, _ = source_images
    fetch_source.side_effect = requests.RequestException('https://files.example/private?token=secret')
    response = http.get('/api/contextdb/documents/doc/source-images')
    assert response.status_code == 502 and 'secret' not in response.json['message']


@pytest.mark.parametrize('name,body,mime,expected', [
    ('原件.md', b'![chart](data:image/png;base64,iVBORw0KGgppbWFnZQ==)', 'image/png', b'\x89PNG\r\n\x1a\nimage'),
    ('原件.html', b'<img alt="vector" src="data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22/%3E">',
     'image/svg+xml', b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
])
def test_embedded_images_use_the_same_authorized_hash_proxy_without_network(source_images, name, body, mime, expected):
    http, client, fetch_source, connection, _ = source_images
    client.get_document.return_value['name'] = name
    fetch_source.return_value = original(body)
    manifest = http.get('/api/contextdb/documents/doc/source-images?knowledge_base_id=kb')
    assert manifest.status_code == 200 and len(manifest.json['data']['images']) == 1
    assert 'data:image' not in manifest.get_data(as_text=True)
    key = manifest.json['data']['images'][0]['image_key']
    response = http.get('/api/contextdb/documents/doc/source-images/' + key + '?knowledge_base_id=kb')
    assert response.status_code == 200 and response.data == expected and response.mimetype == mime
    assert response.headers['Content-Security-Policy'] == 'sandbox'
    connection.urlopen.assert_not_called()
    response.close()


def test_invalid_or_oversized_embedded_images_fail_explicitly(source_images, monkeypatch):
    http, _, fetch_source, connection, _ = source_images
    for source, expected in [(b'![chart](data:image/png;base64,%%)', 415),
                             (b'![chart](data:image/png;base64,aW1hZ2U=)', 413)]:
        fetch_source.return_value = original(source)
        monkeypatch.setattr(images, 'MAX_IMAGE_BYTES', 3)
        key = http.get('/api/contextdb/documents/doc/source-images').json['data']['images'][0]['image_key']
        assert http.get('/api/contextdb/documents/doc/source-images/' + key).status_code == expected
    connection.urlopen.assert_not_called()


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'https://user:pass@images.example/a',
    'http://localhost/a', 'http://localhost.localdomain/a', 'http://device.local/a'])
def test_public_fetch_rejects_unsupported_schemes_credentials_and_local_hosts(url):
    with pytest.raises(StoreError):
        images._public_address(url)
