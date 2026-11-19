"""WeKnora question starters, using the owner's model and official knowledge MCP."""
import asyncio
import hashlib
import json
import re
import time

from flask import Blueprint, g, jsonify, request

from agent import registry
from agent.citations import AnswerCitations
from agent.config import allowed_knowledge_tools, load_agent, resolve_request
from agent.tools import load_knowledge_mcp_tools
from governance.store import StoreError
from webapi.auth import client_for_user, user_id

chat_suggestions_bp = Blueprint('chat_suggestions', __name__)


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(part.get('text', '') for part in content if isinstance(part, dict))
    return str(content or '')


def _structured(output):
    if isinstance(output, dict):
        return output
    artifact = getattr(output, 'artifact', None)
    if artifact is not None:
        data = getattr(artifact, 'structured_content', None)
        if data is None and isinstance(artifact, dict):
            data = artifact.get('structured_content')
        if isinstance(data, dict):
            return data
        if isinstance(artifact, dict) and ('exit_code' in artifact or 'output_file' in artifact):
            return artifact
    content = _text(getattr(output, 'content', output))
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _tool_succeeded(output, native):
    return (getattr(output, 'status', None) != 'error' and
            native.get('exit_code') in (None, 0) and
            native.get('isError') is not True and native.get('success') is not False and
            native.get('errorCode') in (None, 0))


def _settings(config):
    section = config.get('question_suggestions') or {}
    if not isinstance(section, dict) or not isinstance(section.get('starters', {}), dict):
        raise StoreError('推荐问题配置必须为对象', 400)
    value = {'enabled': True, 'mode': 'hybrid', 'items': [], 'count': 6, **section.get('starters', {})}
    if not isinstance(value['enabled'], bool):
        raise StoreError('推荐问题开关必须为布尔值', 400)
    if value['mode'] not in ('curated', 'knowledge', 'hybrid'):
        raise StoreError('推荐问题模式无效', 400)
    if isinstance(value['count'], bool) or not isinstance(value['count'], int) or not 1 <= value['count'] <= 8:
        raise StoreError('推荐问题数量无效', 400)
    if not isinstance(value['items'], list) or len(value['items']) > 8 or any(
            not isinstance(item, str) or len(item) > 200 for item in value['items']):
        raise StoreError('最多配置8条、每条200字的推荐问题', 400)
    return value


def _merge(primary, knowledge, limit, hybrid=False):
    ordered = primary
    if hybrid and primary and knowledge:
        reserved = (limit + 1) // 3
        ordered = primary[:limit - reserved] + knowledge[:reserved] + primary[limit - reserved:] + knowledge[reserved:]
    else:
        ordered = primary + knowledge
    result, seen = [], set()
    for item in ordered:
        text = item.get('text', item.get('question', '')).strip()
        key = re.sub(r'\s+', '', text).casefold()
        if text and len(text) <= 200 and key not in seen:
            seen.add(key)
            result.append(item)
        if len(result) >= limit:
            break
    return result


