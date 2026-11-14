"""Preserved attachment and archive history business contracts."""
import io
import os
from psycopg.types.json import Jsonb
from governance.database import connection


def test_attachment_preview_input_and_owner_isolation(authenticated_client):
    from webapi.chat_resources import prepare_attachments
    http = authenticated_client
    sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    response = http.post(f'/api/v1/sessions/{sid}/attachments', data={'file': (io.BytesIO('附件原文'.encode()), 'note.txt')})
    assert response.status_code == 200
    item = response.json['data']
    assert item['status'] == 'ready' and 'path' not in item
    assert http.get(f'/api/v1/sessions/{sid}/attachments/{item["id"]}/preview').data == '附件原文'.encode()
    prepared = prepare_attachments(sid, os.environ['TEST_PLATFORM_USER'], {'attachment_ids': [item['id']]})
    assert next(iter(prepared['files'].values()))['content'] == '附件原文'
    other_sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    assert http.get(f'/api/v1/sessions/{other_sid}/attachments/{item["id"]}').status_code == 404
    assert http.delete(f'/api/v1/sessions/{sid}/attachments/{item["id"]}').status_code == 200



def test_history_pages_keep_approval_chains_and_reject_invalid_cursor(authenticated_client):
    http = authenticated_client
    sid = http.post('/api/v1/sessions', json={}).json['data']['id']
    owner = os.environ['TEST_PLATFORM_USER']
    with connection() as conn:
        conn.execute("UPDATE agent_sessions SET agent_config='{}' WHERE id=%s", (sid,))
        for number in range(4):
            conn.execute("INSERT INTO agent_runs(id,session_id,owner_id,status,query,answer,created_at) VALUES (%s,%s,%s,'completed',%s,%s,now()+(%s*interval '1 second'))",
                (f'page{number}', sid, owner, f'question{number}', f'answer{number}', number))
        conn.execute("UPDATE agent_runs SET pending_json=%s WHERE id='page2'", (Jsonb({'resumed_run_id': 'page3'}),))
    recent = http.get(f'/api/v1/messages/{sid}/load?limit=2').json['data']
    assert [item['id'] for item in recent] == ['user-page2', 'page2']
    assert recent[-1]['content'] == 'answer2\n\nanswer3'
    earlier = http.get(f'/api/v1/messages/{sid}/load', query_string={'limit': 2, 'before_time': recent[0]['created_at']}).json['data']
    assert [item['id'] for item in earlier] == ['user-page1', 'page1']
    assert http.get(f'/api/v1/messages/{sid}/load?before_time=bad').status_code == 400
    assert http.get(f'/api/v1/sessions/continue-stream/{sid}?message_id=page2&after_cursor=9223372036854775808').status_code == 410
