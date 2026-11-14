"""Retired execution endpoints cannot start the former application runtime."""
from governance.store import StoreError


def unavailable(session_id=None):
    if session_id is not None:
        if not isinstance(session_id, str):
            raise StoreError('session_id 必须是字符串', 400)
        from agent import sessions
        sessions.get_session(session_id)
    raise StoreError('旧 Agent 执行接口已停用；历史数据保留，请使用官方 Deep Agents 会话接口', 410)
