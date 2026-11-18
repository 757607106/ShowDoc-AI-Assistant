"""Agent configurations and request scope, independent of the chat transport."""
import copy
import json
import re
import uuid

from jsonschema import validators
from jsonschema.exceptions import SchemaError

from agent import registry
from governance.store import StoreError

DEFAULT_TOOLS = ['search_knowledge', 'read_document', 'list_documents', 'query_knowledge_graph', 'ask_user']
INTERNAL_ASSISTANT_ID = 'builtin-weknora-assistant'
TOOL_ALIASES = {
    'search_knowledge': {'knowledge.search'}, 'read_document': {'knowledge.get_document'},
    'list_documents': {'knowledge.list_documents'}, 'query_knowledge_graph': {
        'knowledge.list_graph_entities', 'knowledge.get_graph', 'knowledge.list_entity_chunks'},
    'wiki_search': {'knowledge.wiki_search'}, 'wiki_read_page': {'knowledge.get_wiki_page'},
}
DEFAULT_CONFIG = {'agent_mode': 'smart-reasoning', 'agent_type': 'rag-qa', 'model_id': 'agent-main',
    'system_prompt': '', 'temperature': 0.7, 'max_completion_tokens': 0, 'max_iterations': 50,
    'llm_call_timeout': 120, 'thinking': False, 'citation_enabled': True,
    'allowed_tools': None, 'kb_selection_mode': 'all', 'knowledge_bases': [],
    'retrieve_kb_only_when_mentioned': False, 'mcp_selection_mode': 'none', 'mcp_services': [],
    'skills_selection_mode': 'none', 'selected_skills': [], 'web_search_enabled': False,
    'multi_turn_enabled': True, 'history_turns': 5, 'memory_enabled': True, 'retain_retrieval_history': True, 'access_level': 'confirm',
    'image_upload_enabled': False, 'file_upload_enabled': True, 'sandbox_config_id': 'state-backend',
    'subagents': [], 'response_format': None, 'permissions': [], 'interrupt_on': {}}
BUILTINS = {
    'builtin-quick-answer': {'name': '快速问答', 'description': '根据知识库原文直接回答',
                            'config': {'agent_mode': 'quick-answer', 'max_iterations': 8, 'temperature': 0.3}},
    'builtin-smart-reasoning': {'name': '智能推理', 'description': '按需检索、分析和调用工具', 'config': {}},
}
UNSUPPORTED_QUICK_FIELDS = (
    'enable_query_expansion', 'enable_rewrite', 'embedding_top_k', 'keyword_threshold',
    'vector_threshold', 'rerank_top_k', 'rerank_threshold', 'rerank_model_id',
    'context_template', 'context_template_id', 'fallback_prompt', 'fallback_response',
    'intent_prompts', 'fallback_strategy',
)


