"""WeKnora-compatible Agent configuration endpoints."""
import asyncio
import os
from flask import Blueprint, g, jsonify, request

from agent.config import (DEFAULT_TOOLS, allowed_knowledge_tools, copy_agent, delete_agent, list_agents,
                          load_agent, save_agent)
from governance.store import StoreError

agents_bp = Blueprint('agents', __name__)


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise StoreError('请求必须为 JSON 对象', 400)
    return value


def _view(value):
    config = {**value['config'], 'retrieval_provider': 'contextdb', 'retain_retrieval_history': True}
    if config.get('sandbox_config_id') == 'state-backend':
        config['sandbox_config_id'] = ''
    return {**value, 'config': config}


@agents_bp.route('/api/v1/agents', methods=['GET', 'POST'])
@agents_bp.route('/api/v1/agents/builtin')
def agents():
    if request.method == 'POST':
        return jsonify(success=True, data=_view(save_agent(body(), g.user['id']))), 201
    values = list_agents(g.user['id'])
    if request.path.endswith('/builtin'):
        values = [item for item in values if item['is_builtin']]
    elif request.args.get('creator') == 'others':
        values = [item for item in values if item['is_builtin']]
    return jsonify(success=True, data=[_view(value) for value in values], disabled_own_agent_ids=[])


@agents_bp.route('/api/v1/agents/<agent_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def agent(agent_id):
    if request.method == 'DELETE':
        delete_agent(agent_id, g.user['id'])
        return jsonify(success=True)
    value = save_agent(body(), g.user['id'], agent_id) if request.method in ('PUT', 'PATCH') else load_agent(agent_id, g.user['id'])
    return jsonify(success=True, data=_view(value))


@agents_bp.route('/api/v1/agents/<agent_id>/copy', methods=['POST'])
def duplicate(agent_id):
    return jsonify(success=True, data=_view(copy_agent(agent_id, g.user['id']))), 201


@agents_bp.route('/api/v1/agents/tools')
def tools():
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from webapi.auth import client_for_user
    api_key = client_for_user().api_key
    async def discover():
        client = MultiServerMCPClient({'contextdb': {'transport': 'streamable_http',
            'url': os.getenv('CONTEXTDB_MCP_URL', 'https://context-database.aliyuncs.com/v1/mcp'), 'headers': {'X-API-Key': api_key}}})
        return await client.get_tools()
    try:
        discovered = asyncio.run(discover())
    except Exception as exc:
        raise StoreError(f'官方 MCP 工具目录暂不可用（{type(exc).__name__}）', 502) from exc
    definitions = [
        ('ask_user', '询问用户', '暂停并等待用户补充信息', {}),
        ('list_governance_releases', '采集批次', '查看本人采集发布记录', {}),
        ('get_capture_provenance', '采集溯源', '查看本人采集快照来源', {}),
    ]
    native_tools = ['task', 'write_todos', 'read_file', 'ls', 'glob', 'grep', 'write_file', 'edit_file', 'delete']
    catalog = [{'name': name, 'label': label, 'description': description,
        'group': 'knowledge' if name != 'ask_user' else 'interaction', 'requirement': requirement,
        'danger': False}
        for name, label, description, requirement in definitions]
    for candidate in discovered:
        schema = candidate.args_schema.model_json_schema() if isinstance(candidate.args_schema, type) else candidate.args_schema
        if not candidate.name.startswith('knowledge.') or not set(schema.get('properties', {})).intersection(
                ('knowledge_base_id', 'knowledge_base_ids', 'document_id', 'document_ids')):
            continue
        read_only = (candidate.metadata or {}).get('readOnlyHint') is True
        if not read_only:
            continue
        if g.user['role'] != 'admin' and candidate.name in ('knowledge.create_base', 'knowledge.delete_base', 'knowledge.update_base'):
            continue
        catalog.append({'name': candidate.name, 'label': candidate.name, 'description': candidate.description,
            'group': 'knowledge', 'requirement': {}, 'danger': False})
    defaults = allowed_knowledge_tools({'allowed_tools': None}) | {'ask_user'}
    return jsonify(success=True, data={'tools': catalog,
        'default_tools': [item['name'] for item in catalog if item['name'] in defaults], 'switch_managed_tools': native_tools})


@agents_bp.route('/api/v1/agents/type-presets')
def presets():
    rows = [('rag-qa', '文档问答', DEFAULT_TOOLS, {}),
            ('wiki-qa', 'Wiki 问答', ['wiki_search', 'search_knowledge', 'ask_user'], {'any_of': ['wiki']}),
            ('hybrid-rag-wiki', '混合检索', [*DEFAULT_TOOLS, 'wiki_search'], {}),
            ('custom', '自定义', None, {})]
    return jsonify(success=True, data=[{'id': key, 'i18n': {'zh-CN': {'label': name, 'description': name},
        'en-US': {'label': key, 'description': key}}, 'config': {'allowed_tools': sorted(allowed_knowledge_tools({'allowed_tools': allowed}) | {'ask_user'}),
            'retain_retrieval_history': True} if allowed else None,
        'kb_filter': requirements} for key, name, allowed, requirements in rows])


@agents_bp.route('/api/v1/agents/placeholders')
def placeholders():
    values = [{'name': 'query', 'label': '用户问题', 'description': '当前用户问题'},
              {'name': 'web_search_status', 'label': '网络搜索状态', 'description': '本轮是否启用网络搜索'},
              {'name': 'knowledge_bases', 'label': '知识库列表', 'description': '本轮实际知识库范围'},
              {'name': 'current_time', 'label': '当前时间', 'description': '当前日期（Asia/Shanghai）'},
              {'name': 'current_week', 'label': '当前星期', 'description': '当前星期'},
              {'name': 'yesterday', 'label': '昨天日期', 'description': '昨天的日期'},
              {'name': 'language', 'label': '用户语言', 'description': '本轮界面语言'}]
    return jsonify(success=True, data={key: values for key in ('all', 'system_prompt', 'agent_system_prompt',
        'context_template', 'rewrite_system_prompt', 'rewrite_prompt', 'fallback_prompt')})
