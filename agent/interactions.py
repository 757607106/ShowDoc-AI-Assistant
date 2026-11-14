"""Business question schema over the official LangGraph interrupt primitive."""
import json

from langchain_core.tools import tool
from langgraph.types import interrupt

from governance.store import StoreError


def make_interaction_tools(session_id, owner_id):
    @tool
    def ask_user(question: str, options: list[str] | None = None,
                 multi_select: bool = False, fields: list[dict] | None = None,
                 allow_free_text: bool = True) -> str:
        """Ask the user for missing information using the chat's interactive question card."""
        if not question.strip() or len(question) > 8000:
            raise StoreError('请输入有效问题', 400)
        response = interrupt({'kind': 'ask_user', 'request': {
            'question': question, 'options': options or [], 'multi_select': multi_select,
            'fields': fields or [], 'allow_free_text': allow_free_text,
        }})
        return json.dumps(response, ensure_ascii=False)
    return [ask_user]
