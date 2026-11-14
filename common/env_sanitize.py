"""本机运行环境净化(NO_PROXY IPv6 字面量会击穿 httpx URLPattern 解析)。"""

import os


def sanitize_no_proxy():
    """移除 NO_PROXY 中的 IPv6 字面量项(如 `[::1]`),避免 httpx/openai 客户端构造崩溃。

    当前 shell 的 NO_PROXY 常含 `[::1]`、`::1`;httpx(含 httpx2)在解析代理环境变量时
    会因非法端口报 InvalidURL。必须在构造任何 openai/langchain 客户端之前调用。
    """
    raw = os.environ.get('NO_PROXY') or os.environ.get('no_proxy') or ''
    if not raw or ('[' not in raw and ']' not in raw):
        return
    cleaned = ','.join(
        part.strip() for part in raw.split(',')
        if part.strip() and '[' not in part and ']' not in part
    )
    for name in ('NO_PROXY', 'no_proxy'):
        if cleaned:
            os.environ[name] = cleaned
        else:
            os.environ.pop(name, None)
