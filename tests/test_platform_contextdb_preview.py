"""Source previews preserve bytes; media URLs only come from authorized official reads."""
from unittest.mock import Mock

import pytest
import requests

import app as app_module
from integrations.contextdb import ContextDBAuthError, ContextDBClient
import webapi.contextdb_preview as preview


def resource(raw=b'image', mime_type='image/png', status=200, headers=None):
    response = Mock(status_code=status)
    response.headers = {'Content-Type': mime_type, **(headers or {})}
    response.iter_content.return_value = [raw]
    return response


@pytest.fixture
def previews(monkeypatch, authenticated_client):
    client = Mock(base_url='https://context-database.aliyuncs.com', timeout=5)
    client._headers.return_value = {'X-API-Key': 'private-member-key'}
    client._payload = ContextDBClient()._payload
    client.get_document.return_value = {'id': 'doc', 'knowledge_base_id': 'kb', 'name': '原文.md',
        'mime_type': 'text/markdown', 'download_url': 'https://files.example/source'}
    monkeypatch.setattr('webapi.contextdb.client_for_user', lambda: client)
    fetch = Mock(return_value=resource())
    monkeypatch.setattr(preview.requests, 'get', fetch)
    return authenticated_client, client, fetch


@pytest.mark.parametrize('name,mime,raw', [
    ('原文.md', 'text/markdown', '# 原文\n[链接](https://example.com)\n![图](https://example.com/a.png)'.encode()),
    ('手册.pdf', 'application/pdf', b'%PDF-1.7\x00\xff'),
    ('手册.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', b'PK\x03\x04\x00\xff'),
    ('表格.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', b'PK\x03\x04\x00\xfe'),
    ('录音.mp3', 'audio/mpeg', b'ID3\x00\xff'),
    ('视频.mp4', 'video/mp4', b'\x00\x00ftyp\xff'),
])
def test_source_download_preserves_original_bytes_and_media_type(previews, name, mime, raw):
    http, client, fetch = previews
    client.get_document.return_value.update(name=name, mime_type=mime)
    fetch.return_value = resource(raw, mime)
    response = http.get('/api/contextdb/documents/doc/download?knowledge_base_id=kb')
    assert response.status_code == 200 and response.data == raw and response.mimetype == mime
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    client.get_document.assert_called_once_with('kb', 'doc', with_download_url=True)
    assert fetch.call_args.kwargs['headers'] == {'Accept-Encoding': 'identity'}
    assert fetch.call_args.kwargs['allow_redirects'] is False
    assert fetch.call_args.kwargs['stream'] is True
    fetch.return_value.close.assert_called()


def test_source_permission_and_library_mismatch_prevent_download(previews):
    http, client, fetch = previews
    assert http.get('/api/contextdb/documents/doc/download?knowledge_base_id=another').status_code == 404
    fetch.assert_not_called()
    client.get_document.side_effect = ContextDBAuthError('forbidden', status_code=403)
    assert http.get('/api/contextdb/documents/doc/download').status_code == 403
    fetch.assert_not_called()


@pytest.mark.parametrize('path', ['/api/contextdb/assets/asset-1',
    '/api/contextdb/v1/knowledge/assets?asset_id=asset-1'])
def test_asset_resolves_with_member_key_then_downloads_without_credentials(previews, path):
    http, client, fetch = previews
    redirect = resource(status=302, headers={'Location': 'https://files.example/image'})
    client._session.get.return_value = redirect
    response = http.get(path)
    assert response.status_code == 200 and response.data == b'image'
    upstream = client._session.get.call_args
    assert upstream.args == ('https://context-database.aliyuncs.com/v1/knowledge/assets',)
    assert upstream.kwargs['params'] == {'asset_id': 'asset-1'}
    assert upstream.kwargs['headers'] == {'X-API-Key': 'private-member-key'}
    assert upstream.kwargs['allow_redirects'] is False
    assert fetch.call_args.args == ('https://files.example/image',)
    assert fetch.call_args.kwargs['headers'] == {'Accept-Encoding': 'identity'}
    assert 'Location' not in response.headers and 'private-member-key' not in response.data.decode()
    redirect.close.assert_called_once()


def test_asset_permission_failure_never_follows_a_url(previews):
    http, client, fetch = previews
    client._session.get.return_value = Mock(status_code=403)
    client._payload = Mock(side_effect=ContextDBAuthError('asset forbidden', status_code=403))
    assert http.get('/api/contextdb/assets/asset-1').status_code == 403
    fetch.assert_not_called()
    client._session.get.return_value.close.assert_called_once()


@pytest.mark.parametrize('url', [None, 'http://files.example/image', 'file:///etc/passwd',
    'https://user:password@files.example/image', 'https://127.0.0.1/private', 'https://localhost/private'])