def validate_response_format(schema):
    if schema is None:
        return None
    if not isinstance(schema, dict):
        raise StoreError('response_format 必须为 JSON Schema 对象或 null', 400)
    try:
        if len(json.dumps(schema, ensure_ascii=False, allow_nan=False).encode()) > 64_000:
            raise StoreError('response_format 不能超过 64000 字节', 400)
        def walk(value, depth=0):
            if depth > 30:
                raise StoreError('response_format 嵌套不能超过 30 层', 400)
            if isinstance(value, dict):
                if '$id' in value and (not isinstance(value['$id'], str) or not value['$id'].startswith('#')):
                    raise StoreError('response_format 不能改变外部资源解析范围', 400)
                for keyword in ('$ref', '$dynamicRef', '$recursiveRef'):
                    reference = value.get(keyword)
                    if reference is None:
                        continue
                    if not isinstance(reference, str) or not reference.startswith('#'):
                        raise StoreError('response_format 只允许本地 $ref，不能读取外部资源', 400)
                    target = schema
                    if reference != '#':
                        if not reference.startswith('#/'):
                            raise StoreError('response_format $ref 必须使用本地 JSON Pointer', 400)
                        for part in reference[2:].split('/'):
                            key = part.replace('~1', '/').replace('~0', '~')
                            if isinstance(target, list) and not key.isdigit():
                                raise StoreError('response_format 本地数组引用无效', 400)
                            target = target[int(key)] if isinstance(target, list) else target[key]
                for item in value.values():
                    walk(item, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    walk(item, depth + 1)
        walk(schema)
        validator = validators.validator_for(schema, default=None) if '$schema' in schema else validators.validator_for(schema)
        if validator is None:
            raise StoreError('response_format 使用了不支持的 JSON Schema 版本', 400)
        validator.check_schema(schema)
    except (SchemaError, KeyError, IndexError, ValueError, TypeError, RecursionError) as exc:
        raise StoreError('response_format 必须为有效且可解析的 JSON Schema', 400) from exc
    return copy.deepcopy(schema)


def _native_policies(value, *, child=False):
    rules = value.get('permissions', [])
    if not isinstance(rules, list) or len(rules) > 100:
        raise StoreError('permissions 必须为最多 100 项的文件规则列表', 400)
    for rule in rules:
        if (not isinstance(rule, dict) or set(rule) - {'operations', 'paths', 'mode'}
                or rule.get('mode', 'allow') not in (('deny',) if child else ('allow', 'deny', 'interrupt'))
                or not isinstance(rule.get('operations'), list) or not rule['operations']
                or any(operation not in ('read', 'write') for operation in rule['operations'])
                or not isinstance(rule.get('paths'), list) or not rule['paths'] or len(rule['paths']) > 100
                or any(not isinstance(path, str) or not path.startswith('/') or len(path) > 1000
                       or '\\' in path or '\x00' in path or '..' in path.split('/') for path in rule['paths'])):
            raise StoreError('文件权限规则无效；子代理只允许附加 deny 规则', 400)
    interrupts = value.get('interrupt_on', {})
    if not isinstance(interrupts, dict) or len(interrupts) > 200:
        raise StoreError('interrupt_on 必须为工具审批配置对象', 400)
    for name, setting in interrupts.items():
        if not isinstance(name, str) or not name or len(name) > 300:
            raise StoreError('审批工具名无效', 400)
        if isinstance(setting, bool):
            continue
        if (not isinstance(setting, dict) or set(setting) - {'allowed_decisions', 'description'}
                or not isinstance(setting.get('allowed_decisions'), list) or not setting['allowed_decisions']
                or any(choice not in ('approve', 'edit', 'reject', 'respond') for choice in setting['allowed_decisions'])
                or 'description' in setting and (not isinstance(setting['description'], str) or len(setting['description']) > 8000)):
            raise StoreError('工具审批配置无效；条件回调只能由服务端注册', 400)


def _native_config(value):
    for name in ('middleware', 'state_schema', 'context_schema', 'cache', 'debug', 'name', 'native_extension', 'runnable', 'graph_id'):
        if name in value:
            raise StoreError(f'{name} 只能由可信服务端配置', 400)
    value['response_format'] = validate_response_format(value.get('response_format'))
    _native_policies(value)
    children = value.get('subagents')
    if not isinstance(children, list) or len(children) > 20:
        raise StoreError('subagents 必须为最多 20 项的专业子代理列表', 400)
    names = set()
    for child in children:
        if (not isinstance(child, dict) or set(child) - {'name', 'description', 'model_id', 'system_prompt',
                'allowed_tools', 'selected_skills', 'access_level', 'response_format', 'permissions', 'interrupt_on',
                'execution_mode', 'update_strategy', 'mode'}):
            raise StoreError('子代理只能声明模型、指令、工具、技能、权限、审批、输出格式和运行方式', 400)
        execution_mode = child.get('execution_mode', 'sync')
        if execution_mode not in ('sync', 'async'):
            raise StoreError('子代理 execution_mode 必须为 sync 或 async', 400)
        for key, choices in (('update_strategy', ('interrupt', 'enqueue')), ('mode', ('isolated', 'fork'))):
            if key in child and (execution_mode != 'async' or child[key] not in choices):
                raise StoreError(f'子代理 {key} 仅适用于异步运行，可选值为 {"、".join(choices)}', 400)
        name = child.get('name')
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name)
                or name == 'general-purpose' or name in names):
            raise StoreError('子代理名称须为唯一的 1 至 64 位字母数字、横线或下划线，不能使用 general-purpose', 400)
        names.add(name)
        if not isinstance(child.get('description'), str) or not child['description'].strip() or len(child['description']) > 8000:
            raise StoreError('请提供不超过 8000 字符的子代理描述', 400)
        for key in ('model_id', 'system_prompt'):
            if key in child and (not isinstance(child[key], str) or len(child[key]) > (300 if key == 'model_id' else 100_000)):
                raise StoreError(f'子代理 {key} 无效', 400)
        if child.get('access_level', 'confirm') not in ('read_only', 'confirm', 'auto_write'):
            raise StoreError('子代理 access_level 无效', 400)
        for key in ('allowed_tools', 'selected_skills'):
            selected = child.get(key)
            if selected is not None and (not isinstance(selected, list) or len(selected) > 200
                    or any(not isinstance(item, str) or not item or len(item) > 300 for item in selected)):
                raise StoreError(f'子代理 {key} 必须为字符串列表或 null', 400)
        child['response_format'] = validate_response_format(child.get('response_format'))
        _native_policies(child, child=True)


