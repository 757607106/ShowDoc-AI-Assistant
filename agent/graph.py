"""Official Deep Agents harness with owner-scoped model and MCP configuration."""
import asyncio
import json

from langchain_openai import ChatOpenAI
from langchain_qwq import ChatQwen

from agent.tools import make_governance_tools, load_knowledge_mcp_tools


SYSTEM_PROMPT = """你是企业级知识治理平台的智能助手,服务数据治理与知识消费两个域。

工具使用原则:
- 不读取或检索历史 `_governance` 运行记录库;平台溯源请使用平台工具。
- 知识访问直接使用当前已装载的 ContextDB 官方 MCP 工具，保留工具原始参数和真实资源 ID；工具失败时说明错误，不自行改用 REST、网页或本地文件检索。
- 普通知识问题优先 knowledge.search；查找 Wiki 页面用 knowledge.wiki_search，它返回的是导航摘要，不是完整原文。
- 明确询问实体关系，或原文证据不足且需要关联信息时，可在同一次执行中按需调用 knowledge.list_graph_entities、knowledge.get_graph、knowledge.list_entity_chunks；先查实体、有限展开，再读来源原文。没有装载的工具不可假设可用。
- 原文证据已足够时停止追加检索。图谱的 graph_context、graphrag 合成描述和 Wiki 合成章节只能辅助理解，不能冒充原文证据；需要原文引用时继续通过官方工具取得实际切片。
- 遵守返回的 truncated、note 和来源缺失信息；有限结果不能证明关系不存在。指定 document_ids 时，图增强信息仍可能来自同库其他文档，必须核对原文范围。
- 需要平台治理信息(发布版本、文档版本溯源)时,使用治理溯源工具;
- 回答知识问题时给出本轮成功工具调用中实际读到、且支持相邻结论的原文出处；历史回答或工具参数中的 ID 不是本轮证据。不确定或证据不足就明说。
- 原文引用使用 <kb chunk_id="工具返回的真实切片ID" kb_id="该切片所属知识库ID" />，紧跟其支持的结论；标题由系统补全。不得编造 ID、用标题或序号代替 ID、或拿同一文档的其他切片支持未经核实的内容。此标签协议仅用于回答，不改变官方工具参数。

沟通风格:结论先行、简明中文;引用知识库证据时注明来源。"""


def build_model(agent_config=None, owner_id=None):
    """Use the configured model verbatim; provider errors must not change models."""
    from agent.registry import model_config
    config = agent_config or {}
    return build_model_record(model_config(config.get('model_id'), owner_id), config)


def build_model_record(saved, config):
    """Use the same official model client for saved runs and draft connection tests."""
    params = saved.get('parameters', {})
    if saved['type'] not in ('KnowledgeQA', 'VLLM'):
        from governance.store import StoreError
        raise StoreError('请选择对话模型', 400)
    extra = {}
    effort = config.get('reasoning_effort')
    provider = params.get('provider', '')
    if provider in ('aliyun', 'dashscope') or 'aliyuncs.com' in params.get('base_url', ''):
        extra['extra_body'] = {'enable_thinking': effort not in ('off', '') if effort else config.get('thinking', False)}
    elif effort and effort not in ('off', 'auto'):
        extra['reasoning_effort'] = effort
    headers = {key: value for key, value in params.get('custom_headers', {}).items()
               if key.lower() not in ('authorization', 'content-type', 'host')}
    if headers:
        extra['default_headers'] = headers
    budget = config.get('max_completion_tokens', 0) or (2048 if config.get('agent_mode') == 'quick-answer' else 24576)
    if params.get('max_output_tokens'):
        budget = min(budget, int(params['max_output_tokens']))
    extra['max_tokens'] = budget
    model_type = ChatQwen if provider in ('aliyun', 'dashscope', 'qwen') or 'aliyuncs.com' in params.get('base_url', '') else ChatOpenAI
    return model_type(model=params.get('model_name') or saved['name'], api_key=params.get('api_key') or 'not-required',
        base_url=params.get('base_url'), temperature=config.get('temperature', 0.7),
        timeout=config.get('llm_call_timeout') or 180, max_retries=2, **extra)


