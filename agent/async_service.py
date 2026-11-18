"""Aegra authentication and a factory for the existing official DeepAgents graph."""
from contextlib import asynccontextmanager

import anyio
from langchain.agents.middleware import AgentMiddleware
from langgraph_sdk import Auth
from langgraph_sdk.runtime import ServerRuntime

from agent import async_runtime
from agent.credentials import cipher
from governance.store import StoreError

auth = Auth()


class _SkillFiles(AgentMiddleware):
    def __init__(self, owner_id, config, backend):
        self.owner_id, self.config, self.backend = owner_id, config, backend

    async def abefore_agent(self, state, runtime):
        from agent.harness_config import prepare_harness_files
        from agent.sandbox import upload_skill_files
        files = await anyio.to_thread.run_sync(lambda: prepare_harness_files(
            self.owner_id, self.config, state.get('files', {})))
        if self.backend is not None:
            await upload_skill_files(self.backend, files)
        return {'files': files} if files else None


@auth.authenticate
async def authenticate(headers: dict):
    token = headers.get('authorization', headers.get('Authorization', '')).removeprefix('Bearer ').strip()
    try:
        user, grant = await anyio.to_thread.run_sync(lambda: async_runtime.principal(token))
    except StoreError:
        raise Auth.exceptions.HTTPException(status_code=401, detail='Invalid agent delegation') from None
    return {'identity': user['id'], 'grant_id': grant['id'],
            'parent_session_id': grant['parent_session_id'], 'subagent_name': grant['subagent_name']}


@auth.on
async def authorize(ctx, value):
    if ctx.resource == 'assistants':
        return ctx.action in ('read', 'search')
    if ctx.resource != 'threads':
        return False
    scope = {'parent_thread_id': ctx.user.parent_session_id, 'subagent_name': ctx.user.subagent_name}
    thread_id = value.get('thread_id')
    if thread_id:
        saved = await _thread_scope(thread_id, ctx.user.identity)
        if saved is None and ctx.action != 'create':
            return False
        if saved is not None and any(saved.get(key) != expected for key, expected in scope.items()):
            return False
    if ctx.action == 'create':
        value['metadata'] = {**(value.get('metadata') or {}), **scope}
        value['metadata']['delegation_id'] = ctx.user.grant_id
        return None
    if not thread_id and ctx.action not in ('search', 'count'):
        # Bulk run cancellation is owner-wide upstream and does not apply filters.
        return False
    metadata = value.get('metadata') or {}
    if ctx.action == 'update' and any(key in metadata for key in (*scope, 'delegation_id')):
        return False
    return {'metadata': scope}


async def _thread_scope(thread_id, identity):
    # Some Aegra endpoints authorize but do not apply returned metadata filters.
    from aegra_api.core.database import db_manager
    async with db_manager.lg_pool.connection() as conn:
        cursor = await conn.execute('SELECT metadata_json FROM thread WHERE thread_id=%s AND user_id=%s',
                                    (thread_id, identity))
        row = await cursor.fetchone()
    return row['metadata_json'] if row else None


@asynccontextmanager
async def graph(config: dict, runtime: ServerRuntime):
    from agent.graph import build_agent
    user_data = runtime.user
    if user_data is None:
        # Aegra inspects graph channels at startup; schema reads never execute tools.
        yield await build_agent(None, api_key='', owner_id='schema-reader', load_tools=False,
            agent_config={'subagents': [{'name': 'schema', 'description': 'Schema only'}]},
            delegated_subagent='schema', additional_middleware=[_SkillFiles('schema-reader', {}, None)])
        return
    identity = user_data.identity if hasattr(user_data, 'identity') else user_data['identity']
    grant_id = user_data.grant_id if hasattr(user_data, 'grant_id') else user_data['grant_id']
    from agent import registry
    grant = await anyio.to_thread.run_sync(lambda: registry.record(async_runtime.GRANT_KIND, grant_id, identity))
    sid = str(config.get('configurable', {}).get('thread_id', ''))
    if sid:
        metadata = await _thread_scope(sid, identity)
        origin = (metadata or {}).get('delegation_id')
        if not isinstance(origin, str):
            raise StoreError('异步线程缺少授权绑定', 403)
        original = await anyio.to_thread.run_sync(lambda: registry.record(async_runtime.GRANT_KIND, origin, identity))
        if (original['parent_session_id'], original['subagent_name']) != (grant['parent_session_id'], grant['subagent_name']):
            raise StoreError('异步线程不属于当前授权范围', 403)
        grant = original
    user, _ = await anyio.to_thread.run_sync(lambda: async_runtime.principal(
        async_runtime.headers(grant)['Authorization'].removeprefix('Bearer ')))
    execution = runtime.execution_runtime is not None
    key = cipher().decrypt(user['contextdb_key_encrypted'].encode()).decode() if user.get('contextdb_key_encrypted') else ''
    if execution and grant['knowledge_base_ids'] and not key:
        raise StoreError('当前成员未绑定知识库凭据', 403)
    from agent.checkpointer import async_store
    from agent.sandbox import backend_for_session
    child = next(child for child in grant['agent_config']['subagents'] if child['name'] == grant['subagent_name'])
    child_config = {**grant['agent_config'], 'access_level': child.get('access_level', grant['agent_config']['access_level'])}
    if grant['agent_config']['access_level'] == 'read_only':
        child_config['access_level'] = 'read_only'
    if not sid and execution:
        raise StoreError('异步执行缺少原生线程标识', 400)
    async with async_store() as store:
        async with backend_for_session(sid, identity, child_config, user['role']) if execution else _no_backend() as backend:
            child_graph = await build_agent(None, api_key=key, owner_id=identity, role=user['role'],
                knowledge_base_ids=grant['knowledge_base_ids'], knowledge_ids=grant['knowledge_ids'],
                tag_scopes=grant['tag_scopes'], agent_config=grant['agent_config'],
                session_id=sid, agent_id=grant['agent_id'], load_tools=execution, store=store,
                backend=backend, delegated_subagent=grant['subagent_name'],
                additional_middleware=[_SkillFiles(identity, grant['agent_config'], backend)])
            if execution:
                from aegra_api.core.database import db_manager
                from langgraph.constants import CONFIG_KEY_CHECKPOINTER
                from agent.checkpointer import WorkspaceCheckpointer
                # Aegra owns the child database. Lend the graph its quota-aware saver for this run.
                saver = WorkspaceCheckpointer(db_manager.lg_pool)
                saver.parent_session_id = grant['parent_session_id']
                child_graph = child_graph.with_config(configurable={CONFIG_KEY_CHECKPOINTER: saver})
            yield child_graph


@asynccontextmanager
async def _no_backend():
    yield None