def validate_config(config, *, check_runtime=True):
    if not isinstance(config, dict):
        raise StoreError('Agent config 必须为对象', 400)
    value = {**copy.deepcopy(DEFAULT_CONFIG), **copy.deepcopy(config)}
    value['retrieval_provider'] = 'contextdb'
    if value['agent_mode'] == 'quick-answer' and 'history_turns' not in config:
        value['history_turns'] = 0
    value['sandbox_config_id'] = value.get('sandbox_config_id') or 'state-backend'
    if not isinstance(value['sandbox_config_id'], str):
        raise StoreError('sandbox_config_id 必须为字符串', 400)
    for key in ('kb_selection_mode', 'mcp_selection_mode', 'skills_selection_mode'):
        if value[key] not in ('all', 'selected', 'none'):
            raise StoreError(f'{key} 必须为 all、selected 或 none', 400)
    if value['agent_mode'] not in ('quick-answer', 'smart-reasoning'):
        raise StoreError('agent_mode 无效', 400)
    if value['access_level'] not in ('read_only', 'confirm', 'auto_write'):
        raise StoreError('access_level 无效', 400)
    for key in ('knowledge_bases', 'mcp_services', 'selected_skills', 'allowed_tools'):
        if key == 'allowed_tools' and value[key] is None:
            continue
        if not isinstance(value[key], list) or len(value[key]) > 200 or any(not isinstance(x, str) or not x or len(x) > 300 for x in value[key]):
            raise StoreError(f'{key} 必须为有效字符串列表', 400)
        value[key] = list(dict.fromkeys(value[key]))
    for key in ('retrieve_kb_only_when_mentioned', 'thinking', 'citation_enabled', 'multi_turn_enabled', 'web_search_enabled', 'memory_enabled', 'retain_retrieval_history'):
        if not isinstance(value[key], bool):
            raise StoreError(f'{key} 必须为布尔值', 400)
    # WeKnora's smart-mode form hides this switch; its backend always enables history.
    if value['agent_mode'] == 'smart-reasoning':
        value['multi_turn_enabled'] = True
    for key in ('max_iterations', 'max_completion_tokens', 'llm_call_timeout', 'history_turns'):
        if isinstance(value[key], bool) or not isinstance(value[key], int) or value[key] < (-1 if key == 'max_iterations' else 0) or (key == 'max_iterations' and value[key] == 0):
            raise StoreError(f'{key} 必须为有效整数', 400)
    if not isinstance(value['temperature'], (int, float)) or isinstance(value['temperature'], bool) or not 0 <= value['temperature'] <= 2:
        raise StoreError('temperature 必须在0到2之间', 400)
    for key in ('system_prompt', 'system_prompt_id', 'model_id', 'context_template', 'reasoning_effort'):
        if key in value and not isinstance(value[key], str):
            raise StoreError(f'{key} 必须为字符串', 400)
    if value.get('reasoning_effort', '') not in ('', 'off', 'auto', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'):
        raise StoreError('reasoning_effort 无效', 400)
    _native_config(value)
    if check_runtime:
        issues = runtime_config_issues(value)
        if issues:
            raise StoreError(issues[0]['message'], issues[0].get('status', 501))
    return value


def runtime_config_issues(value):
    """Describe unsupported values without changing stored configurations."""
    issues = []
    async_children = [index for index, child in enumerate(value.get('subagents', []))
                      if child.get('execution_mode', 'sync') == 'async']
    if async_children:
        from agent.async_runtime import enabled
        if not enabled():
            issues.extend({'field': f'subagents[{index}].execution_mode', 'message':
                '异步子代理服务尚未连接，请先部署 Agent Protocol 服务或改为同步运行'} for index in async_children)
    if not value['retain_retrieval_history']:
        issues.append({'field': 'retain_retrieval_history', 'message':
            '当前 Harness 使用原生 checkpoint 保留工具历史；尚未接入跨轮清理，请开启 retain_retrieval_history'})
    if value['sandbox_config_id'] not in ('state-backend', 'opensandbox-local'):
        issues.append({'field': 'sandbox_config_id', 'message': '当前 Harness 仅支持 state-backend 或 opensandbox-local'})
    children = [(f'subagents[{index}].', child) for index, child in enumerate(value['subagents'])]
    if value['sandbox_config_id'] == 'opensandbox-local' and value['access_level'] != 'read_only':
        for prefix, agent in [('', value), *children]:
            if agent.get('access_level') != 'read_only' and any(
                    not path.startswith(('/state/', '/memories/'))
                    for rule in agent.get('permissions', []) for path in rule['paths']):
                field = prefix + 'permissions'
                issues.append({'field': field, 'status': 400,
                    'message': f'{field}：OpenSandbox 文件权限规则仅适用于虚拟挂载路径'})
    for prefix, child in children:
        selected = child.get('selected_skills')
        mode = value['skills_selection_mode']
        if selected and (mode == 'none' or mode == 'selected' and not set(selected) <= set(value['selected_skills'])):
            field = prefix + 'selected_skills'
            issues.append({'field': field, 'status': 400, 'message': f'{field}：子代理技能超出父 Agent 已授权范围'})
    for key in ('web_search_enabled', 'reflection_enabled'):
        if value.get(key) is True:
            issues.append({'field': key, 'message': f'{key} 尚未接入当前官方 Harness'})
    # WeKnora only reads these local RAG pipeline options in quick-answer mode.
    if value['agent_mode'] == 'quick-answer':
        for key, unsupported in (('multi_turn_enabled', not value['multi_turn_enabled']), ('history_turns', value['history_turns'] > 0)):
            if unsupported:
                issues.append({'field': key, 'message':
                    '当前 Harness 使用原生 checkpoint 管理历史；尚未接入单轮隔离或 history_turns 窗口'})
        for key in ('enable_query_expansion', 'enable_rewrite'):
            if value.get(key) is True:
                issues.append({'field': key, 'message': f'{key} 的本地算法未启用；检索处理由 ContextDB 管理'})
        for key in ('embedding_top_k', 'keyword_threshold', 'vector_threshold', 'rerank_top_k', 'rerank_threshold', 'rerank_model_id'):
            if value.get(key) not in (None, ''):
                issues.append({'field': key, 'message': f'{key} 请在 ContextDB 中配置，当前平台不能覆盖其检索管线'})
        for key in ('context_template', 'context_template_id', 'fallback_prompt', 'fallback_response', 'intent_prompts'):
            if value.get(key):
                issues.append({'field': key, 'message': f'{key} 尚未接入当前官方 Harness'})
        if value.get('fallback_strategy') not in (None, '', 'model'):
            issues.append({'field': 'fallback_strategy', 'message': '固定 fallback_strategy 尚未接入当前官方 Harness'})
    return issues


def runtime_defaults():
    values = {}
    for details in BUILTINS.values():
        config = validate_config(details['config'])
        config.pop('model_id')
        values[config['agent_mode']] = config
    return values


def _resolve_system_prompt(config, owner_id):
    if config['system_prompt'] or not config.get('system_prompt_id'):
        return config['system_prompt']
    try:
        templates = registry.record('settings', 'prompt-templates', owner_id).get('value', {})
    except StoreError as exc:
        if exc.status == 404:
            raise StoreError('系统提示词模板不存在或无权访问', 404) from exc
        raise
    category = 'agent_system_prompt' if config['agent_mode'] == 'smart-reasoning' else 'system_prompt'
    if not isinstance(templates, dict) or not isinstance(templates.get(category, []), list):
        raise StoreError('系统提示词模板配置无效', 400)
    candidates = templates.get(category, [])
    if any(not isinstance(item, dict) for item in candidates):
        raise StoreError('系统提示词模板配置无效', 400)
    matches = [item for item in candidates if item.get('id') == config['system_prompt_id']]
    if not matches:
        raise StoreError('系统提示词模板不存在或无权访问', 404)
    if len(matches) > 1:
        raise StoreError('系统提示词模板 ID 重复，请修正模板配置', 400)
    content = matches[0].get('content')
    if not isinstance(content, str):
        raise StoreError('系统提示词模板正文必须为字符串', 400)
    return content


def list_agents(owner_id):
    saved = registry.records('agent', owner_id)
    overrides = {item['id']: item for item in saved}
    values = [overrides.get(agent_id) or {'id': agent_id, 'is_builtin': True, 'tenant_id': 1,
        'name': details['name'], 'description': details['description'],
        'config': validate_config({**details['config'], 'model_id': registry.default_model_id(owner_id)})} for agent_id, details in BUILTINS.items()] + [
            item for item in saved if item['id'] not in BUILTINS]
    for value in values:
        value['config'] = {**value['config'], 'retrieval_provider': 'contextdb'}
    return values


def load_agent(agent_id=None, owner_id=None):
    agent_id = agent_id or 'builtin-smart-reasoning'
    if agent_id == INTERNAL_ASSISTANT_ID:
        return {'id': agent_id, 'is_builtin': True, 'tenant_id': 1, 'name': 'WeKnora 助手',
            'description': '当前页面的知识检索与会话助手',
            'config': validate_config({'agent_type': 'custom', 'temperature': 0.3,
                'model_id': registry.default_model_id(owner_id),
                'allowed_tools': [*DEFAULT_TOOLS, 'wiki_search']})}
    if agent_id == 'platform-agent':
        agent_id = 'builtin-smart-reasoning'
    for item in list_agents(owner_id):
        if item['id'] == agent_id:
            result = copy.deepcopy(item)
            result['config'] = validate_config(result['config'], check_runtime=False)
            return result
    raise StoreError('Agent 不存在或无权使用', 404)


def save_agent(body, owner_id, agent_id=None):
    if agent_id == INTERNAL_ASSISTANT_ID:
        raise StoreError('页面内置助手由服务器管理，不能覆盖其配置', 403)
    value = load_agent(agent_id, owner_id) if agent_id else {'id': str(uuid.uuid4()), 'is_builtin': False, 'tenant_id': 1, 'created_by': owner_id}
    for key in ('name', 'description', 'avatar'):
        if key in body:
            if not isinstance(body[key], str) or len(body[key]) > (200 if key == 'name' else 10000):
                raise StoreError(f'{key} 无效', 400)
            value[key] = body[key]
    if not value.get('name', '').strip():
        raise StoreError('请提供 Agent 名称', 400)
    submitted = body.get('config', value.get('config', {}))
    if not agent_id and isinstance(submitted, dict) and 'model_id' not in submitted:
        submitted = {**submitted, 'model_id': registry.default_model_id(owner_id)}
    value['config'] = validate_config(submitted)
    _resolve_system_prompt(value['config'], owner_id)
    return registry.save_record('agent', value, owner_id)


def copy_agent(agent_id, owner_id):
    value = load_agent(agent_id, owner_id)
    value['config'] = validate_config(value['config'])
    _resolve_system_prompt(value['config'], owner_id)
    for field in ('created_at', 'updated_at'):
        value.pop(field, None)
    value.update(id=str(uuid.uuid4()), is_builtin=False, created_by=owner_id, name=value['name'] + ' (副本)')
    return registry.save_record('agent', value, owner_id)


def delete_agent(agent_id, owner_id):
    if load_agent(agent_id, owner_id)['is_builtin']:
        raise StoreError('内置 Agent 不能删除', 400)
    registry.delete_record('agent', agent_id, owner_id)


def _ids(body, key):
    value = body.get(key)
    value = [] if value is None else value
    if not isinstance(value, list) or len(value) > 100 or any(not isinstance(item, str) or not item or len(item) > 300 for item in value):
        raise StoreError(f'{key} 必须为有效 ID 列表', 400)
    return list(dict.fromkeys(value))


def resolve_request(body, *, client, owner_id, role='viewer', session=None, has_image_attachments=False):
    if body.get('agent_source_tenant_id') not in (None, 0, '', 1, '1'):
        raise StoreError('当前平台不支持跨空间 Agent', 403)
    session_config = (session or {}).get('agent_config') or {}
    agent = load_agent(body.get('agent_id') or (session or {}).get('agent_id') or session_config.get('agent_id'), owner_id)
    config = copy.deepcopy(agent['config'])
    for key in ('summary_model_id', 'reasoning_effort'):
        if body.get(key):
            config['model_id' if key == 'summary_model_id' else key] = body[key]
    registry.model_config(config['model_id'], owner_id)
    config = validate_config(config)
    config['system_prompt'] = _resolve_system_prompt(config, owner_id)
    access = body.get('assistant_access', config['access_level'])
    levels = ['read_only', 'confirm', 'auto_write']
    if access not in levels:
        raise StoreError('assistant_access 无效', 400)
    config['access_level'] = levels[min(levels.index(access), levels.index(config['access_level']))]
    if role == 'viewer':
        config['access_level'] = 'read_only'
    kb_ids, document_ids = _ids(body, 'knowledge_base_ids'), _ids(body, 'knowledge_ids')
    mentions = body.get('mentioned_items') or []
    if not isinstance(mentions, list) or any(not isinstance(item, dict) for item in mentions):
        raise StoreError('mentioned_items 无效', 400)
    tags = []
    for item in mentions:
        if item.get('type') == 'kb' and item.get('id'):
            kb_ids.append(item['id'])
        elif item.get('type') == 'file' and item.get('id'):
            document_ids.append(item['id'])
        elif item.get('type') == 'tag':
            if not item.get('kb_id') or not item.get('id'):
                raise StoreError('标签需要所属知识库', 400)
            tags.append({'knowledge_base_id': item['kb_id'], 'tag_id': item['id']})
    if tags or body.get('tag_ids'):
        raise StoreError('ContextDB 尚未提供与当前标签 ID 对应的官方筛选契约，请选择文档或知识库', 501)
    explicit = bool(kb_ids or document_ids)
    whole_kb_ids = list(dict.fromkeys(kb_ids))
    requested_knowledge_base_ids = list(whole_kb_ids)
    origin_document, origin_base = None, None
    if not explicit:
        if config['retrieve_kb_only_when_mentioned']:
            origin = body.get('question_origin') or {}
            if not isinstance(origin, dict):
                raise StoreError('question_origin 无效', 400)
            anchor = origin.get('knowledge_base_id')
            permitted = config['kb_selection_mode'] == 'all' or (
                config['kb_selection_mode'] == 'selected' and anchor in config['knowledge_bases'])
            kb_ids = [anchor] if isinstance(anchor, str) and anchor and permitted else []
            origin_document = origin.get('knowledge_id') or origin.get('document_id')
            if kb_ids and origin_document:
                if not isinstance(origin_document, str):
                    raise StoreError('推荐问题的来源文档 ID 无效', 400)
                origin_base = anchor
                document_ids = [origin_document]
                kb_ids = []
        elif config['kb_selection_mode'] == 'selected':
            kb_ids = list(config['knowledge_bases'])
        elif config['kb_selection_mode'] == 'all':
            values = client.list_knowledge_bases().get('knowledge_bases', [])
            kb_ids = [item.get('id') or item.get('knowledge_base_id') for item in values
                      if not str(item.get('name', '')).startswith('_governance')]
        else:
            kb_ids = []
        whole_kb_ids = list(kb_ids)
    document_ids = list(dict.fromkeys(document_ids))
    document_bases = {}
    for document_id in document_ids:
        detail = client.get_document(None, document_id)
        kb_id = detail.get('knowledge_base_id')
        if not kb_id:
            raise StoreError('无法验证所选文档的知识库归属', 403)
        if document_id == origin_document and origin_base and kb_id != origin_base:
            raise StoreError('推荐问题的文档不属于已验证的来源知识库', 403)
        document_bases[document_id] = kb_id
        kb_ids.append(kb_id)
    kb_ids = list(dict.fromkeys(kb_ids))
    for kb_id in kb_ids:
        if not isinstance(kb_id, str) or not kb_id:
            raise StoreError('知识库 ID 无效', 400)
        client.get_knowledge_base(kb_id)
    config['_document_bases'] = document_bases
    config['_whole_knowledge_bases'] = whole_kb_ids
    config['_owner_id'] = owner_id
    if 'local_browser_enabled' in body and not isinstance(body['local_browser_enabled'], bool):
        raise StoreError('local_browser_enabled 必须为布尔值', 400)
    config['_local_browser_enabled'] = body.get('local_browser_enabled', False)
    config['web_search_enabled'] = config['web_search_enabled'] and body.get('web_search_enabled', True) is True
    for prefix, request_key, config_key in (('mcp', 'mcp_service_ids', 'mcp_services'), ('skills', 'skill_names', 'selected_skills')):
        selected = _ids(body, request_key)
        if selected:
            configured = config.get(config_key) or []
            if config[f'{prefix}_selection_mode'] == 'none' or (config[f'{prefix}_selection_mode'] == 'selected' and not set(selected).issubset(configured)):
                raise StoreError('提及的工具或 Skill 超出 Agent 配置范围', 403)
            config[f'{prefix}_selection_mode'] = 'selected'
            config[config_key] = selected
    config['_page_context'] = body.get('page_context')
    config['_query'] = body.get('query', '')
    config['_locale'] = body.get('_locale', 'zh-CN')
    result = {'agent_id': agent['id'], 'agent_config': config, 'knowledge_base_ids': kb_ids,
        'requested_knowledge_base_ids': requested_knowledge_base_ids,
        'knowledge_ids': document_ids, 'tag_scopes': tags, 'agent_enabled': config['agent_mode'] == 'smart-reasoning',
        'mentioned_items': copy.deepcopy(mentions), 'mcp_service_ids': _ids(body, 'mcp_service_ids'), 'skill_names': _ids(body, 'skill_names')}
    if has_image_attachments:
        _select_image_model(config, owner_id)
    return result


def allowed_knowledge_tools(config):
    names = config.get('allowed_tools')
    if names is None:
        names = DEFAULT_TOOLS + ['wiki_search']
    return set().union(*(TOOL_ALIASES.get(name, {name}) for name in names)) if names else set()


def apply_image_model(resolved, owner_id):
    """Route an actual image turn to the configured VLM after attachment preparation."""
    if not any(item.get('type') == 'image_url' for item in resolved.get('message_blocks', [])):
        return resolved
    config = resolved['agent_config']
    _select_image_model(config, owner_id)
    return resolved


def _select_image_model(config, owner_id):
    if not config.get('image_upload_enabled'):
        raise StoreError('当前 Agent 未启用图片输入', 400)
    model_id = config.get('vlm_model_id') or config.get('model_id')
    model = registry.model_config(model_id, owner_id)
    if model['type'] != 'VLLM' and not model.get('parameters', {}).get('supports_vision'):
        raise StoreError('请选择 VLLM 模型或明确支持图片的对话模型', 400)
    config['model_id'] = model_id
