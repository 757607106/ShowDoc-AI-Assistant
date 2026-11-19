"""WeKnora wire projections of official LangGraph messages; no execution state."""
from types import SimpleNamespace

from agent.artifacts import answer_blocks, media_file, media_files, message_dict
from agent.citations import AnswerCitations
from governance.knowledge_names import KnowledgeNames


def _knowledge_names(owner_id=None):
    from webapi.auth import user_id
    owner = owner_id or user_id()
    return KnowledgeNames(owner) if owner else None


def _reference_views(citations, names):
    if names is None:
        return list(citations.references)
    return [{**reference, 'document_display_name': reference.get('document_display_name') or names.document({**reference,
        'document_id': reference['knowledge_id'], 'document_name': reference['knowledge_filename']},
        reference=True)['document_display_name']} for reference in citations.references]


def _register_citations(citations, tool_name, data, success):
    previous = len(citations.references)
    citations.register(tool_name, data, success)
    chunks = data.get('results', data.get('chunks', [])) if isinstance(data, dict) else []
    for reference in citations.references[previous:]:
        for chunk in chunks:
            if (isinstance(chunk, dict) and chunk.get('document_display_name')
                    and (chunk.get('knowledge_base_id') or chunk.get('kb_id')) == reference['knowledge_base_id']
                    and (chunk.get('document_id') or chunk.get('doc_id')) == reference['knowledge_id']
                    and chunk.get('chunk_id') == reference['id']):
                reference['document_display_name'] = chunk['document_display_name']
                break


def text(content):
    if isinstance(content, str):
        return content
    return ''.join(part.get('text', '') for part in content or [] if isinstance(part, dict)
                   and part.get('type') in (None, 'text', 'output_text'))


def answer_content(message):
    """Keep SDK answer blocks and reuse Markdown images and native artifact downloads."""
    if not isinstance(message.get('content'), list):
        return text(message.get('content')), []
    from urllib.parse import quote, urlsplit
    blocks = answer_blocks(message)
    output = []
    for index, block in enumerate(blocks):
        kind = block.get('type')
        if kind == 'text':
            output.append(block.get('text', ''))
            continue
        if item := media_file(message, index, block):
            output.append(f'\n\n[{kind}](sandbox:{item[0]})\n\n')
            continue
        url = block.get('url')
        if not url and block.get('base64') and block.get('mime_type'):
            url = f"data:{block['mime_type']};base64,{block['base64']}"
        if not isinstance(url, str):
            continue
        try:
            scheme = urlsplit(url).scheme.lower()
        except ValueError:
            continue
        if scheme not in ('http', 'https', 'data') and not url.startswith('/'):
            continue
        if scheme == 'data' and not url.startswith(('data:image/', 'data:audio/', 'data:video/', 'data:application/')):
            continue
        if scheme == 'data' and kind != 'image':
            continue
        destination = quote(url, safe=':/?#=&;,[]%+@')
        output.append(f'\n\n![image]({destination})\n\n' if kind == 'image'
                      else f'\n\n[{kind}]({destination})\n\n')
    return ''.join(output), blocks


def reasoning_text(message):
    """Project visible reasoning without exposing signatures or encrypted replay data."""
    kwargs = message.get('additional_kwargs', {})
    if isinstance(kwargs.get('reasoning_content'), str):
        return kwargs['reasoning_content']
    blocks = kwargs.get('thinking_blocks') or message.get('content') or []
    if isinstance(blocks, str):
        return ''
    parts = []
    for block in blocks:
        if isinstance(block, dict) and block.get('type') in ('reasoning', 'thinking'):
            summary = ''.join(item.get('text', '') for item in block.get('summary', []) if isinstance(item, dict))
            parts.append(block.get('reasoning') or block.get('thinking') or summary)
    return ''.join(parts)


def assistant_id(message):
    return 'assistant:' + message['id']


def pending_calls(state):
    messages = [message_dict(message) for message in state.values.get('messages', [])]
    start = max((index for index, message in enumerate(messages) if message.get('type') == 'human'), default=-1)
    current = messages[start + 1:]
    completed = {message.get('tool_call_id') for message in current if message.get('type') == 'tool'}
    return [call for message in current for call in message.get('tool_calls', []) if call['id'] not in completed]


def tool_display_name(name):
    return {'write_todos': 'todo_write', 'execute': 'shell_exec'}.get(name, name)


def tool_result(message, arguments=None, names=None):
    from webapi.chat.chat_suggestions import _structured, _tool_succeeded
    output = text(message.get('content'))
    native_message = SimpleNamespace(**message)
    native = _structured(native_message)
    result = {'tool_call_id': message['tool_call_id'], 'tool_name': tool_display_name(message.get('name', '')),
              'success': _tool_succeeded(native_message, native), 'output': output}
    if not result['success']:
        result['error'] = output
    if isinstance(native, dict):
        result['data'] = native
        resource = {
            'knowledge.list_bases': 'knowledge/knowledge_bases',
            'knowledge.get_base': 'knowledge/knowledge_bases/detail',
            'knowledge.list_documents': 'knowledge/documents',
            'knowledge.get_document': 'knowledge/documents/detail',
            'knowledge.search': 'knowledge/query',
            'knowledge.list_entity_chunks': 'knowledge/entities/chunks',
        }.get(message.get('name'))
        if names is not None and resource:
            result['data'] = names.present(resource, native, kb_id=(arguments or {}).get('knowledge_base_id'))
    if message.get('name') == 'execute':
        artifact = message.get('artifact')
        metadata = artifact if isinstance(artifact, dict) else native
        # HITL keeps requested arguments; its native result explains reviewer edits.
        result.update(display_type='shell_exec', command=(arguments or {}).get('command', ''))
        result.update({key: metadata[key] for key in ('exit_code', 'truncated') if key in metadata})
    if message.get('name') == 'write_todos':
        todos = (arguments or {}).get('todos', []) if result['success'] else []
        result.update(display_type='plan', total_steps=len(todos),
            steps=[{'id': str(index), 'description': todo['content'], 'status': todo['status']}
                   for index, todo in enumerate(todos)])
    if message.get('name') == 'ask_user':
        result['data'] = {'display_type': 'ask_user', 'question': arguments or {},
                          'answered': not native.get('declined', False), 'answer': native}
    return result