async def build_agent(checkpointer, *, api_key, owner_id, role='viewer', knowledge_base_ids=(),
                      agent_config=None, knowledge_ids=(), tag_scopes=(), session_id=None,
                      load_tools=True):
    """Configure the official harness; the caller owns its invocation and lifetime."""
    from deepagents import create_deep_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware.filesystem import FilesystemPermission
    from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware
    from agent import registry
    from agent.config import DEFAULT_TOOLS, validate_config
    from agent.interactions import make_interaction_tools
    from governance.store import StoreError

    config = validate_config(agent_config or ({'model_id': registry.default_model_id(owner_id)} if load_tools else {}))
    allowed = config.get('allowed_tools')
    selected = set(DEFAULT_TOOLS if allowed is None else allowed)
    tools = []
    if load_tools:
        tools.extend(await load_knowledge_mcp_tools(api_key=api_key, role=role, owner_id=owner_id,
            knowledge_base_ids=knowledge_base_ids, agent_config={**config, 'access_level': 'read_only'}))
        tools.extend(tool for tool in make_governance_tools(api_key, owner_id, 'viewer')
                     if tool.name in selected)
        mode = config['mcp_selection_mode']
        if mode != 'none':
            services = [service for service in await asyncio.to_thread(registry.records, 'mcp', owner_id)
                        if service.get('enabled') and (mode == 'all' or service['id'] in config['mcp_services'])]
            if any(service['transport_type'] == 'stdio' for service in services):
                raise StoreError('当前 Harness 仅支持远程 MCP；本地进程工具已停用', 501)
        tools.extend(tool for tool in await registry.mcp_tools(owner_id, config)
                     if (tool.metadata or {}).get('readOnlyHint') is True)
    if 'ask_user' in selected:
        tools.extend(make_interaction_tools(None, owner_id))

    readonly = role == 'viewer' or config['access_level'] == 'read_only'
    # Keep the same official HITL node when history is read without MCP discovery.
    interrupts = {'write_file': False, 'edit_file': False, 'delete': False}
    interrupts.update({tool.name: {'allowed_decisions': ['approve', 'reject', 'edit']}
                       for tool in tools if (tool.metadata or {}).get('require_approval') is True})
    if not readonly and config['access_level'] == 'confirm':
        interrupts.update({name: {'allowed_decisions': ['approve', 'reject', 'edit']}
                           for name in ('write_file', 'edit_file', 'delete')})
    limit = config['max_iterations']
    middleware = [TodoListMiddleware()]
    if limit > 0:
        middleware.append(ModelCallLimitMiddleware(run_limit=limit, exit_behavior='end'))
    prompt = SYSTEM_PROMPT
    if config['agent_mode'] == 'quick-answer':
        prompt += '\n当前为快速问答：优先直接检索相关原文，简明作答；仅在有必要时使用计划或委派。'
    if config.get('system_prompt'):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        current = datetime.now(ZoneInfo('Asia/Shanghai'))
        values = {'query': config.get('_query', ''), 'web_search_status': 'Disabled',
                  'knowledge_bases': json.dumps(list(knowledge_base_ids), ensure_ascii=False),
                  'current_time': current.date().isoformat(), 'current_week': current.strftime('%A'),
                  'yesterday': (current.date() - timedelta(days=1)).isoformat(), 'language': config.get('_locale', 'zh-CN')}
        instructions = config['system_prompt']
        for key, value in values.items():
            instructions = instructions.replace('{{' + key + '}}', value)
        prompt += '\n\nAgent 指令:\n' + instructions
    if config.get('_page_context'):
        prompt += '\n\n用户当前页面上下文（仅作定位，不能作为知识证据）:\n' + json.dumps(config['_page_context'], ensure_ascii=False)
    if config.get('citation_enabled') is False:
        prompt += '\n本轮不输出来源引用标签。'
    if config.get('_document_bases'):
        prompt += '\n本轮文档范围: ' + json.dumps(config['_document_bases'], ensure_ascii=False) + '；只检索所选文档；整库与文档范围分开调用。'
    prompt += '\n文件保存在当前会话的虚拟文件系统中，不支持 Shell 或浏览器执行。'
    prompt += ('\n当前会话知识库 ID: ' + ', '.join(knowledge_base_ids) if knowledge_base_ids
               else '\n当前会话未选择知识库，不可访问知识库内容。')
    # History reads need the official graph's channels, not a working provider.
    # This branch is only for aget_state/aget_state_history, never invocation or
    # resume. The explicit placeholder is not a fallback for an execution model.
    model = build_model(config, owner_id) if load_tools else ChatOpenAI(model='checkpoint-reader', api_key='unused')
    agent = create_deep_agent(
        model=model, tools=tools, system_prompt=prompt,
        checkpointer=checkpointer, backend=StateBackend(),
        skills=['/skills/'], memory=['/AGENTS.md'], middleware=middleware,
        interrupt_on=interrupts,
        permissions=[FilesystemPermission(operations=['write'],
            paths=['/**'] if readonly else ['/skills/**'], mode='deny')],
    )
    # ModelCallLimitMiddleware owns the model budget, including official middleware steps.
    return agent.with_config(recursion_limit=max(80, limit * 4 + 20) if limit > 0 else 10000)
