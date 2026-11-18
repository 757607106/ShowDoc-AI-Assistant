"""Official Deep Agents harness with owner-scoped model and MCP configuration."""
import asyncio
import copy
import json

from langchain_openai import ChatOpenAI

from agent.models import build_model_record
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

SKILL_EXECUTION_PATHS = """技能路径说明：文件工具中的 /state/skills/<技能名>/<相对路径> 与
/state/subagent-skills/<子代理名>/<技能名>/<相对路径> 是虚拟指令/资料来源。
具备 execute 时，所选技能的会话执行副本位于 /workspace/skills/<技能名>/<相对路径>；
Shell 只能使用这个真实路径，不能把 /state/ 或 /memories/ 当作命令行目录。
技能依赖由部署镜像提供；执行副本不回写技能目录。"""


def build_model(agent_config=None, owner_id=None):
    """Use the configured model verbatim; provider errors must not change models."""
    from agent.registry import model_config
    config = agent_config or {}
    return build_model_record(model_config(config.get('model_id'), owner_id), config)


async def build_agent(checkpointer, *, api_key, owner_id, role='viewer', knowledge_base_ids=(),
                      agent_config=None, knowledge_ids=(), tag_scopes=(), session_id=None,
                      load_tools=True, store=None, agent_id=None, backend=None,
                      delegated_subagent=None, additional_middleware=()):
    """Configure the official harness; the caller owns its invocation and lifetime."""
    from deepagents import create_deep_agent
    from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
    from deepagents.middleware.filesystem import FilesystemPermission
    from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware
    from agent import registry
    from agent.config import DEFAULT_TOOLS, validate_config
    from agent.interactions import make_interaction_tools
    from governance.store import StoreError

    config = validate_config(agent_config or ({'model_id': registry.default_model_id(owner_id)} if load_tools else {}),
                             check_runtime=load_tools and delegated_subagent is None)
    allowed = config.get('allowed_tools')
    selected = set(DEFAULT_TOOLS if allowed is None else allowed)
    tools = []
    if load_tools:
        tools.extend(await load_knowledge_mcp_tools(api_key=api_key, role=role, owner_id=owner_id,
            knowledge_base_ids=knowledge_base_ids, agent_config={**config, 'access_level': 'read_only'}))
        tools.extend(tool for tool in make_governance_tools(api_key, owner_id, 'viewer')
                     if tool.name in selected)
        tools.extend(tool for tool in await registry.mcp_tools(owner_id, config)
                     if (tool.metadata or {}).get('readOnlyHint') is True)
    if 'ask_user' in selected:
        tools.extend(make_interaction_tools(None, owner_id))

    if role == 'viewer':
        config = {**config, 'access_level': 'read_only'}
    readonly = config['access_level'] == 'read_only'
    if readonly and backend is not None:
        raise StoreError('只读 Agent 不允许启用命令执行后端', 403)
    routes = {'/state/': StateBackend()} if backend is not None else {}
    skills = ['/state/skills/'] if backend is not None else ['/skills/']
    memory = ['/state/AGENTS.md'] if backend is not None else ['/AGENTS.md']
    skill_paths = ['/state/skills/**'] if backend is not None else ['/skills/**']
    if store is not None and load_tools and config['memory_enabled']:
        from agent.memory_files import namespace, policy
        memory_policy = await asyncio.to_thread(policy, owner_id)
        if memory_policy['effective']:
            memory_namespace = namespace(owner_id, agent_id)
            memory_prefix = f'/memories/{agent_id}/'
            routes[memory_prefix] = StoreBackend(namespace=lambda _runtime: memory_namespace, store=store)
            memory.append(memory_prefix + 'AGENTS.md')
    runtime_backend = backend if backend is not None else StateBackend()
    if routes:
        runtime_backend = CompositeBackend(default=runtime_backend, routes=routes)
    permissions = [FilesystemPermission(operations=['write'],
        paths=['/**'] if readonly else [*skill_paths, ('/state/' if backend is not None else '/') + 'subagent-skills/**'], mode='deny')]
    permissions.extend(FilesystemPermission(**rule) for rule in config['permissions'])
    _validate_backend_permissions(runtime_backend, permissions)
    interrupts = _interrupt_policy(tools, config['access_level'], backend is not None, config['interrupt_on'])
    limit = config['max_iterations']
    middleware = [TodoListMiddleware(), *additional_middleware]
    if backend is not None:
        middleware.append(_execution_skills(runtime_backend, skills))
        from agent.sandbox import ManagedOpenSandboxBackend, SandboxArtifacts
        if isinstance(backend, ManagedOpenSandboxBackend):
            middleware.append(SandboxArtifacts(backend))
    if limit > 0:
        middleware.append(ModelCallLimitMiddleware(run_limit=limit, exit_behavior='end'))
    prompt = _system_prompt(config, knowledge_base_ids, backend is not None)
    # History reads need the official graph's channels, not a working provider.
    # This branch is only for aget_state/aget_state_history, never invocation or
    # resume. The explicit placeholder is not a fallback for an execution model.
    model = build_model(config, owner_id) if load_tools else ChatOpenAI(model='checkpoint-reader', api_key='unused')
    local_children = [child for child in config['subagents'] if
        child['name'] == delegated_subagent or delegated_subagent is None and child.get('execution_mode', 'sync') == 'sync']
    subagents = _subagents({**config, 'subagents': local_children}, tools, model, runtime_backend,
                          backend is not None, owner_id, knowledge_base_ids, load_tools, permissions, interrupts,
                          additional_middleware=additional_middleware if delegated_subagent else ())
    if delegated_subagent is not None:
        if len(subagents) != 1:
            raise StoreError('异步子代理配置已失效', 409)
        spec = subagents[0]
        if 'runnable' in spec:
            agent = spec['runnable']
        else:
            child_middleware = [item for item in middleware if type(item).__name__ != 'SkillsMiddleware']
            child_middleware.extend(spec.get('middleware', []))
            agent = create_deep_agent(**{key: value for key, value in spec.items() if key not in ('description', 'middleware')},
                backend=runtime_backend, checkpointer=checkpointer, store=store, middleware=child_middleware)
        return agent.with_config(recursion_limit=max(80, limit * 4 + 20) if limit > 0 else 10000)
    from agent.async_runtime import specification
    from agent.async_work import NativeAsyncTasks
    middleware.append(NativeAsyncTasks(owner_id, session_id))
    subagents.extend(specification(child, owner_id=owner_id, session_id=session_id, agent_id=agent_id,
        config=config, knowledge_base_ids=knowledge_base_ids, knowledge_ids=knowledge_ids, tag_scopes=tag_scopes,
        persist=load_tools) for child in config['subagents'] if child.get('execution_mode') == 'async')
    agent = create_deep_agent(
        model=model, tools=tools, system_prompt=prompt,
        checkpointer=checkpointer, backend=runtime_backend, store=store,
        skills=skills, memory=memory, middleware=middleware,
        interrupt_on=interrupts, permissions=permissions,
        subagents=subagents, response_format=config['response_format'], name=agent_id,
    )
    # Main-graph steps are limited; delegation, summarization and retries can make extra provider calls.
    return agent.with_config(recursion_limit=max(80, limit * 4 + 20) if limit > 0 else 10000)


