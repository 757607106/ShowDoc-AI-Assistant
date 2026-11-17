"""Exercise real Aegra/DeepAgents workers against a local slow OpenAI provider."""
import json
import os
from pathlib import Path
import re
import select
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Provider(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def reply(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def closed(connection):
        try:
            return bool(select.select([connection], [], [], 0)[0]) and not connection.recv(1, socket.MSG_PEEK)
        except OSError:
            return True

    def do_GET(self):
        with self.server.lock:
            self.reply([{key: value for key, value in item.items() if key != 'socket'} for item in self.server.events])

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        content = next(item['content'] for item in reversed(body['messages']) if item['role'] == 'user')
        if isinstance(content, list):
            content = ''.join(item.get('text', '') for item in content)
        match = re.search(r'PROBE\[([\w-]+)\] DUR=([\d.]+)', content)
        label, duration = match.group(1), float(match.group(2))
        with self.server.lock:
            for item in self.server.events:
                if item['end'] is None and self.closed(item['socket']):
                    item.update(end=time.monotonic(), cancelled=True)
            event = {'label': label, 'start': time.monotonic(), 'end': None,
                     'cancelled': False, 'socket': self.connection}
            self.server.events.append(event)
        stream, cancelled = bool(body.get('stream')), False
        try:
            if stream:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Connection', 'close')
                self.end_headers()
            deadline = event['start'] + duration
            while time.monotonic() < deadline:
                if event['end'] is not None or self.closed(self.connection):
                    cancelled = True
                    return
                if stream:
                    self.chunk(label, {'content': '.'})
                time.sleep(.05)
            if stream:
                self.chunk(label, {'role': 'assistant', 'content': 'DONE ' + label})
                self.chunk(label, {}, finish='stop')
                self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush()
            else:
                self.reply({'id': 'probe-' + label, 'object': 'chat.completion', 'created': int(time.time()),
                    'model': 'probe-model', 'choices': [{'index': 0, 'message': {'role': 'assistant',
                    'content': 'DONE ' + label}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}})
        except (BrokenPipeError, ConnectionResetError):
            cancelled = True
        finally:
            with self.server.lock:
                if event['end'] is None:
                    event.update(end=time.monotonic(), cancelled=cancelled)
            self.close_connection = True

    def chunk(self, label, delta, finish=None):
        data = {'id': 'probe-' + label, 'object': 'chat.completion.chunk', 'created': int(time.time()),
                'model': 'probe-model', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
        self.wfile.write(('data: ' + json.dumps(data) + '\n\n').encode())
        self.wfile.flush()


def verify(port):
    import psycopg
    import requests
    from agent import async_runtime, registry, sessions
    from agent.config import validate_config
    from governance.database import connection

    os.environ['ASYNC_AGENT_RUNTIME_ENABLED'] = '1'  # Only this temporary exec process.
    base, provider = 'http://127.0.0.1:2026', f'http://host.docker.internal:{port}'
    owner, parent, threads, headers = str(uuid.uuid4()), None, [], {}
    result, stage = {'result': 'failed', 'checks': {}}, 'fixture'

    def api(method, path, body=None, expected=200):
        response = requests.request(method, base + path, headers=headers, json=body, timeout=25)
        assert response.status_code == expected, f'{method} {path}: HTTP {response.status_code}, expected {expected}'
        return response.json() if response.content else None

    def events():
        return requests.get(provider + '/events', timeout=5).json()

    def until(check, description, timeout=50):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = check()
            if value:
                return value
            time.sleep(.05)
        raise AssertionError('Timed out: ' + description)

    def thread():
        tid = str(uuid.uuid4())
        threads.append(tid)
        api('POST', '/threads', {'thread_id': tid})
        return tid

    def run(tid, label, duration, strategy='enqueue', expected=200):
        return api('POST', f'/threads/{tid}/runs', {'assistant_id': async_runtime.GRAPH_ID,
            'input': {'messages': [{'role': 'user', 'content': f'PROBE[{label}] DUR={duration}'}]},
            'multitask_strategy': strategy, 'durability': 'sync'}, expected)

    def started(label):
        return until(lambda: next((item for item in events() if item['label'] == label), None), 'provider ' + label)

    def completed(tid, value):
        path = f'/threads/{tid}/runs/' + value['run_id']
        current = until(lambda: (item if item['status'] not in ('pending', 'running') else None)
                        if (item := api('GET', path)) else None, 'terminal run')
        assert current['status'] == 'success', 'Run ended with ' + current['status']
        return current

    try:
        with connection() as conn:
            conn.execute('''INSERT INTO platform_users(id,email,username,password_hash,role)
                VALUES (%s,%s,%s,%s,'viewer')''',
                (owner, f'async-multitask-{owner}@invalid.example', 'Temporary multitask fixture', uuid.uuid4().hex))
        parent = sessions.create_session('Temporary multitask verification', owner)['id']
        model = registry.save_model({'name': 'Temporary local provider', 'type': 'KnowledgeQA', 'source': 'remote',
            'parameters': {'provider': 'generic', 'model_name': 'probe-model', 'api_key': 'fake',
                           'base_url': provider + '/v1'}}, owner)
        child = {'name': 'worker', 'description': 'Local provider verification', 'execution_mode': 'async',
                 'allowed_tools': [], 'selected_skills': [], 'access_level': 'read_only'}
        config = validate_config({'model_id': model['id'], 'allowed_tools': [], 'mcp_selection_mode': 'none',
            'skills_selection_mode': 'none', 'memory_enabled': False, 'access_level': 'read_only',
            'subagents': [child], 'max_iterations': 2, 'max_completion_tokens': 256}, check_runtime=False)
        headers = async_runtime.specification(child, owner_id=owner, session_id=parent, agent_id=None,
            config=config, knowledge_base_ids=[], knowledge_ids=[], tag_scopes=[], persist=True)['headers']
        stage, tid = 'reject', thread()
        first = run(tid, 'reject-running', 2)
        started('reject-running')
        run(tid, 'reject-unexpected', .1, 'reject', 409)
        completed(tid, first)
        result['checks']['reject_busy_http'] = 409
        stage = 'enqueue'
        fifo = [run(tid, 'fifo-1', 1.2)]
        started('fifo-1')
        fifo.extend(run(tid, f'fifo-{number}', 1.2) for number in range(2, 5))
        for value in fifo:
            completed(tid, value)
        sequence = [item for item in events() if item['label'].startswith('fifo-')]
        assert [item['label'] for item in sequence] == [f'fifo-{n}' for n in range(1, 5)], 'enqueue order changed'
        assert all(a['end'] <= b['start'] for a, b in zip(sequence, sequence[1:])), 'same-thread provider overlap'
        result['checks']['enqueue'] = {'runs': 4, 'fifo': True, 'max_provider_active': 1}
        stage, other_a, other_b = 'parallel', thread(), thread()
        a, b = run(other_a, 'parallel-a', 3), run(other_b, 'parallel-b', 3)
        started('parallel-a'); started('parallel-b')
        completed(other_a, a); completed(other_b, b)
        pair = {item['label']: item for item in events() if item['label'].startswith('parallel-')}
        overlap = min(item['end'] for item in pair.values()) - max(item['start'] for item in pair.values())
        assert overlap > .3, 'different threads did not execute concurrently'
        result['checks']['different_threads'] = {'parallel': True, 'overlap_seconds': round(overlap, 3)}
        stage, interrupt_thread = 'interrupt', thread()
        old = run(interrupt_thread, 'interrupt-old', 10)
        started('interrupt-old')
        new = run(interrupt_thread, 'interrupt-new', .8, 'interrupt')
        old_status = api('GET', f'/threads/{interrupt_thread}/runs/' + old['run_id'])['status']
        assert old_status == 'interrupted', 'old run was not interrupted'
        with psycopg.connect(os.environ['DATABASE_URL']) as conn:
            assert conn.execute('SELECT claimed_by,lease_expires_at FROM runs WHERE run_id=%s AND user_id=%s',
                                (old['run_id'], owner)).fetchone() == (None, None), 'old lease remains owned'
        completed(interrupt_thread, new)
        pair = {item['label']: item for item in events() if item['label'].startswith('interrupt-')}
        assert pair['interrupt-old']['cancelled'], 'old provider connection was not cancelled'
        assert pair['interrupt-old']['end'] <= pair['interrupt-new']['start'], 'interrupt provider overlap'
        result['checks']['interrupt'] = {'old_status': old_status, 'old_lease_released': True,
            'provider_disconnected_before_replacement': True, 'replacement_status': 'success'}
        result['result'] = 'passed'
    except Exception as exc:
        result.update(stage=stage, error_type=type(exc).__name__, error=str(exc)[:400])
    finally:
        cleanup_errors = []
        for tid in threads:
            try:
                for value in api('GET', f'/threads/{tid}/runs?limit=100'):
                    if value['status'] in ('pending', 'running'):
                        api('POST', f'/threads/{tid}/runs/{value["run_id"]}/cancel?wait=1&action=interrupt')
                api('DELETE', '/threads/' + tid)
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__)
        with psycopg.connect(os.environ['DATABASE_URL']) as conn:
            conn.execute('DELETE FROM thread WHERE thread_id=ANY(%s) AND user_id=%s', (threads, owner))
        with connection() as conn:
            conn.execute('DELETE FROM runtime_records WHERE owner_id=%s', (owner,))
            conn.execute('DELETE FROM agent_sessions WHERE id=%s AND owner_id=%s', (parent, owner))
            conn.execute('DELETE FROM platform_users WHERE id=%s', (owner,))
            assert conn.execute('SELECT count(*) AS n FROM runtime_records WHERE owner_id=%s', (owner,)).fetchone()['n'] == 0
        result['cleanup'] = {'fixture_owner_removed': True, 'fixture_threads_removed': len(threads), 'errors': cleanup_errors}
        if cleanup_errors:
            result['result'] = 'failed'
    print('MULTITASK_RESULT=' + json.dumps(result))
    return result['result'] == 'passed'


if __name__ == '__main__':
    if sys.argv[1:2] == ['--inside-container']:
        raise SystemExit(0 if verify(int(sys.argv[2])) else 1)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    server.lock, server.events = threading.RLock(), []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        checked = subprocess.run(['docker', 'exec', '-i', 'showdoc-async-agent-agent-runtime-1', 'python', '-',
            '--inside-container', str(server.server_port)], input=Path(__file__).read_text(), text=True,
            capture_output=True, timeout=180)
        payloads = [line.removeprefix('MULTITASK_RESULT=') for line in checked.stdout.splitlines() if line.startswith('MULTITASK_RESULT=')]
        result = json.loads(payloads[-1]) if payloads else {'result': 'failed', 'stage': 'container-process',
            'exit_code': checked.returncode, 'error': checked.stderr[-1500:]}
        result['provider'] = [{k: v for k, v in item.items() if k != 'socket'} for item in server.events]
        destination = Path('output/verification/deepagents-native-implementation-20261117/async-multitask.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['result'] == 'passed' else 1)
    finally:
        server.shutdown()
        server.server_close()
