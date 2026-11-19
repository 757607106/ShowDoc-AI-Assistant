"""Translate individual WeKnora cards into one native interrupt resume request."""
import asyncio
import json
from datetime import datetime

from agent import registry, sessions
from agent.interactions import validate_response as _validate_response, validate_responses
from governance.store import StoreError


def response_schema(interrupt):
    schema = getattr(interrupt, 'response_schema', None)
    if schema is not None and not isinstance(schema, dict):
        from pydantic import TypeAdapter
        schema = TypeAdapter(schema).json_schema()
    if schema is None and isinstance(interrupt.value, dict):
        schema = interrupt.value.get('response_schema')
    if schema is not None:
        from agent.config import validate_response_format
        schema = validate_response_format(schema)
    return schema


def _ask_request(value):
    return {'question': value.get('question'), 'options': value.get('options') or [],
            'multi_select': value.get('multi_select', False), 'fields': value.get('fields') or [],
            'allow_free_text': value.get('allow_free_text', True)}


def _legacy_ask_call(request, calls, requests):
    # Old checkpoints lack the native ID: bind only a unique request/call pair.
    request = _ask_request(request)
    if sum(_ask_request(item) == request for item in requests) != 1:
        return {}
    matches = [call for call in calls if call['name'] == 'ask_user' and _ask_request(call['args']) == request]
    return matches[0] if len(matches) == 1 else {}


def interrupt_origins(state):
    origins = {}
    def visit(snapshot):
        for item in snapshot.interrupts:
            origins[item.id] = (item, snapshot)
        for task in snapshot.tasks:
            if hasattr(task.state, 'interrupts'):
                visit(task.state)
    visit(state)
    return origins


def validate_native_resume(state, responses):
    validate_responses([{'id': item.id, 'value': item.value, 'response_schema': response_schema(item)}
                        for item, _ in interrupt_origins(state).values()], responses)


