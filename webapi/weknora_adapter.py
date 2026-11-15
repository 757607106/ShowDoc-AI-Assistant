"""WeKnora wire projections of official LangGraph messages; no execution state."""
from types import SimpleNamespace

from agent.citations import AnswerCitations


def text(content):
    if isinstance(content, str):
        return content
    return ''.join(part.get('text', '') for part in content or [] if isinstance(part, dict)
                   and part.get('type') in (None, 'text', 'output_text'))


def message_dict(message):
    return message.model_dump(mode='json') if hasattr(message, 'model_dump') else message


def reasoning_text(message):
    """Project visible reasoning without exposing signatures or encrypted replay data."""
    kwargs = message.get('additional_kwargs', {})
    if isinstance(kwargs.get('reasoning_content'), str):
        return kwargs['reasoning_content']
    blocks = kwargs.get('thinking_blocks') or message.get('content') or []
    if isinstance(blocks, str):
        return ''
    return ''.join(block.get('reasoning') or block.get('thinking') or '' for block in blocks
                   if isinstance(block, dict) and block.get('type') in ('reasoning', 'thinking'))


def assistant_id(message):
    return 'assistant:' + message['id']


def pending_calls(state):
    messages = [message_dict(message) for message in state.values.get('messages', [])]
    start = max((index for index, message in enumerate(messages) if message.get('type') == 'human'), default=-1)
    current = messages[start + 1:]
    completed = {message.get('tool_call_id') for message in current if message.get('type') == 'tool'}
    return [call for message in current for call in message.get('tool_calls', []) if call['id'] not in completed]


def tool_result(message, arguments=None):
    from webapi.chat_suggestions import _structured, _tool_succeeded
    output = text(message.get('content'))
    native_message = SimpleNamespace(**message)
    native = _structured(native_message)
    result = {'tool_call_id': message['tool_call_id'], 'tool_name': message.get('name', ''),
              'success': _tool_succeeded(native_message, native), 'output': output}
    if not result['success']:
        result['error'] = output
    if isinstance(native, dict):
        result['data'] = native
    if message.get('name') == 'write_todos':
        todos = (arguments or {}).get('todos', []) if result['success'] else []
        result.update(tool_name='todo_write', display_type='plan', total_steps=len(todos),
            steps=[{'id': str(index), 'description': todo['content'], 'status': todo['status']}
                   for index, todo in enumerate(todos)])
    if message.get('name') == 'ask_user':
        result['data'] = {'display_type': 'ask_user', 'question': arguments or {},
                          'answered': not native.get('declined', False), 'answer': native}
    return result


def history(state, session_id, knowledge_base_ids=()):
    """Group native messages by user turn, preserving every tool call identifier."""
    rows, current, tools = [], None, {}
    citations = AnswerCitations(knowledge_base_ids)
    for raw in state.values.get('messages', []):
        message = message_dict(raw)
        kind = message.get('type', message.get('role'))
        if kind in ('human', 'user'):
            metadata = message.get('additional_kwargs', {}).get('harness', {})
            rows.append({'id': message['id'], 'session_id': session_id, 'role': 'user',
                'content': metadata.get('display_text', text(message.get('content'))),
                'created_at': metadata.get('created_at'), 'is_completed': True,
                'mentioned_items': metadata.get('mentioned_items', []),
                'images': metadata.get('user_images', []), 'attachments': metadata.get('attachments', [])})
            current = {'id': assistant_id(message), 'assistant_message_id': assistant_id(message),
                'request_id': assistant_id(message), 'session_id': session_id, 'role': 'assistant',
                'created_at': metadata.get('created_at'), 'content': '', 'agent_steps': [],
                'is_completed': True, 'knowledge_references': []}
            rows.append(current)
            tools = {}
            citations = AnswerCitations(metadata.get('knowledge_base_ids', knowledge_base_ids))
        elif current is not None and kind in ('ai', 'assistant'):
            calls = message.get('tool_calls', [])
            step = {'iteration': len(current['agent_steps']), 'tool_calls': []}
            if calls:
                step['thought'] = text(message.get('content'))
                current['content'] = ''
            else:
                current['content'] += text(message.get('content'))
            reasoning = reasoning_text(message)
            if reasoning:
                step['reasoning_content'] = reasoning
            for call in calls:
                projected = {**call, 'name': 'todo_write' if call['name'] == 'write_todos' else call['name']}
                step['tool_calls'].append(projected)
                tools[call['id']] = projected
            current['agent_steps'].append(step)
        elif current is not None and kind == 'tool':
            call = tools.get(message['tool_call_id'])
            result = tool_result(message, call.get('args') if call else None)
            if call is not None:
                call['result'] = {**result, 'data': {**result.get('data', {}),
                    **{key: value for key, value in result.items() if key != 'data'}}}
            citations.register(message.get('name'), result.get('data'), result['success'])
            current['knowledge_references'] = list(citations.references)
    if current is not None and (state.next or state.interrupts):
        current['is_completed'] = False
        current['run_state'] = 'awaiting_input' if state.interrupts else 'interrupted'
    return rows


class StreamProjection:
    """Translate one request's native stream; discard child graph answer channels."""
    def __init__(self, session_id, identifier, knowledge_base_ids=()):
        self.session_id, self.identifier = session_id, identifier
        self.calls = {}
        self.child_calls = []
        self.citations = AnswerCitations(knowledge_base_ids)

    def event(self, kind, content='', data=None, done=False):
        return {'response_type': kind, 'id': self.identifier, 'assistant_message_id': self.identifier,
                'session_id': self.session_id, 'content': content, 'data': data or {}, 'done': done}

    def feed(self, part):
        if part['ns']:
            if part['type'] == 'updates':
                for update in part['data'].values():
                    if isinstance(update, dict):
                        for raw in update.get('messages', []):
                            message = message_dict(raw)
                            self.child_calls.extend(message.get('tool_calls', []))
            return []
        events = []
        if part['type'] == 'messages':
            raw, metadata = part['data']
            message = message_dict(raw)
            if message.get('type') not in ('ai', 'AIMessageChunk') or metadata.get('langgraph_node') != 'model':
                return []
            identifier = message.get('id', '')
            reasoning = reasoning_text(message)
            if reasoning:
                events.append(self.event('thinking', reasoning, {'event_id': identifier + ':thinking'}))
            if text(message.get('content')):
                events.append(self.event('answer', text(message['content']), {'event_id': identifier}))
        elif part['type'] == 'updates':
            for update in part['data'].values():
                if not isinstance(update, dict):
                    continue
                messages = update.get('messages', [])
                for raw in messages if isinstance(messages, list) else [messages]:
                    message = message_dict(raw)
                    if not isinstance(message, dict):
                        continue
                    kind, identifier = message.get('type'), message.get('id', '')
                    if kind == 'ai':
                        if text(message.get('content')):
                            events.append(self.event('answer', text(message['content']),
                                {'event_id': identifier, 'replace': True}, done=True))
                        for call in message.get('tool_calls', []):
                            if call['id'] not in self.calls:
                                self.calls[call['id']] = call
                                events.append(self.event('tool_call', data={'tool_call_id': call['id'],
                                    'tool_name': 'todo_write' if call['name'] == 'write_todos' else call['name'],
                                    'arguments': call['args']}))
                    elif kind == 'tool':
                        call = self.calls.get(message['tool_call_id'], {})
                        result = tool_result(message, call.get('args'))
                        self.citations.register(message.get('name'), result.get('data'), result['success'])
                        events.append(self.event('tool_result', data=result))
                        if self.citations.references:
                            events.append(self.event('references', data={'references': list(self.citations.references)}))
        return events
