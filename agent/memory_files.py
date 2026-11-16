"""Owner/Agent policy for native Deep Agents memory files; no extraction pipeline."""
from agent import registry
from governance.store import StoreError


def policy(owner_id):
    values = {item['id']: item.get('value', {}) for item in registry.records('settings', owner_id)}
    workspace = values.get('memory-config', {}).get('enabled', False) is True
    personal = values.get('memory-preference', {}).get('enabled', True) is True
    return {'workspace_enabled': workspace, 'user_enabled': personal, 'effective': workspace and personal,
            'write_mode': 'native_file', 'max_items': 0, 'item_count': 0,
            'supported': True, 'storage_mode': 'agents_md', 'structured_memory_supported': False}


def namespace(owner_id, agent_id):
    if not isinstance(owner_id, str) or not owner_id or not isinstance(agent_id, str) or not agent_id:
        raise StoreError('长期记忆必须绑定已认证成员与 Agent', 400)
    return owner_id, 'agents', agent_id, 'memory'