def test_asset_rejects_invalid_upstream_locations(previews, url):
    http, client, fetch = previews
    client._session.get.return_value = resource(status=302, headers={'Location': url})
    assert http.get('/api/contextdb/assets/asset-1').status_code == 502
    fetch.assert_not_called()


def test_asset_requires_id_and_read_method(previews):
    http, client, fetch = previews
    assert http.get('/api/contextdb/v1/knowledge/assets?url=https://files.example/a').status_code == 400
    assert http.post('/api/contextdb/v1/knowledge/assets', json={'asset_id': 'asset-1'}).status_code == 405
    client._session.get.assert_not_called()
    fetch.assert_not_called()


@pytest.mark.parametrize('kind', ['image', 'audio', 'video'])
def test_attachment_refreshes_url_from_exact_authorized_chunk(previews, kind):
    http, client, fetch = previews
    client._request.return_value = {'document_id': 'doc', 'chunks': [{'chunk_index': 3,
        'attachments': [{'type': kind, 'download_url': 'https://files.example/current-media'}]}]}
    response = http.get('/api/contextdb/documents/doc/attachments/3/0?knowledge_base_id=kb&url=https://evil.example/')
    assert response.status_code == 200 and response.data == b'image'
    client.get_document.assert_called_once_with('kb', 'doc', with_download_url=True)
    client._request.assert_called_once_with('GET', '/v1/knowledge/documents/chunks',
        params={'document_id': 'doc', 'offset': 3, 'limit': 1})
    assert fetch.call_args.args == ('https://files.example/current-media',)


@pytest.mark.parametrize('result,status', [
    ({'document_id': 'other', 'chunks': [{'chunk_index': 3}]}, 404),
    ({'chunks': []}, 404),
    ({'chunks': [{'chunk_index': 4}]}, 409),
    ({'chunks': [{'chunk_index': 3, 'attachments': []}]}, 404),
    ({'chunks': [{'chunk_index': 3, 'attachments': [{'type': 'image'}]}]}, 409),
    ({'chunks': [{'chunk_index': 3, 'attachments': [{'type': 'link', 'download_url': 'https://files.example/a'}]}]}, 409),
    ({'chunks': [{'chunk_index': 3, 'attachments': 'invalid'}]}, 502),
])
def test_attachment_does_not_guess_when_source_changes(previews, result, status):
    http, client, fetch = previews
    client._request.return_value = result
    assert http.get('/api/contextdb/documents/doc/attachments/3/0').status_code == status
    fetch.assert_not_called()


def test_media_stream_forwards_range_without_credentials(previews):
    http, _, fetch = previews
    fetch.return_value = resource(b'part', 'text/markdown', status=206,
        headers={'Content-Range': 'bytes 5-8/100', 'Content-Length': '4', 'Accept-Ranges': 'bytes'})
    response = http.get('/api/contextdb/documents/doc/download', headers={'Range': 'bytes=5-8'})
    assert response.status_code == 206 and response.data == b'part'
    assert response.headers['Content-Range'] == 'bytes 5-8/100'
    assert response.headers['Accept-Ranges'] == 'bytes'
    assert fetch.call_args.kwargs['headers'] == {'Accept-Encoding': 'identity', 'Range': 'bytes=5-8'}
    fetch.reset_mock()
    assert http.get('/api/contextdb/documents/doc/download', headers={'Range': 'bytes=0-1,5-6'}).status_code == 416
    fetch.assert_not_called()


def test_download_error_is_explicit_and_does_not_expose_signed_url(previews):
    http, _, fetch = previews
    fetch.side_effect = requests.RequestException('https://files.example/source?private-signature')
    response = http.get('/api/contextdb/documents/doc/download')
    assert response.status_code == 503 and '刷新后重试' in response.json['message']
    assert 'private-signature' not in response.json['message']


@pytest.mark.parametrize('status', [413, 416])
def test_media_size_and_range_failures_remain_explicit(previews, status):
    http, _, fetch = previews
    fetch.return_value = resource(status=status)
    response = http.get('/api/contextdb/documents/doc/download')
    assert response.status_code == status and response.json['success'] is False
    fetch.return_value.iter_content.assert_not_called()
    fetch.return_value.close.assert_called_once()


def test_preview_endpoints_require_platform_login(previews):
    _, client, fetch = previews
    raw = app_module.app.test_client()
    for path in ('/api/contextdb/assets/asset-1', '/api/contextdb/documents/doc/download',
                 '/api/contextdb/documents/doc/attachments/0/0',
                 '/api/contextdb/documents/doc/source-images',
                 '/api/contextdb/documents/doc/source-images/' + '0' * 64):
        assert raw.get(path).status_code == 401
    client.get_document.assert_not_called()
    client._session.get.assert_not_called()
    fetch.assert_not_called()
