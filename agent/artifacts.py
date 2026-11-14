"""Download archived StateBackend file versions without executing a legacy runtime."""
import base64
import hashlib
import json

from deepagents.backends.utils import file_data_to_string

from agent import sessions
from governance.store import StoreError


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
    try:
        value = file_data_to_string(item)
        if item.get('encoding', 'utf-8') == 'utf-8':
            return value.encode('utf-8')
        if item['encoding'] == 'base64':
            return base64.b64decode(value, validate=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise StoreError('文件编码无效', 409) from exc
    raise StoreError('文件编码无效', 409)
