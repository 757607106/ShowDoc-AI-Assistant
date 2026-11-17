"""Business question schema over the official LangGraph interrupt primitive."""
import json

from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from governance.store import StoreError


def validate_response(value, schema=None):
    try:
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False)) > 100_000:
            raise ValueError('too large')
    except (TypeError, ValueError, RecursionError) as exc:
        raise StoreError('交互响应必须为不超过 100000 字符的有效 JSON', 400) from exc
    if schema is not None:
        from jsonschema.validators import validator_for
        from jsonschema.exceptions import ValidationError
        try:
            validator_for(schema)(schema).validate(value)
        except (ValidationError, RecursionError) as exc:
            raise StoreError('交互响应不符合原生响应结构', 400) from exc


def validate_responses(pending, responses):
    from agent.config import validate_response_format
    if not pending or not isinstance(responses, dict) or set(responses) != {item['id'] for item in pending}:
        raise StoreError('必须按当前原生中断 ID 完整提交响应', 409)
    for item in pending:
        response = responses[item['id']]
        value = item.get('value')
        schema = item.get('response_schema')
        if schema is None and isinstance(value, dict):
            schema = value.get('response_schema')
        validate_response(response, validate_response_format(schema) if schema is not None else None)
        if not isinstance(value, dict) or 'action_requests' not in value:
            continue
        from pydantic import TypeAdapter, ValidationError
        from langchain.agents.middleware.human_in_the_loop import HITLResponse
        try:
            parsed = TypeAdapter(HITLResponse).validate_python(response)
            actions, reviews = value['action_requests'], value['review_configs']
            if len(parsed['decisions']) != len(actions):
                raise ValueError('incomplete decisions')
            for action, review, decision in zip(actions, reviews, parsed['decisions'], strict=True):
                if decision['type'] not in review['allowed_decisions']:
                    raise ValueError('decision not allowed')
                if decision['type'] == 'edit' and decision['edited_action']['name'] != action['name']:
                    raise ValueError('cannot replace tool')
        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            raise StoreError('工具审批响应无效或超出允许范围', 400) from exc


def make_interaction_tools(session_id, owner_id):
    @tool
    def ask_user(question: str, options: list[str] | None = None,
                 multi_select: bool = False, fields: list[dict] | None = None,
                 allow_free_text: bool = True, *, runtime: ToolRuntime) -> str:
        """Ask the user for missing information using the chat's interactive question card."""
        if not question.strip() or len(question) > 8000:
            raise StoreError('请输入有效问题', 400)
        response = interrupt({'kind': 'ask_user', 'tool_call_id': runtime.tool_call_id, 'request': {
            'question': question, 'options': options or [], 'multi_select': multi_select,
            'fields': fields or [], 'allow_free_text': allow_free_text,
        }})
        return json.dumps(response, ensure_ascii=False)
    return [ask_user]