def _system_prompt(config, knowledge_base_ids, has_shell):
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
    if not has_shell:
        prompt += '\n文件保存在当前会话的虚拟文件系统中，不支持 Shell 或浏览器执行。'
    else:
        prompt += '\n命令在当前会话的独立沙箱中执行；/state/ 与 /memories/ 是文件工具提供的虚拟目录，不能当作 Shell 的真实目录。'
        prompt += '\n需交付给用户下载的文件请保存到 /workspace/；本轮生成或修改的文件会自动归档，单次工具产物总量限 25 MiB。临时依赖、缓存不要放在此交付目录中。'
    prompt += ('\n当前会话知识库 ID: ' + ', '.join(knowledge_base_ids) if knowledge_base_ids
               else '\n当前会话未选择知识库，不可访问知识库内容。')
    return prompt


def _execution_skills(backend, sources):
    from deepagents.middleware.skills import SKILLS_SYSTEM_PROMPT, SkillsMiddleware
    return SkillsMiddleware(backend=backend, sources=sources,
                            system_prompt=SKILLS_SYSTEM_PROMPT + '\n\n' + SKILL_EXECUTION_PATHS)


def _validate_backend_permissions(backend, permissions):
    from deepagents.backends import CompositeBackend
    from deepagents.middleware.filesystem import supports_execution
    if supports_execution(backend):
        prefixes = list(backend.routes) if isinstance(backend, CompositeBackend) else []
        if any(not any(path.startswith(prefix) for prefix in prefixes)
               for rule in permissions for path in rule.paths):
            from governance.store import StoreError
            raise StoreError('执行后端的文件规则仅支持虚拟挂载路径；真实目录权限须由沙箱策略限制', 501)


