"""Checkpoint selection and state-only branching through native LangGraph APIs."""
from langgraph.graph import END

from governance.store import StoreError


async def ancestry(graph, state):
    # shortcut: walk the native parent chain; paginate if long-thread reads become slow.
    while state.config.get('configurable', {}).get('checkpoint_id'):
        yield state
        if not state.parent_config:
            break
        state = await graph.aget_state(state.parent_config)


async def select(graph, session_id, message_id, *, rewind=False):
    from webapi.weknora.adapter import history
    head = await graph.aget_state({'configurable': {'thread_id': session_id}})
    states = [state async for state in ancestry(graph, head)]
    if not states:
        raise StoreError('会话没有可用检查点', 409)
    if head.next or head.interrupts:
        raise StoreError('会话尚未完成，请先完成或取消当前请求', 409)
    rows = history(head, session_id)
    selected = next((row for row in rows if row['id'] == message_id), None)
    if selected is None:
        raise StoreError('消息不存在', 404)
    if rewind and selected is rows[-1]:
        raise StoreError('回退到最新回答不会删除消息', 409)
    users = [m.id for m in head.values.get('messages', []) if m.type == 'human']
    human_id = message_id if selected['role'] == 'user' else message_id.removeprefix('assistant:')
    count = users.index(human_id) + (selected['role'] == 'assistant')
    prefix = users[:count]
    for state in states:
        identifiers = [m.id for m in state.values.get('messages', []) if m.type == 'human']
        if identifiers == prefix and (not state.next and not state.interrupts or not prefix):
            return state, len(rows) - rows.index(selected) - (selected['role'] == 'assistant')
    raise StoreError('选中消息缺少完整检查点，无法恢复', 409)


async def seed(graph, source, session_id):
    if not source.values.get('messages'):
        return
    # A new thread loads the latest native memory file on its next invocation.
    # The target is a new empty thread; LastValue channels must receive their native value.
    values = {key: value for key, value in source.values.items()
              if key not in ('memory_contents', '__interrupt__', 'async_tasks')}
    config = await graph.aupdate_state({'configurable': {'thread_id': session_id}}, values, as_node='model')
    await graph.aupdate_state(config, None, as_node=END)


async def rewind(graph, source):
    config = await graph.aupdate_state(source.config, None, as_node='__copy__')
    # Clearing scheduled tasks also handles the empty checkpoint before the first question.
    await graph.aupdate_state(config, None, as_node=END)