async def _knowledge_questions(resolved, client, owner, role, query, count):
    config = {**resolved['agent_config'], 'access_level': 'read_only'}
    scope = resolved['knowledge_base_ids']
    if not scope or 'knowledge.search' not in allowed_knowledge_tools(config):
        return []
    client = client or client_for_user(owner)
    tools = await load_knowledge_mcp_tools(api_key=client.api_key, owner_id=owner, role=role,
                                         knowledge_base_ids=scope, agent_config=config)
    search = next((tool for tool in tools if tool.name == 'knowledge.search'), None)
    if search is None:
        raise StoreError('官方 MCP 未提供推荐问题所需的知识检索工具', 503)
    schema = search.args_schema
    properties = (schema.model_json_schema() if isinstance(schema, type) else schema).get('properties', {})
    whole = config.get('_whole_knowledge_bases', scope)
    groups = [group for group in (whole, [kb for kb in scope if kb not in whole]) if group]
    questions = []
    for group in groups:
        arguments = {'query': query[:512], 'knowledge_base_ids': group}
        if 'top_k' in properties:
            arguments['top_k'] = min(20, max(6, count * 2))
        output = await search.ainvoke(arguments)
        native = _structured(output)
        collector = AnswerCitations(group)
        success = _tool_succeeded(output, native)
        if not success:
            raise StoreError('ContextDB MCP 知识检索失败', 503)
        collector.register('knowledge.search', native, success=success)
        raw_chunks = native.get('chunks', native.get('results', []))
        for source in collector.references:
            raw = next((item for item in raw_chunks if item.get('chunk_id') == source['id']), {})
            metadata = raw.get('metadata') if isinstance(raw.get('metadata'), dict) else {}
            candidates = metadata.get('generated_questions', raw.get('generated_questions', []))
            question = metadata.get('standard_question') or raw.get('standard_question')
            source_type = 'faq' if isinstance(question, str) and question.strip() else 'document'
            if not question and isinstance(candidates, list) and candidates:
                candidate = candidates[0]
                question = candidate if isinstance(candidate, str) else candidate.get('question', candidate.get('text')) if isinstance(candidate, dict) else None
            if not question:
                question = next((line.strip(' #*-0123456789.、\t') for line in source['content'].splitlines()
                                 if 3 <= len(line.strip()) <= 200 and line.strip().endswith(('?', '？'))), None)
            if not question:
                title = source['title']
                if title == source['knowledge_id']:
                    title = source['content'].splitlines()[0].strip(' #*')[:60]
                question = f'“{title[:100]}”主要介绍了哪些内容？'
            if isinstance(question, str):
                questions.append({'question': question.strip(), 'source': source_type,
                    'knowledge_base_id': source['knowledge_base_id'], 'knowledge_id': source['knowledge_id']})
    return _merge([], questions, count)


@chat_suggestions_bp.get('/api/v1/agents/<agent_id>/suggested-questions')
def starters(agent_id):
    owner = user_id()
    config = load_agent(agent_id, owner)['config']
    settings = _settings(config)
    if not settings['enabled']:
        return jsonify(success=True, data={'questions': []})
    try:
        requested = int(request.args.get('limit', 0))
    except ValueError as exc:
        raise StoreError('推荐数量无效', 400) from exc
    count = min(30, requested) if requested > 0 else settings['count']
    curated = [{'question': item.strip(), 'source': 'agent_config'} for item in settings['items'] if item.strip()]
    if settings['mode'] == 'curated':
        return jsonify(success=True, data={'questions': _merge(curated, [], count)})
    if request.args.get('tag_scopes'):
        raise StoreError('ContextDB 暂无上游标签 ID 的可靠映射', 501)
    body = {'agent_id': agent_id}
    for field in ('knowledge_base_ids', 'knowledge_ids'):
        if request.args.get(field):
            body[field] = request.args[field].split(',')
    client = client_for_user()
    resolved = resolve_request(body, client=client, owner_id=owner, role=g.user['role'])
    key = hashlib.sha256(json.dumps(resolved, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cache_id = 'starters:' + key + ':' + str(count)
    try:
        cached = registry.record('question-starters', cache_id, owner)
    except StoreError as exc:
        if exc.status != 404:
            raise
        cached = None
    if cached and time.time() - cached['timestamp'] < 300:
        return jsonify(success=True, data={'questions': cached['questions']})
    try:
        knowledge = asyncio.run(asyncio.wait_for(_knowledge_questions(resolved, client, owner, g.user['role'],
            '主要业务功能、常见问题、使用指南', count), timeout=30))
    except StoreError:
        raise
    except Exception as exc:
        raise StoreError('官方 MCP 推荐问题读取失败', 503) from exc
    questions = _merge(curated if settings['mode'] == 'hybrid' else [], knowledge, count, settings['mode'] == 'hybrid')
    registry.save_record('question-starters', {'id': cache_id, 'timestamp': time.time(), 'questions': questions}, owner)
    return jsonify(success=True, data={'questions': questions})