def cards(state, session_id):
    from webapi.weknora.adapter import message_dict
    origins = interrupt_origins(state)
    ask_requests = [item.value.get('request', {}) for item, _ in origins.values()
                    if isinstance(item.value, dict) and item.value.get('kind') == 'ask_user']
    result = []
    for interrupt, snapshot in origins.values():
        value = interrupt.value
        schema = response_schema(interrupt)
        if not isinstance(value, dict):
            value = {'kind': 'native_interrupt', 'request': value}
        messages = [message_dict(message) for message in snapshot.values.get('messages', [])]
        finished = {message.get('tool_call_id') for message in messages if message.get('type') == 'tool'}
        calls = [call for message in messages for call in message.get('tool_calls', []) if call['id'] not in finished]
        actions = value.get('action_requests')
        reviews = value.get('review_configs')
        if not (isinstance(actions, list) and actions and isinstance(reviews, list) and len(reviews) == len(actions)
                and all(isinstance(action, dict) and isinstance(action.get('name'), str)
                        and isinstance(action.get('args'), dict) for action in actions)
                and all(isinstance(review, dict) and isinstance(review.get('allowed_decisions'), list) for review in reviews)):
            actions = None
        for index, action in enumerate(actions if actions is not None else [value]):
            kind = 'tool_approval' if actions is not None else value.get('kind')
            request_value = value.get('request')
            if kind == 'ask_user' and not (isinstance(request_value, dict) and isinstance(request_value.get('question'), str)):
                kind = 'native_interrupt'
            if kind == 'mcp_oauth' and not (isinstance(request_value, dict) and isinstance(request_value.get('service_id'), str)):
                kind = 'native_interrupt'
            if actions is None and kind not in ('ask_user', 'mcp_oauth'):
                kind = 'native_interrupt'
            candidates = [call for call in calls if call['name'] == (action['name'] if actions is not None else kind)]
            if kind == 'ask_user':
                native_id = value.get('tool_call_id')
                if native_id is not None:
                    # Dynamic subgraph interrupts may bubble up without their calls in this snapshot.
                    if not isinstance(native_id, str) or not native_id:
                        raise StoreError('原生提问中断的工具标识无效', 501)
                    call = {'id': native_id}
                else:
                    call = _legacy_ask_call(value.get('request', {}), calls, ask_requests)
            elif kind == 'native_interrupt' and isinstance(value.get('tool_call_id'), str):
                call = {'id': value['tool_call_id']}
            else:
                call = next((item for item in candidates if item['args'] == action.get('args')), None) or (candidates[-1] if candidates else {})
            if call in calls:
                calls.remove(call)
            request = ({'service_name': action['name'], 'mcp_tool_name': action['name'],
                        'description': action.get('description', ''), 'args': action['args']} if actions is not None
                       else {'value': value.get('request', value)} if kind == 'native_interrupt'
                       else value.get('request', {}))
            allowed = (reviews[index].get('allowed_decisions', [])
                       if actions is not None else [])
            if actions is not None:
                request['allowed_decisions'] = allowed
                args_schema = reviews[index].get('args_schema')
                if args_schema:
                    request['args_schema'] = args_schema
            if kind == 'native_interrupt' and schema is not None:
                request['response_schema'] = schema
            result.append({'id': f'{session_id}:{interrupt.id}:{index}', 'kind': kind, 'request': request,
                'tool_call_id': call.get('id'), 'status': 'suspended', 'created_at': snapshot.created_at,
                '_interrupt': interrupt.id, '_index': index,
                '_allowed': allowed, '_response_schema': schema})
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
    bound_ids = {card['tool_call_id'] for card in pending if card['tool_call_id']}
    unused = [call for call in native_calls if call['id'] not in bound_ids]
    ask_requests = [card['request'] for card in pending if card['kind'] == 'ask_user']
    for card in pending:
        if not card['tool_call_id']:
            if card['kind'] == 'ask_user':
                match = _legacy_ask_call(card['request'], native_calls, ask_requests)
                if match and match['id'] not in bound_ids:
                    card['tool_call_id'] = bindings[card['id']] = match['id']
                    bound_ids.add(match['id'])
                    unused.remove(match)
                continue
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
            if body.get('decision') not in ('approve', 'edit', 'reject', 'respond'):
                raise StoreError('审批决定无效', 400)
            response = {'type': body['decision']}
            if body['decision'] == 'reject':
                response['message'] = str(body.get('reason') or '用户拒绝')
            elif body['decision'] == 'respond':
                if not isinstance(body.get('message'), str):
                    raise StoreError('工具响应必须为文本', 400)
                response['message'] = body['message']
            elif body['decision'] == 'edit' or 'modified_args' in body and body['modified_args'] != card['request']['args']:
                if not isinstance(body.get('modified_args'), dict):
                    raise StoreError('修改参数必须为对象', 400)
                response = {'type': 'edit', 'edited_action': {
                    'name': card['request']['mcp_tool_name'], 'args': body['modified_args']}}
                _validate_response(body['modified_args'], card['request'].get('args_schema'))
            if response['type'] not in card['_allowed']:
                raise StoreError('此原生中断不允许该审批决定', 400)
        elif expected_kind == 'mcp_oauth':
            decision = body.get('decision')
            service_id = card['request']['service_id']
            if decision not in ('authorize', 'cancel') or body.get('service_id', service_id) != service_id:
                raise StoreError('MCP 授权决定或服务无效', 400)
            if decision == 'authorize':
                from agent import mcp_auth
                service = registry.record('mcp', service_id, user['id'])
                if (not service.get('enabled') or service.get('auth_config', {}).get('auth_type') != 'oauth'
                        or mcp_auth.status(user['id'], service)['state'] not in ('authorized', 'refreshable')):
                    raise StoreError('请先完成当前 MCP 服务授权', 409)
            response = {'decision': decision, 'authorized': decision == 'authorize'}
        elif expected_kind == 'ask_user':
            if body.get('kind') != 'ask_user' or not isinstance(body.get('response'), dict):
                raise StoreError('提问响应必须为 ask_user 对象', 400)
            response = body['response']
        elif expected_kind == 'native_interrupt':
            if body.get('kind') != expected_kind or 'response' not in body:
                raise StoreError('请提交原生中断响应', 400)
            response = body['response']
        else:
            raise StoreError('交互类型无效', 400)
        _validate_response(response, card.get('_response_schema') if expected_kind != 'tool_approval' else None)
        receipt = _receipt(user['id'], session_id, state)
        if pending_id in receipt['responses']:
            raise StoreError('交互响应已提交，请重新加载会话', 409)
        receipt['responses'][pending_id] = response
        if all(item['id'] in receipt['responses'] for item in pending):
            _resume_values(pending, receipt['responses'])
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
    return _resume_values(pending, receipt['responses'])


def _resume_values(pending, responses):
    resume = {}
    for card in pending:
        response = responses[card['id']]
        if card['kind'] == 'tool_approval':
            resume.setdefault(card['_interrupt'], {'decisions': []})['decisions'].append(response)
        else:
            resume[card['_interrupt']] = response
    for card in pending:
        _validate_response(resume[card['_interrupt']], card.get('_response_schema'))
    return resume