def _interrupt_policy(tools, access, has_shell, requested, inherited=None):
    result = copy.deepcopy(inherited or {})
    for name, setting in requested.items():
        previous = result.get(name)
        if previous and setting is False:
            continue
        if previous and isinstance(previous, dict):
            if setting is True:
                continue
            if isinstance(setting, dict):
                setting = {**previous, **setting, 'allowed_decisions': [choice for choice in setting['allowed_decisions']
                    if choice in previous['allowed_decisions']]}
                if not setting['allowed_decisions']:
                    from governance.store import StoreError
                    raise StoreError('子代理不能扩大或清空父级审批决定范围', 400)
        result[name] = copy.deepcopy(setting)
    forced = {tool.name for tool in tools if (tool.metadata or {}).get('require_approval') is True}
    if access == 'confirm':
        forced.update(('write_file', 'edit_file', 'delete'))
        if has_shell:
            forced.add('execute')
    for name in forced:
        if not result.get(name):
            result[name] = {'allowed_decisions': ['approve', 'reject', 'edit']}
    if access == 'read_only':
        result.update({name: False for name in ('write_file', 'edit_file', 'delete', 'execute')})
    return result


def _subagents(config, tools, model, backend, has_shell, owner_id, knowledge_base_ids,
               load_tools, parent_permissions, parent_interrupts, *, additional_middleware=()):
    from deepagents import create_deep_agent
    from deepagents.backends import CompositeBackend, StateBackend
    from deepagents.middleware._fs_interrupt import _build_interrupt_on_from_permissions
    from deepagents.middleware.filesystem import FilesystemPermission
    from agent.config import TOOL_ALIASES, allowed_knowledge_tools
    from governance.store import StoreError
    levels = ('read_only', 'confirm', 'auto_write')
    parent_access = config['access_level']
    authorized = allowed_knowledge_tools(config) | {tool.name for tool in tools}
    prefix = '/state/' if has_shell else '/'
    result = []
    for child in config['subagents']:
        names = child.get('allowed_tools')
        if names is None:
            child_tools = list(tools)
        else:
            selected = set().union(*(TOOL_ALIASES.get(name, {name}) for name in names)) if names else set()
            if not selected <= authorized:
                raise StoreError('子代理工具超出父 Agent 已授权范围', 403)
            child_tools = [tool for tool in tools if tool.name in selected]
        child_access = levels[min(levels.index(parent_access), levels.index(child.get('access_level', parent_access)))]
        permissions = [FilesystemPermission(**rule) for rule in child.get('permissions', [])]
        if child_access == 'read_only':
            permissions.append(FilesystemPermission(operations=['write'], paths=['/**'], mode='deny'))
        sources = [prefix + 'skills/']
        selected_skills = child.get('selected_skills')
        if selected_skills is not None:
            if config['skills_selection_mode'] == 'none' and selected_skills or (config['skills_selection_mode'] == 'selected'
                    and not set(selected_skills) <= set(config['selected_skills'])):
                raise StoreError('子代理技能超出父 Agent 已授权范围', 403)
            sources = [prefix + 'subagent-skills/' + child['name'] + '/'] if selected_skills else []
            paths = [prefix + 'skills/**', *[prefix + 'subagent-skills/' + other['name'] + '/**'
                for other in config['subagents'] if other['name'] != child['name'] or not selected_skills]]
            permissions.append(FilesystemPermission(operations=['read'], paths=paths, mode='deny'))
        permissions.extend(parent_permissions)
        # Use the pinned SDK's path predicates, including child deny rules. A
        # child override cannot turn off its parent's generated approval gate.
        inherited_interrupts = _build_interrupt_on_from_permissions(permissions, backend)
        inherited_interrupts.update(parent_interrupts)
        child_config = {**config, 'system_prompt': child.get('system_prompt', config.get('system_prompt', ''))}
        selected_model = model
        if load_tools and child.get('model_id') and child['model_id'] != config['model_id']:
            child_config.update(model_id=child['model_id'], thinking=False, reasoning_effort='')
            selected_model = build_model(child_config, owner_id)
        spec = {'name': child['name'], 'description': child['description'], 'model': selected_model,
            'system_prompt': _system_prompt(child_config, knowledge_base_ids, has_shell and child_access != 'read_only'),
            'tools': child_tools, 'skills': sources, 'permissions': permissions,
            'interrupt_on': _interrupt_policy(child_tools, child_access, has_shell, child.get('interrupt_on', {}), inherited_interrupts),
            'response_format': child['response_format']}
        if child_access == 'read_only' and has_shell:
            # A non-executing CompositeBackend keeps file access without granting the parent's shell.
            readonly_backend = CompositeBackend(default=StateBackend(), routes={'/': backend})
            runnable = create_deep_agent(selected_model, tools=child_tools, system_prompt=spec['system_prompt'],
                backend=readonly_backend, skills=sources, permissions=permissions,
                interrupt_on=spec['interrupt_on'], response_format=spec['response_format'], name=child['name'],
                middleware=list(additional_middleware))
            spec = {'name': child['name'], 'description': child['description'], 'runnable': runnable}
        elif has_shell and sources:
            _validate_backend_permissions(backend, permissions)
            spec['middleware'] = [_execution_skills(backend, sources)]
        else:
            _validate_backend_permissions(backend, permissions)
        result.append(spec)
    return result
