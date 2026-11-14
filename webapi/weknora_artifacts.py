"""Artifact metadata and bytes projected from native checkpoint history only."""
from pathlib import PurePosixPath

from agent.artifacts import download
from webapi.weknora_adapter import assistant_id, message_dict


async def collect(graph, config, owner_id, session_id):
    # shortcut: derive versions by scanning checkpoints; revisit if long-chat history reads become slow.
    snapshots = [state async for state in graph.aget_state_history(config)]
    turns, previous = {}, {}
    for state in reversed(snapshots):
        users = [message_dict(message) for message in state.values.get('messages', [])
                 if getattr(message, 'type', None) == 'human']
        if not users:
            continue
        identifier = assistant_id(users[-1])
        files = {path: item for path, item in state.values.get('files', {}).items()
                 if not path.startswith(('/attachments/', '/skills/')) and path != '/AGENTS.md'}
        recorded = turns.setdefault(identifier, {})
        for path, item in files.items():
            if item == previous.get(path):
                continue
            old = recorded.get(path)
            name = PurePosixPath(path)
            metadata = {'index': old[0]['index'] if old else len(recorded), 'file_name': name.name,
                'file_type': name.suffix.lstrip('.').lower(), 'source_path': path,
                'file_size': len(download(owner_id, session_id, path, item)),
                'created_at': item.get('created_at') or state.created_at,
                'mod_time': item.get('modified_at') or state.created_at}
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
        return await collect(graph, {'configurable': {'thread_id': selected['id']}}, user['id'], selected['id'])
