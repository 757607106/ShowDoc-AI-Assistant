"""Translate individual WeKnora cards into one native interrupt resume request."""
import asyncio
import json
from datetime import datetime

from agent import registry, sessions
from governance.store import StoreError


def cards(state, session_id):
    from webapi.weknora_adapter import message_dict
    origins = {}
    def visit(snapshot):
        for item in snapshot.interrupts:
            origins[item.id] = (item, snapshot)
        for task in snapshot.tasks:
            if hasattr(task.state, 'interrupts'):
                visit(task.state)
    visit(state)
    result = []
    for interrupt, snapshot in origins.values():
        value = interrupt.value
        if not isinstance(value, dict):
            raise StoreError('原生中断未提供受支持的交互协议', 501)
        messages = [message_dict(message) for message in snapshot.values.get('messages', [])]
        finished = {message.get('tool_call_id') for message in messages if message.get('type') == 'tool'}
        calls = [call for message in messages for call in message.get('tool_calls', []) if call['id'] not in finished]
        actions = value.get('action_requests')
        for index, action in enumerate(actions if actions is not None else [value]):
            kind = 'tool_approval' if actions is not None else value.get('kind')
            if kind not in ('tool_approval', 'ask_user', 'mcp_oauth'):
                raise StoreError('当前 WeKnora 对接不支持此原生中断类型', 501)
            candidates = [call for call in calls if call['name'] == (action['name'] if actions is not None else kind)]
            call = next((item for item in candidates if item['args'] == action.get('args')), None) or (candidates[-1] if candidates else {})
            if call:
                calls.remove(call)
            request = ({'service_name': action['name'], 'mcp_tool_name': action['name'],
                        'description': action.get('description', ''), 'args': action['args']} if actions is not None
                       else value.get('request', {}))
            result.append({'id': f'{session_id}:{interrupt.id}:{index}', 'kind': kind, 'request': request,
                'tool_call_id': call.get('id'), 'status': 'suspended', 'created_at': snapshot.created_at,
                '_interrupt': interrupt.id, '_index': index,
                '_allowed': value.get('review_configs', [{}] * len(actions))[index].get('allowed_decisions', [])
                            if actions is not None else []})
    return result


def card_event(card):
    kind = card['kind']
    event = 'tool_approval_required' if kind == 'tool_approval' else 'mcp_oauth_required' if kind == 'mcp_oauth' else 'agent_prompt_required'
    data = {'pending_id': card['id'], 'kind': kind, 'tool_call_id': card['tool_call_id'],
            'suspendable': True, 'suspended': True, 'request': card['request']}
    if card.get('created_at'):
        data['requested_at'] = int(datetime.fromisoformat(card['created_at']).timestamp())
    if kind in ('tool_approval', 'mcp_oauth'):
        data.update(card['request'])
    if kind == 'tool_approval':
        data['args_json'] = json.dumps(card['request']['args'], ensure_ascii=False)
    return event, data


def _receipt(owner_id, session_id, state):
    checkpoint = state.config['configurable']['checkpoint_id']
    try:
        value = registry.record('harness_resume', session_id, owner_id)
    except StoreError as exc:
        if exc.status != 404:
            raise
        value = {}
    return value if value.get('checkpoint') == checkpoint else {
        'id': session_id, 'checkpoint': checkpoint, 'responses': {}}


def bind_card_ids(owner_id, session_id, state, pending, native_calls):
    """Dynamic tool subgraphs expose their call IDs on the official stream only."""
    receipt = _receipt(owner_id, session_id, state)
    bindings = receipt.setdefault('tool_ids', {})
    unused = list(native_calls)
    for card in pending:
        if not card['tool_call_id']:
            name = card['request'].get('mcp_tool_name', card['kind'])
            match = next((call for call in unused if call['name'] == name and
                          (card['kind'] != 'tool_approval' or call['args'] == card['request']['args'])), None)
            if match:
                bindings[card['id']] = match['id']
                unused.remove(match)
            card['tool_call_id'] = bindings.get(card['id'])
    if bindings:
        registry.save_record('harness_resume', receipt, owner_id)


def stage(user, pending_id, body, expected_kind):
    if expected_kind == 'mcp_oauth':
        raise StoreError('聊天内 OAuth 恢复尚未对接，请先在 MCP 服务设置中完成授权后重新发送', 501)
    from webapi.harness import read_snapshot
    parts = pending_id.split(':')
    if len(parts) != 3:
        raise StoreError('交互标识无效', 400)
    session_id = parts[0]
    with sessions._mutation(session_id, user['id']) as selected:
        state = asyncio.run(read_snapshot(user, selected))
        if state is None:
            raise StoreError('交互已失效，请重新加载会话', 409)
        pending = cards(state, session_id)
        card = next((item for item in pending if item['id'] == pending_id), None)
        if card is None or card['kind'] != expected_kind:
            raise StoreError('交互已失效，请重新加载会话', 409)
        if expected_kind == 'tool_approval':
            if body.get('scope') not in (None, 'once') or body.get('allow_in_session'):
                raise StoreError('当前原生对接仅支持本次工具审批', 501)
            if body.get('decision') not in ('approve', 'reject'):
                raise StoreError('审批决定无效', 400)
            response = {'type': body['decision']}
            if body['decision'] == 'reject':
                response['message'] = str(body.get('reason') or '用户拒绝')
            elif 'modified_args' in body and body['modified_args'] != card['request']['args']:
                if not isinstance(body['modified_args'], dict):
                    raise StoreError('修改参数必须为对象', 400)
                response = {'type': 'edit', 'edited_action': {
                    'name': card['request']['mcp_tool_name'], 'args': body['modified_args']}}
            if response['type'] not in card['_allowed']:
                raise StoreError('此原生中断不允许该审批决定', 400)
        elif expected_kind == 'ask_user':
            if body.get('kind') != 'ask_user' or not isinstance(body.get('response'), dict):
                raise StoreError('提问响应必须为 ask_user 对象', 400)
            response = body['response']
        receipt = _receipt(user['id'], session_id, state)
        if pending_id in receipt['responses']:
            raise StoreError('交互响应已提交，请重新加载会话', 409)
        receipt['responses'][pending_id] = response
        registry.save_record('harness_resume', receipt, user['id'])
        return all(item['id'] in receipt['responses'] for item in pending)


def consume(owner_id, session_id, state, pending_id):
    """Native pending interrupts, rather than an adapter flag, decide whether to resume."""
    pending = cards(state, session_id)
    try:
        previous = registry.record('harness_resume', session_id, owner_id)
        if pending_id in previous['responses'] and not any(item['id'] == pending_id for item in pending):
            return None
    except StoreError as exc:
        if exc.status != 404:
            raise
    receipt = _receipt(owner_id, session_id, state)
    if pending_id not in receipt['responses'] or not pending or any(item['id'] not in receipt['responses'] for item in pending):
        raise StoreError('交互决定尚未全部提交，或交互已失效', 409)
    resume = {}
    for card in pending:
        response = receipt['responses'][card['id']]
        if card['kind'] == 'tool_approval':
            resume.setdefault(card['_interrupt'], {'decisions': []})['decisions'].append(response)
        else:
            resume[card['_interrupt']] = response
    return resume
