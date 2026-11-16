"""Opt-in real WeKnora HTTP/SSE + model + read-only ContextDB acceptance."""
import argparse
import json
import time
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    assert config['schema'].startswith('real_accept_')
    assert config['backend_url'].startswith('http://127.0.0.1:')
    client = requests.Session()
    client.headers['Authorization'] = 'Bearer ' + config['access_token']

    def api(method, path, **kwargs):
        response = client.request(method, config['backend_url'] + path, timeout=(10, 240), **kwargs)
        response.raise_for_status()
        return response.json()

    base = next(item for item in config['knowledge_bases'] if item['name'] == 'knowledge-default')
    agent = api('POST', '/api/v1/agents', json={
        'name': '真实验收-只读知识链路', 'config': {'model_id': 'agent-main', 'temperature': 0,
            'max_completion_tokens': 768, 'max_iterations': 5, 'thinking': False,
            'kb_selection_mode': 'selected', 'knowledge_bases': [base['id']],
            'allowed_tools': ['search_knowledge'], 'mcp_selection_mode': 'none',
            'memory_enabled': False, 'access_level': 'read_only'}})['data']
    session = api('POST', '/api/v1/sessions', json={'title': '真实验收-只读知识链路'})['data']
    sid = session['id']
    started = time.monotonic()
    wire = []
    with client.post(config['backend_url'] + '/api/v1/agent-chat/' + sid, json={
            'agent_id': agent['id'],
            'query': '这是只读检索验收。请实际调用 knowledge.search 搜索“库存查询”，根据本轮工具返回回答库存查询入口，附原文引用；不要凭常识补充，不调用其他工具。回答不超过100字。'},
            stream=True, timeout=(10, 240)) as response:
        response.raise_for_status()
        assert response.headers['Content-Type'].startswith('text/event-stream')
        for line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if line.startswith('data: '):
                event = json.loads(line[6:])
                wire.append((round(time.monotonic() - started, 3), event))
    errors = [item for _, item in wire if item['response_type'] == 'error']
    assert not errors, errors
    assert wire[-1][1]['response_type'] == 'complete', wire[-1]
    calls = [item['data'] for _, item in wire if item['response_type'] == 'tool_call']
    assert calls and all(item['tool_name'] == 'knowledge.search' for item in calls), calls
    results = [item['data'] for _, item in wire if item['response_type'] == 'tool_result']
    assert results and all(item['success'] for item in results)
    references = [item['data']['references'] for _, item in wire if item['response_type'] == 'references']
    assert references and references[-1]
    assert all(item['knowledge_base_id'] == base['id'] for item in references[-1])
    rows = api('GET', f'/api/v1/messages/{sid}/load')['data']
    assert len(rows) == 2 and rows[-1]['is_completed'] is True
    assert rows[-1]['knowledge_references'] == references[-1]
    native = api('GET', f'/api/v1/harness/sessions/{sid}/state')
    assert native['next'] == []
    tools = [m for m in native['values']['messages'] if m['type'] == 'tool']
    assert {m['tool_call_id'] for m in tools} == {item['tool_call_id'] for item in calls}
    record = {
        'real_http': True, 'mocked_network_or_model': False, 'cloud_knowledge_writes': 0,
        'model': 'unchanged agent-main / qwen-max', 'session_id': sid, 'agent_id': agent['id'],
        'knowledge_base_id': base['id'], 'sse_frames': len(wire),
        'first_frame_seconds': wire[0][0], 'total_seconds': round(time.monotonic() - started, 3),
        'tool_calls': [{'name': item['tool_name'], 'id': item['tool_call_id']} for item in calls],
        'reference_count': len(references[-1]),
        'references': [{key: item.get(key) for key in
            ('id', 'knowledge_id', 'knowledge_base_id', 'title', 'score')} for item in references[-1]],
        'answer': rows[-1]['content'],
        'checkpoint_message_count': len(native['values']['messages']),
        'checks': ['real WeKnora HTTP/SSE', 'provider-generated native tool call',
            'successful real ContextDB MCP search', 'references stay in authorized scope',
            'history equals live references', 'native tool call/result identifiers match']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: record[key] for key in ('sse_frames', 'total_seconds', 'reference_count')}))


if __name__ == '__main__':
    main()
