"""ctxdb CLI 子进程封装(仅开发诊断用途)。

运行时数据通道分工(见 docs/architecture/contextdb-integration-notes.md):
- 平台后端(webapi)→ ContextDB 官方 REST(integrations.contextdb.client)
- Agent 知识库访问 → ContextDB MCP(/v1/mcp,langchain-mcp-adapters 挂载)
- ctxdb CLI → 只用于安装期 setup/status 与开发期诊断,不参与平台运行时
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

CTXDB_AGENT = os.getenv("CTXDB_AGENT", "qoder")


def _binary():
    found = shutil.which("ctxdb")
    if found:
        return found
    candidate = os.path.expanduser("~/.local/bin/ctxdb")
    if os.access(candidate, os.X_OK):
        return candidate
    raise RuntimeError("ctxdb CLI 未安装(参考 docs/architecture/contextdb-integration-notes.md 安装步骤)")


def run(args, *, timeout=30, check=True):
    """运行 ctxdb 子命令并返回解析后的 JSON;失败抛 RuntimeError(stderr 摘要)。"""
    command = [_binary(), *args, "--agent", CTXDB_AGENT, "--json"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(f"ctxdb {' '.join(args)} 失败({completed.returncode}): {stderr[:300]}")
    stdout = completed.stdout.strip()
    try:
        return json.loads(stdout)
    except ValueError:
        return stdout


def status():
    """配置与连通性诊断(等价 ctxdb status --json)。"""
    return run(["status"])


def ping():
    """轻量连通性诊断。"""
    return run(["ping"])
