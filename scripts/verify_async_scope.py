"""Verify live grant scopes with temporary users and empty threads; never start runs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def verify():
    import psycopg
    import requests
    from agent import async_runtime, registry, sessions
    from governance.database import connection

    # The running container supplies its existing environment; no private env file is read.
    if Path('/app/.runtime/async-agent.env').exists():
        raise RuntimeError('This check must use the container environment, not a private env file')
    base = 'http://127.0.0.1:2026'
    # Enable fixture minting only in this short-lived exec process, never the service or its files.
    os.environ['ASYNC_AGENT_RUNTIME_ENABLED'] = '1'
    requests.get(base + '/health', timeout=5).raise_for_status()
    owners, parents, threads, checked = [], [], [], []

    def call(method, path, headers, expected, body=None):
        response = requests.request(method, base + path, headers=headers, json=body, timeout=10)
        if response.status_code != expected:
            raise AssertionError(f'{method} {path}: expected {expected}, got {response.status_code}')
        checked.append({'method': method, 'status': response.status_code})
        return response

    def fixture(owner):
        parent = sessions.create_session('Temporary async scope verification', owner)['id']
        parents.append(parent)
        child = {'name': 'scope-worker', 'description': 'Empty thread verification', 'execution_mode': 'async'}
        spec = async_runtime.specification(child, owner_id=owner, session_id=parent, agent_id=None,
            config={'access_level': 'read_only', 'subagents': [child]}, knowledge_base_ids=[],
            knowledge_ids=[], tag_scopes=[], persist=True)
        grant = next(value for value in registry.records(async_runtime.GRANT_KIND, owner)
                     if value['parent_session_id'] == parent)
        thread_id = str(uuid.uuid4())
        threads.append((thread_id, owner, spec['headers']))
        response = call('POST', '/threads', spec['headers'], 200, {
            'thread_id': thread_id, 'metadata': {'parent_thread_id': 'forged', 'delegation_id': 'forged'}})
        metadata = response.json()['metadata']
        assert metadata['parent_thread_id'] == parent and metadata['delegation_id'] == grant['id']
        return thread_id, spec['headers']

    try:
        with connection() as conn:
            for _ in range(2):
                owner = str(uuid.uuid4())
                owners.append(owner)
                conn.execute('''INSERT INTO platform_users(id,email,username,password_hash,role)
                    VALUES (%s,%s,%s,%s,'viewer')''',
                    (owner, f'async-scope-{owner}@invalid.example', 'Temporary scope fixture', uuid.uuid4().hex))
        own, header_a = fixture(owners[0])
        other_parent, _ = fixture(owners[0])
        other_owner, _ = fixture(owners[1])
        missing_run = str(uuid.uuid4())
        for foreign in (other_parent, other_owner):
            root = '/threads/' + foreign
            cases = [
                ('GET', root, None), ('PATCH', root, {'metadata': {'probe_note': 'forbidden'}}),
                ('DELETE', root, None), ('GET', root + '/state', None),
                ('POST', root + '/state', {'as_node': '__copy__'}),
                ('GET', root + '/history', None), ('POST', root + '/history', {'limit': 1}),
                ('GET', root + '/runs', None), ('GET', root + '/runs/' + missing_run, None),
                ('POST', root + '/runs/' + missing_run + '/cancel', None),
                ('DELETE', root + '/runs/' + missing_run, None),
            ]
            for method, path, body in cases:
                call(method, path, header_a, 403, body)
            # Existing IDs cannot be adopted through Aegra's idempotent-create path.
            # A foreign owner's UUID is absent from scoped lookup, then conflicts at the global primary key.
            call('POST', '/threads', header_a, 403 if foreign == other_parent else 409,
                 {'thread_id': foreign, 'if_exists': 'do_nothing'})
        call('POST', '/runs/cancel', header_a, 403, {'status': 'all'})
        call('PATCH', '/threads/' + own, header_a, 403, {'metadata': {'delegation_id': 'forged'}})
        call('GET', '/threads/' + own, header_a, 200)
        call('PATCH', '/threads/' + own, header_a, 200, {'metadata': {'probe_note': 'own-scope'}})
        call('GET', '/threads/' + own + '/state', header_a, 200)
        call('GET', '/threads/' + own + '/history', header_a, 200)
        call('GET', '/threads/' + own + '/runs', header_a, 200)
        call('GET', '/threads/' + own + '/runs/' + missing_run, header_a, 404)
        call('POST', '/threads/' + own + '/runs/' + missing_run + '/cancel', header_a, 404)
    finally:
        already_failed = sys.exc_info()[0] is not None
        remote_errors = []
        for thread_id, owner, headers in threads:
            try:
                response = requests.delete(base + '/threads/' + thread_id, headers=headers, timeout=10)
                if response.status_code not in (200, 404):
                    remote_errors.append(response.status_code)
            except requests.RequestException:
                remote_errors.append('network')
        # A failed HTTP assertion must not leave fixture rows; only these UUIDs are targeted.
        with psycopg.connect(os.environ['DATABASE_URL']) as conn:
            conn.execute('DELETE FROM thread WHERE thread_id=ANY(%s) AND user_id=ANY(%s)',
                         ([item[0] for item in threads], owners))
            assert conn.execute('SELECT count(*) FROM thread WHERE thread_id=ANY(%s)',
                                ([item[0] for item in threads],)).fetchone()[0] == 0
        with connection() as conn:
            conn.execute('DELETE FROM runtime_records WHERE owner_id=ANY(%s) AND kind=%s',
                         (owners, async_runtime.GRANT_KIND))
            conn.execute('DELETE FROM agent_sessions WHERE id=ANY(%s) AND owner_id=ANY(%s)', (parents, owners))
            conn.execute('DELETE FROM platform_users WHERE id=ANY(%s)', (owners,))
            assert conn.execute('SELECT count(*) AS n FROM platform_users WHERE id=ANY(%s)', (owners,)).fetchone()['n'] == 0
            assert conn.execute('SELECT count(*) AS n FROM agent_sessions WHERE id=ANY(%s)', (parents,)).fetchone()['n'] == 0
            assert conn.execute('SELECT count(*) AS n FROM runtime_records WHERE owner_id=ANY(%s)', (owners,)).fetchone()['n'] == 0
        if remote_errors and not already_failed:
            raise AssertionError(f'HTTP cleanup had errors {remote_errors}; exact fixture rows were removed')
    print(json.dumps({'result': 'passed', 'http_checks': len(checked), 'runs_started': 0,
                      'fixture_users_removed': len(owners), 'fixture_threads_removed': len(threads)}))


if __name__ == '__main__':
    if sys.argv[1:] == ['--inside-container']:
        verify()
    else:
        subprocess.run(['docker', 'exec', '-i', 'showdoc-async-agent-agent-runtime-1',
                        'python', '-', '--inside-container'], input=Path(__file__).read_text(),
                       text=True, check=True)
