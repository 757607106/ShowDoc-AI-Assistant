"""Download archived StateBackend file versions without executing a legacy runtime."""
import base64
import hashlib
import json
import mimetypes

from deepagents.backends.utils import file_data_to_string

from agent import sessions
from governance.store import StoreError


def message_dict(message):
    return message.model_dump(mode='json') if hasattr(message, 'model_dump') else message


def answer_blocks(message):
    from deepagents.middleware.async_subagents import _final_content
    return [{key: value for key, value in block.items() if key != 'id'}
            for block in _final_content({'messages': [message]})
            if block.get('type') in ('text', 'image', 'audio', 'video', 'file')]


def media_file(message, index, block):
    if block.get('type') not in ('audio', 'video', 'file'):
        return None
    encoded, mime = block.get('base64'), block.get('mime_type')
    url = block.get('url', '')
    if isinstance(url, str) and url.startswith('data:') and ';base64,' in url:
        mime, encoded = url[5:].split(';base64,', 1)
    if not isinstance(encoded, str) or not isinstance(mime, str) or not message.get('id'):
        return None
    try:
        base64.b64decode(encoded, validate=True)
    except ValueError:
        return None
    identifier = hashlib.sha256(str(message['id']).encode()).hexdigest()[:16]
    mime = mime.split(';', 1)[0].lower()
    extension = '.wav' if mime in ('audio/wav', 'audio/x-wav') else mimetypes.guess_extension(mime) or '.bin'
    path = f'/response-media/{block["type"]}-{identifier}-{index}{extension}'
    return path, {'content': encoded, 'encoding': 'base64'}


def media_files(messages):
    """Read-only artifact projections of bytes already persisted in native messages."""
    result = {}
    for raw in messages:
        message = message_dict(raw)
        if message.get('type', message.get('role')) not in ('ai', 'assistant') or message.get('tool_calls'):
            continue
        if isinstance(message.get('content'), list):
            for index, block in enumerate(answer_blocks(message)):
                if item := media_file(message, index, block):
                    result[item[0]] = item[1]
    return result


def is_artifact(path):
    return path != '/AGENTS.md' and not path.startswith(('/attachments/', '/skills/', '/subagent-skills/',
        '/conversation_history/', '/large_tool_results/', '/workspace/conversation_history/',
        '/workspace/large_tool_results/'))


def file_bytes(item):
    try:
        value = file_data_to_string(item)
        if item.get('encoding', 'utf-8') == 'utf-8':
            return value.encode('utf-8')
        if item['encoding'] == 'base64':
            return base64.b64decode(value, validate=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise StoreError('文件编码无效', 409) from exc
    raise StoreError('文件编码无效', 409)


def artifact_key(session_id, path, item):
    if item.get('_version_key'):
        return session_id + ':' + item['_version_key']
    if item.get('_sandbox') or 'modified_at' in item and 'size' in item:
        item = {'modified_at': item.get('modified_at'), 'file_size': item.get('file_size', item.get('size'))}
    return session_id + ':' + hashlib.sha256(json.dumps([path, item], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def deleted_for(owner_id, session_id):
    from agent import registry
    return {item['id']: item['deleted_at'] for item in registry.records('artifact_deleted', owner_id) if item.get('session_id') == session_id}


def download(owner_id, session_id, path, item):
    if item.get('deleted_at') or artifact_key(session_id, path, item) in deleted_for(owner_id, session_id):
        raise StoreError('文件已删除', 404)
    source = item.get('_source')
    if source:
        if source.get('unavailable') or not source.get('checkpoint_id'):
            raise StoreError('文件版本已不可用', 404)
        from agent.checkpointer import make_checkpointer
        with make_checkpointer() as saver:
            state = sessions.state_reader(saver).get_state({'configurable': {'thread_id': session_id,
                                                                            'checkpoint_id': source['checkpoint_id']}})
        item = state.values.get('files', {}).get(path)
        if not item or artifact_key(session_id, path, item).split(':', 1)[1] != source['version_key']:
            raise StoreError('文件版本已不可用', 404)
    return file_bytes(item)
