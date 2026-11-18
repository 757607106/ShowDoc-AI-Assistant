"""Artifact versions from checkpoint history and native current-file deletion."""
from pathlib import PurePosixPath

from agent.artifacts import artifact_key, deleted_for, download, is_artifact
from agent.time_travel import ancestry
from webapi.weknora_adapter import assistant_id, media_files, message_dict


def collect(snapshots, owner_id, session_id):
    turns, previous = {}, {}
    deleted = deleted_for(owner_id, session_id)
    for state in reversed(snapshots):
        users = [message_dict(message) for message in state.values.get('messages', [])
                 if getattr(message, 'type', None) == 'human']
        if not users:
            continue
        identifier = assistant_id(users[-1])
        files = {path: item for path, item in {**media_files(state.values.get('messages', [])),
                                              **state.values.get('files', {})}.items()
                 if is_artifact(path)}
        recorded = turns.setdefault(identifier, {})
        for path, item in files.items():
            if item == previous.get(path):
                continue
            old = recorded.get(path)
            name = PurePosixPath(path)
            version_key = artifact_key(session_id, path, item)
            metadata = {'index': old[0]['index'] if old else len(recorded), 'file_name': name.name,
                'file_type': name.suffix.lstrip('.').lower(), 'source_path': path,
                'created_at': item.get('created_at') or state.created_at,
                'mod_time': item.get('modified_at') or state.created_at}
            if version_key in deleted:
                metadata['deleted_at'] = deleted[version_key]
            else:
                metadata['file_size'] = len(download(owner_id, session_id, path, item))
            recorded[path] = (metadata, item)
        for path in recorded.keys() - files.keys():
            recorded[path][0]['deleted_at'] = state.created_at
        previous = files
    return {identifier: list(recorded.values()) for identifier, recorded in turns.items()}


async def read(user, selected):
    from agent.checkpointer import async_checkpointer
    from webapi.harness import _graph
    resolved = selected['agent_config']
    if not resolved.get('agent_config'):
        return {}
    async with async_checkpointer() as saver:
        graph = await _graph(saver, user, selected, resolved, load_tools=False)
        head = await graph.aget_state({'configurable': {'thread_id': selected['id']}})
        return collect([state async for state in ancestry(graph, head)], user['id'], selected['id'])


async def delete(user, selected, message_id, index, *, all_versions=False):
    from langgraph.graph import END
    from agent import registry
    from agent.checkpointer import async_checkpointer
    from governance.database import connection
    from governance.store import StoreError, now
    from webapi.harness import _graph

    owner, sid = user['id'], selected['id']
    if not selected['agent_config'].get('agent_config'):
        raise StoreError('文件不存在或已删除', 404)
    async with async_checkpointer() as saver:
        graph = await _graph(saver, user, selected, selected['agent_config'], load_tools=False)
        config = {'configurable': {'thread_id': sid}}
        state = await graph.aget_state(config)
        if state.next or state.interrupts:
            raise StoreError('会话尚未完成，请先完成或取消当前请求', 409)
        turns = collect([snapshot async for snapshot in ancestry(graph, state)], owner, sid)
        target = next(((meta, item) for meta, item in turns.get(message_id, []) if meta['index'] == index), None)
        if target is None:
            raise StoreError('文件不存在或已删除', 404)
        metadata, item = target
        path = metadata['source_path']
        existing = deleted_for(owner, sid)
        target_key = artifact_key(sid, path, item)
        version_keys = ({artifact_key(sid, path, version) for versions in turns.values()
                         for meta, version in versions if meta['source_path'] == path}
                        if all_versions else {target_key})
        if metadata.get('deleted_at'):
            if target_key not in existing:
                raise StoreError('文件不存在或已删除', 404)
            # Retry only already-deleted versions; a regenerated file must survive cleanup.
            version_keys &= existing.keys()
        current = state.values.get('files', {}).get(path)
        remove_current = current is not None and artifact_key(sid, path, current) in version_keys
        pending = version_keys - existing.keys()
        if not pending and not remove_current:
            raise StoreError('文件不存在或已删除', 404)
        deleted_at = now()
        with connection() as conn:
            from governance.workspaces import set_file_sizes
            set_file_sizes(conn, owner, {'artifact:' + key: 0 for key in pending})
            for key in pending:
                registry.save_record('artifact_deleted',
                    {'id': key, 'session_id': sid, 'deleted_at': deleted_at}, owner, _connection=conn)
        if remove_current:
            # Use StateBackend's native None deletion reducer; preserve historical checkpoints.
            try:
                updated = await graph.aupdate_state(state.config, {'files': {path: None}}, as_node='model')
                await graph.aupdate_state(updated, None, as_node=END)
            except Exception as exc:
                raise StoreError('产物记录已删除，但文件清理失败，请重试删除', 503) from exc
    return {'file_name': metadata['file_name'], 'deleted': len(pending)}
