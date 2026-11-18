"""ContextDB native MCP knowledge tools, plus owner-scoped platform operations."""
import asyncio
import json
import os

from langchain_core.tools import tool

from governance.store import Store, StoreError
from integrations.contextdb import ContextDBClient


def make_governance_tools(api_key, owner_id, role):
    client = ContextDBClient(api_key=api_key)
    store = Store(client=client, owner_id=owner_id)

    @tool
    def list_governance_releases() -> str:
        """查看本人采集发布批次的标识、范围和同步记录。"""
        return json.dumps(store.list_releases()[:20], ensure_ascii=False)

    @tool
    def get_capture_provenance(version_id: str) -> str:
        """按采集快照标识查看来源、采集任务和版本标识，不返回知识正文。"""
        record = store.get_document(version_id)
        return json.dumps({k: record.get(k) for k in ('title', 'version_id', 'source_key', 'job_id', 'is_current')}, ensure_ascii=False)

    @tool
    def rerun_collection(task_id: str) -> str:
        """重跑本人已配置的数据采集任务。沿用服务端保存的来源与凭据，不能指定新来源。"""
        previous = store.get_job(task_id)
        if previous.get('kind') != 'crawl':
            raise StoreError('只能重跑已配置的采集任务', 400)
        job = store.create_job(previous['entry'], previous['params'], previous.get('selected_ids'),
                               previous.get('selected_titles'), scope=previous['scope'])
        return json.dumps({'task_id': job['task_id'], 'status': job['status']}, ensure_ascii=False)

    tools = [list_governance_releases, get_capture_provenance]
    if role != 'viewer':
        tools.append(rerun_collection)
    return tools


def scoped_arguments(arguments, knowledge_base_ids, properties):
    args = dict(arguments)
    if not knowledge_base_ids:
        raise StoreError('当前会话未选择知识库，知识访问已停止', 403)
    if args.get('knowledge_base_names'):
        raise StoreError('限定知识库的会话必须使用知识库 ID', 400)
    if 'knowledge_base_ids' in properties:
        ids = args.get('knowledge_base_ids') or knowledge_base_ids
        if not isinstance(ids, list) or any(kb not in knowledge_base_ids for kb in ids):
            raise StoreError('工具请求超出当前选择的知识库', 403)
        args['knowledge_base_ids'] = ids
    if 'knowledge_base_id' in properties:
        kb = args.get('knowledge_base_id')
        if not kb and len(knowledge_base_ids) == 1:
            kb = knowledge_base_ids[0]
        if kb not in knowledge_base_ids:
            raise StoreError('请明确选择会话范围内的知识库 ID', 403)
        args['knowledge_base_id'] = kb
    if not set(properties).intersection(('knowledge_base_id', 'knowledge_base_ids', 'document_id', 'document_ids')):
        raise StoreError('该工具无法限定当前会话的知识库范围', 403)
    return args


