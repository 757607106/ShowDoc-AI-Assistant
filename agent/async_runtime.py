"""Trusted configuration and identity bindings for the Agent Protocol service."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from agent import registry, sessions
from governance.database import connection
from governance.store import StoreError

GRAPH_ID = 'delegated_agent'
MAIN_GRAPH_ID = 'main_agent'
GRANT_KIND = 'async_delegation'
MAIN_KIND = 'main_run'


def configuration():
    path = Path(__file__).resolve().parents[1] / '.runtime' / 'async-agent.env'
    saved = dotenv_values(path) if path.is_file() else {}
    def value(key):
        return os.environ[key] if key in os.environ else saved.get(key, '') or ''
    return {'url': value('ASYNC_AGENT_RUNTIME_URL').rstrip('/'),
            'signing_key': value('ASYNC_AGENT_RUNTIME_SIGNING_KEY'),
            'enabled': value('ASYNC_AGENT_RUNTIME_ENABLED') == '1'}


def enabled():
    settings = configuration()
    try:
        url = urlsplit(settings['url'])
        valid = url.scheme in ('http', 'https') and bool(url.hostname) and not any(
            (url.username, url.password, url.query, url.fragment))
    except ValueError:
        valid = False
    return bool(settings['enabled'] and valid and len(settings['signing_key']) >= 32)


def _serializer():
    key = configuration()['signing_key']
    if len(key) < 32:
        raise StoreError('异步运行服务认证尚未配置', 503)
    return URLSafeTimedSerializer(key, salt='deepagents-async-delegation')


def headers(grant):
    token = _serializer().dumps({'owner_id': grant['owner_id'], 'grant_id': grant['id'],
                                 'kind': grant.get('_kind', GRANT_KIND)})
    return {'Authorization': 'Bearer ' + token}


def principal(token):
    try:
        claims = _serializer().loads(token, max_age=24 * 3600)
        kind = claims.get('kind', GRANT_KIND)
        if kind not in (GRANT_KIND, MAIN_KIND):
            raise StoreError('异步代理认证类型无效', 401)
        grant = registry.record(kind, claims['grant_id'], claims['owner_id'])
    except (BadSignature, SignatureExpired, KeyError, TypeError, StoreError) as exc:
        raise StoreError('异步代理认证无效或已过期', 401) from exc
    parent = sessions.get_session(grant.get('parent_session_id') or grant.get('session_id'),
                                  grant['owner_id'], _include_deleting=True)
    if parent['agent_config'].get('runtime') != 'deepagents':
        raise StoreError('父会话不允许异步执行', 403)
    with connection() as conn:
        user = conn.execute('SELECT * FROM workspace_users WHERE id=%s AND active', (grant['owner_id'],)).fetchone()
    if user is None:
        raise StoreError('账号已停用', 401)
    return user, grant


def create_main_grant(owner_id, selected, resolved):
    """Immutable execution/authorization binding for one main-session configuration."""
    grant = {'owner_id': owner_id, 'session_id': selected['id'], 'agent_id': resolved.get('agent_id'),
             'agent_config': resolved['agent_config'], 'knowledge_base_ids': list(resolved.get('knowledge_base_ids', [])),
             'knowledge_ids': list(resolved.get('knowledge_ids', [])), 'tag_scopes': list(resolved.get('tag_scopes', []))}
    grant['id'] = hashlib.sha256(json.dumps(grant, sort_keys=True, ensure_ascii=False,
                                           allow_nan=False).encode()).hexdigest()
    grant['_kind'] = MAIN_KIND
    return registry.save_record(MAIN_KIND, grant, owner_id)


def main_client(owner_id, session_id):
    grants = registry.records(MAIN_KIND, owner_id)
    grant = next((item for item in reversed(grants) if item['session_id'] == session_id), None)
    if grant is None:
        raise StoreError('当前会话没有官方运行绑定', 404)
    return client(grant), grant


def specification(child, *, owner_id, session_id, agent_id, config,
                  knowledge_base_ids, knowledge_ids, tag_scopes, persist):
    if persist and (not enabled() or not session_id):
        raise StoreError('异步代理需要已部署服务和所属会话', 503)
    settings = configuration()
    spec = {'name': child['name'], 'description': child['description'], 'graph_id': GRAPH_ID,
            'url': settings['url'] or 'http://127.0.0.1:2026', 'notify_parent': False}
    for key in ('update_strategy', 'mode'):
        if key in child:
            spec[key] = child[key]
    if persist:
        # This is an immutable configuration/authorization binding, not a run queue.
        grant = {'owner_id': owner_id, 'parent_session_id': session_id, 'agent_id': agent_id,
                 'subagent_name': child['name'], 'agent_config': config,
                 'knowledge_base_ids': list(knowledge_base_ids), 'knowledge_ids': list(knowledge_ids),
                 'tag_scopes': list(tag_scopes)}
        grant['id'] = hashlib.sha256(json.dumps(grant, sort_keys=True, ensure_ascii=False,
                                               allow_nan=False).encode()).hexdigest()
        registry.save_record(GRANT_KIND, grant, owner_id)
        spec['headers'] = headers(grant)
    return spec


def client(grant):
    from langgraph_sdk import get_client
    return get_client(url=configuration()['url'], headers=headers(grant))
