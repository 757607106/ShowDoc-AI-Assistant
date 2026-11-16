"""Real HTTP negative authorization checks, confined to the shared acceptance schema."""
import argparse
import json
import os
import secrets
import sys
from pathlib import Path

import psycopg
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--knowledge-result', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    assert config['schema'].startswith('real_accept_')
    load_dotenv('.env')
    os.environ['DATABASE_URL'] = config['database_url']
    os.environ['AGENT_DATABASE_URL'] = config['agent_database_url']
    with psycopg.connect(config['database_url']) as conn:
        database, schema = conn.execute('SELECT current_database(),current_schema()').fetchone()
        assert database.endswith('_test') and schema == config['schema']
    from governance.database import connection
    from agent.checkpointer import make_checkpointer
    with make_checkpointer() as saver:
        runtime = saver.conn.execute('SELECT current_database() AS db,current_schema() AS schema').fetchone()
        assert runtime['db'].endswith('_test') and runtime['schema'] == config['schema']
    from webapi.auth import create_user
    evidence = json.loads(args.knowledge_result.read_text())
    target, agent = evidence['session_id'], evidence['agent_id']
    password = secrets.token_urlsafe(24)
    owner = create_user('isolation-' + secrets.token_hex(8) + '@example.invalid', '隔离验收', password, 'viewer')
    results = []
    try:
        with connection() as conn:
            email = conn.execute('SELECT email FROM platform_users WHERE id=%s', (owner,)).fetchone()['email']
        with make_checkpointer() as saver:
            before = saver.conn.execute('SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s', (target,)).fetchone()['n']
        client = requests.Session()
        login = client.post(config['backend_url'] + '/api/v1/auth/login', json={'email': email, 'password': password}, timeout=20)
        assert login.status_code == 200
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        cases = [
            ('GET', f'/api/v1/sessions/{target}', None, 404),
            ('GET', f'/api/v1/harness/sessions/{target}/state', None, 404),
            ('GET', f'/api/v1/messages/{target}/load', None, 404),
            ('POST', f'/api/v1/agent-chat/{target}', {'query': 'must not execute'}, 404),
            ('POST', f'/api/v1/sessions/{target}/fork', {'message_id': 'foreign'}, 404),
            ('POST', f'/api/v1/sessions/{target}/sandbox/terminal-ticket', {}, 404),
            ('GET', f'/api/v1/agents/{agent}/memory-file', None, 404),
        ]
        for method, path, body, expected in cases:
            response = client.request(method, config['backend_url'] + path, json=body, timeout=30)
            assert response.status_code == expected, (method, path, response.status_code)
            results.append({'method': method, 'path': path, 'status': response.status_code})
        own = client.post(config['backend_url'] + '/api/v1/sessions', json={'title': '只读账号验收'}, timeout=20)
        assert own.status_code == 200
        own_sid = own.json()['data']['id']
        denied = client.post(config['backend_url'] + f'/api/v1/sessions/{own_sid}/sandbox/terminal-ticket', json={}, timeout=20)
        assert denied.status_code == 403
        results.append({'check': 'viewer terminal rejected before provisioning', 'status': 403})
        with connection() as conn:
            assert conn.execute("SELECT count(*) AS n FROM runtime_records WHERE owner_id=%s AND kind='opensandbox-session'", (owner,)).fetchone()['n'] == 0
            conn.execute('DELETE FROM platform_tokens WHERE owner_id=%s', (owner,))
        with make_checkpointer() as saver:
            assert saver.conn.execute('SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s', (target,)).fetchone()['n'] == before
        revoked = client.get(config['backend_url'] + '/api/v1/auth/me', timeout=20)
        assert revoked.status_code == 401
        results.append({'check': 'actual token revocation', 'status': 401})
        invalid = requests.get(config['backend_url'] + f'/api/v1/harness/sessions/{target}/state',
                               headers={'Authorization': 'Bearer invalid'}, timeout=20)
        assert invalid.status_code == 401
        results.append({'check': 'invalid signature', 'status': 401})
        args.output.write_text(json.dumps({'real_http': True, 'mocked_authentication': False,
            'checks': results, 'source_checkpoint_count_unchanged': before,
            'viewer_sandbox_never_provisioned': True}, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': len(results), 'foreign_source_unmodified': True}))
    finally:
        with connection() as conn:
            conn.execute('DELETE FROM agent_sessions WHERE owner_id=%s', (owner,))
            conn.execute('DELETE FROM platform_audit WHERE owner_id=%s', (owner,))
            conn.execute('DELETE FROM platform_users WHERE id=%s', (owner,))


if __name__ == '__main__':
    main()