async def load_knowledge_mcp_tools(*, api_key, role='viewer', owner_id=None, knowledge_base_ids=(), agent_config=None):
    """Discover official schemas; connector tools are outside this platform's knowledge scope."""
    if not knowledge_base_ids:
        return []
    knowledge_base_ids = list(knowledge_base_ids)
    from langchain_mcp_adapters.client import MultiServerMCPClient
    schemas, annotations, allowed = {}, {}, set()
    ownership_client = ContextDBClient(api_key=api_key)
    config = agent_config or {}
    document_bases = config.get('_document_bases', {})
    whole_bases = set(config.get('_whole_knowledge_bases', knowledge_base_ids))
    async def authorize(request, handler):
        if request.name not in allowed:
            raise StoreError('该工具未获当前会话授权', 403)
        if owner_id:
            from governance.database import connection
            with connection() as conn:
                user = conn.execute('SELECT role,active,contextdb_key_encrypted FROM workspace_users WHERE id=%s', (owner_id,)).fetchone()
            from agent.credentials import cipher
            if not user or not user['active'] or not user['contextdb_key_encrypted'] or cipher().decrypt(user['contextdb_key_encrypted'].encode()).decode() != api_key:
                raise StoreError('当前成员凭据已变更或账号已停用，请重新开始执行', 403)
            if user['role'] == 'viewer' and not annotations.get(request.name, {}).get('readOnlyHint'):
                raise StoreError('当前账号没有该工具的写入权限', 403)
            if user['role'] != 'admin' and request.name in ('knowledge.create_base', 'knowledge.delete_base', 'knowledge.update_base'):
                raise StoreError('当前账号没有知识库管理权限', 403)
        arguments = scoped_arguments(request.args, knowledge_base_ids, schemas.get(request.name, {}))
        properties = schemas[request.name]
        requested_bases = set(arguments.get('knowledge_base_ids') or [arguments.get('knowledge_base_id')]) - {None}
        restricted = requested_bases - whole_bases
        if restricted:
            if requested_bases & whole_bases:
                raise StoreError('文档范围和整库范围请分别调用工具，避免扩大检索范围', 400)
            scoped_docs = [document_id for document_id, kb_id in document_bases.items() if kb_id in restricted]
            if 'document_ids' in properties:
                supplied = arguments.get('document_ids') or scoped_docs
                if not isinstance(supplied, list) or not supplied or not set(supplied).issubset(scoped_docs):
                    raise StoreError('工具请求超出所选文档范围', 403)
                arguments['document_ids'] = supplied
            elif 'document_id' in properties:
                supplied = arguments.get('document_id')
                if not supplied and len(scoped_docs) == 1:
                    supplied = scoped_docs[0]
                if supplied not in scoped_docs:
                    raise StoreError('请指定当前范围内的文档', 403)
                arguments['document_id'] = supplied
            else:
                raise StoreError('该官方工具无法限定所选文档范围', 403)
        document_ids = []
        for field in ('document_id', 'document_ids'):
            value = arguments.get(field)
            if value is None:
                continue
            ids = [value] if field == 'document_id' else value
            if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids):
                raise StoreError('文档 ID 必须是非空字符串', 400)
            document_ids.extend(ids)
        if not set(properties).intersection(('knowledge_base_id', 'knowledge_base_ids')) and not document_ids:
            raise StoreError('缺少可验证所属知识库的文档 ID', 403)
        for document_id in dict.fromkeys(document_ids):
            detail = await asyncio.to_thread(ownership_client.get_document, None, document_id)
            if not isinstance(detail, dict) or detail.get('knowledge_base_id') not in knowledge_base_ids:
                raise StoreError('文档不属于当前选择的知识库或无法验证归属', 403)
            if detail['knowledge_base_id'] not in whole_bases and document_id not in document_bases:
                raise StoreError('文档不属于本轮所选文档范围', 403)
        if config.get('access_level') == 'read_only' and not annotations.get(request.name, {}).get('readOnlyHint'):
            raise StoreError('当前会话仅允许读取知识库', 403)
        return await handler(request.override(args=arguments))
    client = MultiServerMCPClient({'contextdb': {
        'transport': 'streamable_http',
        'url': os.getenv('CONTEXTDB_MCP_URL', 'https://context-database.aliyuncs.com/v1/mcp'),
        'headers': {'X-API-Key': api_key},
    }}, tool_interceptors=[authorize])
    discovered = await client.get_tools()
    tools = []
    for candidate in discovered:
        if not candidate.name.startswith('knowledge.'):
            continue
        if agent_config is not None:
            from agent.config import allowed_knowledge_tools
            if candidate.name not in allowed_knowledge_tools(config):
                continue
        schema = candidate.args_schema
        if isinstance(schema, type):
            schema = schema.model_json_schema()
        schemas[candidate.name] = schema.get('properties', {})
        if not set(schemas[candidate.name]).intersection(('knowledge_base_id', 'knowledge_base_ids', 'document_id', 'document_ids')):
            continue
        annotations[candidate.name] = candidate.metadata or {}
        read_only = (candidate.metadata or {}).get('readOnlyHint') is True
        if (role == 'viewer' or config.get('access_level') == 'read_only') and not read_only:
            continue
        if role != 'admin' and candidate.name in ('knowledge.create_base', 'knowledge.delete_base', 'knowledge.update_base'):
            continue
        tools.append(candidate)
        allowed.add(candidate.name)
    if (agent_config is None or 'knowledge.search' in allowed_knowledge_tools(config)) and not any(candidate.name == 'knowledge.search' for candidate in tools):
        raise RuntimeError('ContextDB MCP 未提供可用的 knowledge.search；知识访问已停止')
    return tools
