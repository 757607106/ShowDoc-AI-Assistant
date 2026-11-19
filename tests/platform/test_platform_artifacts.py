"""Archived image attachments retain owned previews."""
import io
import base64
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from psycopg.types.json import Jsonb
from PIL import Image
from agent import sessions


def test_image_upload_history_uses_owned_preview_and_not_base64(authenticated_client):
    from webapi.chat.chat_resources import prepare_attachments
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    raw = io.BytesIO()
    Image.new('RGB', (2, 2), 'white').save(raw, 'PNG')
    value = prepare_attachments(sid, owner, {'images': [{'data': 'data:image/png;base64,' + base64.b64encode(raw.getvalue()).decode()}]})
    image = value['user_images'][0]
    assert 'base64' not in image['url'] and image['id'] in value['attachment_ids']
    assert authenticated_client.get(image['url']).data == raw.getvalue()


def test_text_attachment_is_persisted_without_host_file_and_keeps_preview_expiry_and_owner(authenticated_client, monkeypatch, tmp_path):
    from deepagents.backends.utils import file_data_to_string
    from agent import sandbox
    from governance.database import connection
    from governance.store import StoreError
    from webapi.chat import chat_resources
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    other_sid = sessions.create_session(owner_id=owner)['id']
    monkeypatch.setattr(sandbox, 'enabled', lambda: True)
    parse = Mock(return_value='隔离解析正文')
    monkeypatch.setattr(chat_resources, '_parse_attachment', parse)
    response = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments',
        data={'file': (io.BytesIO(b'original bytes'), 'document.txt')})
    assert response.status_code == 200, response.json
    public = response.json['data']
    assert not {'path', 'raw_content', 'text'} & public.keys()
    parse.assert_called_once_with('document.txt', b'original bytes')
    with connection() as conn:
        item = conn.execute('SELECT payload FROM runtime_records WHERE id=%s', (public['id'],)).fetchone()['payload']
    assert 'path' not in item and base64.b64decode(item['raw_content']) == b'original bytes'
    assert not list((tmp_path / 'data').glob('chat-attachments/**/*'))
    preview = f'/api/v1/sessions/{sid}/attachments/{public["id"]}/preview'
    assert authenticated_client.get(preview).data == b'original bytes'
    ready = chat_resources.prepare_attachments(sid, owner, {'attachment_ids': [public['id']]})
    assert file_data_to_string(next(iter(ready['files'].values()))) == '隔离解析正文'
    assert authenticated_client.get(preview.replace(sid, other_sid)).status_code == 404
    with pytest.raises(StoreError) as denied:
        chat_resources.prepare_attachments(sid, 'another-owner', {'attachment_ids': [public['id']]})
    assert denied.value.status == 404
    item['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with connection() as conn:
        conn.execute('UPDATE runtime_records SET payload=%s WHERE id=%s', (Jsonb(item), public['id']))
    assert authenticated_client.get(preview).status_code == 410


def test_unconfigured_parser_rejects_text_without_host_fallback_or_partial_record(authenticated_client, monkeypatch):
    from agent import sandbox
    from governance.database import connection
    from webapi.chat import chat_resources
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    monkeypatch.setattr(sandbox, 'enabled', lambda: False)
    forbidden = Mock(side_effect=AssertionError('unconfigured parser must not run'))
    monkeypatch.setattr(chat_resources, '_parse_attachment', forbidden)
    response = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments',
        data={'file': (io.BytesIO(b'input'), 'document.txt')})
    assert response.status_code == 503
    forbidden.assert_not_called()
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM runtime_records WHERE kind='chat_attachment'").fetchone()['n'] == 0


def test_failed_isolated_parse_retains_owned_original_and_delete_removes_only_record(authenticated_client, monkeypatch):
    from agent import sandbox
    from governance.database import connection
    from webapi.chat import chat_resources
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    monkeypatch.setattr(sandbox, 'enabled', lambda: True)
    monkeypatch.setattr(chat_resources, '_parse_attachment', Mock(side_effect=ValueError('invalid parser output')))
    response = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments',
        data={'file': (io.BytesIO(b'bad document'), 'bad.pdf')})
    assert response.status_code == 200 and response.json['data']['status'] == 'failed'
    item = response.json['data']
    base = f'/api/v1/sessions/{sid}/attachments/{item["id"]}'
    assert authenticated_client.get(base + '/preview').data == b'bad document'
    assert authenticated_client.delete(base).status_code == 200
    assert authenticated_client.get(base).status_code == 404
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM runtime_records WHERE kind='chat_attachment'").fetchone()['n'] == 0


@pytest.mark.skipif(os.getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires local OpenSandbox and the fixed parser image')
def test_real_attachment_http_to_isolated_parser_and_owned_preview(authenticated_client, monkeypatch):
    from dotenv import dotenv_values
    from deepagents.backends.utils import file_data_to_string
    from webapi.chat.chat_resources import prepare_attachments
    for key, value in dotenv_values('.env').items():
        if key.startswith('OPEN_SANDBOX_') and value:
            monkeypatch.setenv(key, value)
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    raw = '真实隔离附件正文'.encode('utf-8')
    response = authenticated_client.post(f'/api/v1/sessions/{sid}/attachments',
        data={'file': (io.BytesIO(raw), 'fixture.txt')})
    assert response.status_code == 200, response.json
    item = response.json['data']
    assert item['status'] == 'ready'
    prepared = prepare_attachments(sid, owner, {'attachment_ids': [item['id']]})
    assert file_data_to_string(next(iter(prepared['files'].values()))) == raw.decode('utf-8')
    assert authenticated_client.get(f'/api/v1/sessions/{sid}/attachments/{item["id"]}/preview').data == raw