def history(state, session_id, knowledge_base_ids=(), *, owner_id=None):
    """Group native messages by user turn, preserving every tool call identifier."""
    rows, current, tools = [], None, {}
    citations = AnswerCitations(knowledge_base_ids)
    names = _knowledge_names(owner_id)
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
            if metadata.get('interactions'):
                current['delegated_prompts'] = metadata['interactions']
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
                rendered, blocks = answer_content(message)
                current['content'] += rendered
                if blocks:
                    current.setdefault('content_blocks', []).extend(blocks)
            reasoning = reasoning_text(message)
            if reasoning:
                step['reasoning_content'] = reasoning
            for call in calls:
                projected = {**call, 'name': tool_display_name(call['name'])}
                step['tool_calls'].append(projected)
                tools[call['id']] = projected
            current['agent_steps'].append(step)
        elif current is not None and kind == 'tool':
            call = tools.get(message['tool_call_id'])
            result = tool_result(message, call.get('args') if call else None, names)
            if call is not None:
                call['result'] = {**result, 'data': {**result.get('data', {}),
                    **{key: value for key, value in result.items() if key != 'data'}}}
            _register_citations(citations, message.get('name'), result.get('data'), result['success'])
            current['knowledge_references'] = _reference_views(citations, names)
    if current is not None and (state.next or state.interrupts):
        current['is_completed'] = False
        current['run_state'] = 'awaiting_input' if state.interrupts else 'interrupted'
    return rows


async def structured_outputs(snapshots, checkpointer):
    results, completed = {}, set()
    for state in snapshots:
        users = [message_dict(message) for message in state.values.get('messages', [])
                 if getattr(message, 'type', None) == 'human']
        if not users or not users[-1].get('additional_kwargs', {}).get('harness', {}).get('structured_output'):
            continue
        identifier = assistant_id(users[-1])
        if not state.next and not state.interrupts:
            completed.add(identifier)
        if identifier not in completed or identifier in results or 'structured_response' not in state.values:
            continue
        current = await checkpointer.aget_tuple(state.config)
        parent = await checkpointer.aget_tuple(state.parent_config) if state.parent_config else None
        # A native channel write distinguishes valid JSON null from a stale or reset value.
        version = current.checkpoint['channel_versions'].get('structured_response') if current else None
        previous = parent.checkpoint['channel_versions'].get('structured_response') if parent else None
        if state.metadata.get('source') == 'loop' and version is not None and version != previous:
            results[identifier] = state.values['structured_response']
    return results


class StreamProjection:
    """Translate one request's native stream; discard child graph answer channels."""
    def __init__(self, session_id, identifier, knowledge_base_ids=(), *, owner_id=None):
        self.session_id, self.identifier = session_id, identifier
        self.calls = {}
        self.child_calls = []
        self.background_work = {}
        self.citations = AnswerCitations(knowledge_base_ids)
        self.names = _knowledge_names(owner_id)
        self.owner_id = self.names.owner_id if self.names else None

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
                for work_id, task in (update.get('async_tasks') or {}).items():
                    current = (task.get('run_id'), task.get('status'))
                    if self.background_work.get(work_id) == current:
                        continue
                    self.background_work[work_id] = current
                    state = {'success': 'succeeded', 'error': 'failed', 'timeout': 'failed',
                             'interrupted': 'cancelled'}.get(task.get('status'), task.get('status', 'running'))
                    event = 'work_finished' if state in ('succeeded', 'failed', 'cancelled') else 'work_started'
                    events.append(self.event(event, data={'work_id': work_id, 'kind': 'async_subagent',
                        'title': task.get('agent_name', ''), 'state': state,
                        'payload': {'run_id': task.get('run_id')}}))
                messages = update.get('messages', [])
                for raw in messages if isinstance(messages, list) else [messages]:
                    message = message_dict(raw)
                    if not isinstance(message, dict):
                        continue
                    kind, identifier = message.get('type'), message.get('id', '')
                    if kind == 'ai':
                        rendered, blocks = answer_content(message) if not message.get('tool_calls') else (text(message.get('content')), [])
                        if rendered:
                            events.append(self.event('answer', rendered,
                                {'event_id': identifier, 'replace': True, **({'content_blocks': blocks} if blocks else {})}, done=True))
                        for call in message.get('tool_calls', []):
                            if call['id'] not in self.calls:
                                self.calls[call['id']] = call
                                events.append(self.event('tool_call', data={'tool_call_id': call['id'],
                                    'tool_name': tool_display_name(call['name']),
                                    'arguments': call['args']}))
                    elif kind == 'tool':
                        call = self.calls.get(message['tool_call_id'], {})
                        result = tool_result(message, call.get('args'), self.names)
                        _register_citations(self.citations, message.get('name'), result.get('data'), result['success'])
                        events.append(self.event('tool_result', data=result))
                        if self.citations.references:
                            events.append(self.event('references', data={'references': _reference_views(self.citations, self.names)}))
        return events
