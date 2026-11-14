"""Agent grants use ContextDB's live group roster; execution keeps the actor's KB ACL."""
import copy

from agent import registry
from governance.database import connection
from governance.store import StoreError


def _client(owner):
    from webapi.auth import client_for_user
    return client_for_user(owner)


def _pages(client, path, key, **params):
    page = 1
    while True:
        result = client._request('GET', path, params={**params, 'page': page, 'page_size': 500})
        values = result.get(key, [])
        yield from values
        if len(values) < 500 or page * 500 >= result.get('total', page * 500 + 1):
            return
        page += 1


def groups(actor):
    client = _client(actor)
    profile = client.current_permissions()
    memberships = {str(item['group_id']): item['membership_role'] for item in profile.get('groups', [])}
    result = []
    for value in _pages(client, '/v1/workspaces/groups', 'groups'):
        key = str(value['group_id'])
        if value.get('status', 'active') != 'active' or key not in memberships:
            continue
        result.append({**value, 'id': key, 'description': '', 'owner_id': value.get('created_by', ''),
            'owner_tenant_id': 1, 'my_role': 'admin' if memberships[key] == 'group_admin' else 'viewer',
            'is_owner': False, 'member_count': None})
    return result


def group(actor, group_id, *, edit=False):
    value = next((item for item in groups(actor) if item['id'] == str(group_id)), None)
    if not value or (edit and value['my_role'] != 'admin'):
        raise StoreError('无权访问或管理此 ContextDB 用户组', 403)
    return value


def _shares(agent_id=None):
    with connection() as conn:
        rows = conn.execute("SELECT owner_id,payload FROM runtime_records WHERE kind='agent_share'").fetchall()
    return [(row['owner_id'], row['payload']) for row in rows if agent_id is None or row['payload']['agent_id'] == agent_id]


def _member(owner, actor, group_id):
    profile = _client(actor).current_permissions()
    membership = next((item for item in profile.get('groups', []) if str(item['group_id']) == str(group_id)), None)
    if not membership or profile.get('evaluation_state', 'active') != 'active':
        return False
    member_id = profile['member']['member_id']
    # Verify in the source workspace too; numeric group IDs alone are not a cross-workspace identity.
    return any(item['member_id'] == member_id and item.get('status', 'active') == 'active'
               for item in _pages(_client(owner), '/v1/workspaces/groups/members', 'members', group_id=int(group_id)))


def resource_owner(agent_id, actor):
    from agent.config import BUILTINS
    if not agent_id or agent_id == 'platform-agent' or agent_id in BUILTINS:
        return actor
    if any(item['id'] == agent_id for item in registry.records('agent', actor)):
        return actor
    for owner, share in _shares(agent_id):
        if owner != actor and _member(owner, actor, share['organization_id']):
            registry.record('agent', agent_id, owner)
            return owner
    raise StoreError('Agent 不存在或共享权限已撤销', 404)


def check_execution(actor, config):
    owner = config.get('_resource_owner_id', actor)
    if owner != actor and resource_owner(config.get('_agent_id'), actor) != owner:
        raise StoreError('Agent 共享权限已撤销', 403)
    return owner


def disabled_ids(actor):
    with connection() as conn:
        row = conn.execute('SELECT preferences FROM platform_users WHERE id=%s', (actor,)).fetchone()
    return (row['preferences'] or {}).get('disabled_agent_ids', []) if row else []


def shared_agents(actor, organization_id=None):
    from agent.config import load_agent
    values, disabled = [], set(disabled_ids(actor))
    for owner, share in _shares():
        if organization_id is not None and share['organization_id'] != str(organization_id):
            continue
        if owner != actor and not _member(owner, actor, share['organization_id']):
            continue
        try:
            agent = load_agent(share['agent_id'], owner)
        except StoreError as exc:
            if exc.status == 404:
                continue
            raise
        config = agent['config']
        values.append({'agent': agent, 'share_id': share['id'], 'organization_id': share['organization_id'],
            'org_name': share['organization_name'], 'permission': share['permission'], 'source_tenant_id': 1,
            'shared_at': share['created_at'], 'shared_by_user_id': owner,
            'web_search_ready': False,
            'disabled_by_me': agent['id'] in disabled, 'is_mine': owner == actor,
            '_resource_owner_id': owner})
    return values


def accessible_agent_configs(actor):
    from agent.config import list_agents
    configs = [{**copy.deepcopy(item['config']), '_resource_owner_id': actor} for item in list_agents(actor)]
    configs.extend({**copy.deepcopy(item['agent']['config']), '_resource_owner_id': item['_resource_owner_id']}
                   for item in shared_agents(actor) if not item['is_mine'])
    return configs
