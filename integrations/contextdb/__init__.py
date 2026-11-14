"""ContextDB 云连接器:官方 REST 客户端 + MCP 工具调用 + CLI 诊断封装。

运行时通道分工:平台后端用 REST;Agent 知识库访问用 MCP(/v1/mcp);
ctxdb CLI 仅开发诊断(安装期 setup/status)。
"""

from integrations.contextdb.cli import ping as cli_ping
from integrations.contextdb.cli import status as cli_status
from integrations.contextdb.client import (
    DEFAULT_BASE_URL,
    ContextDBAuthError,
    ContextDBClient,
    ContextDBConflictError,
    ContextDBError,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "ContextDBAuthError",
    "ContextDBClient",
    "ContextDBConflictError",
    "ContextDBError",
    "cli_ping",
    "cli_status",
]
