"""Official LangGraph PostgreSQL persistence; checkpoints are not knowledge documents."""
import os
from contextlib import asynccontextmanager

import anyio
from psycopg.conninfo import conninfo_to_dict
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import PostgresStore


def database_url():
    value = os.getenv('AGENT_DATABASE_URL', '')
    if not value:
        raise RuntimeError('AGENT_DATABASE_URL 未配置；Agent 必须使用独立 PostgreSQL 数据库和账号')
    agent = conninfo_to_dict(value)
    platform = conninfo_to_dict(os.getenv('DATABASE_URL', ''))
    if not agent.get('dbname') or not agent.get('user'):
        raise RuntimeError('AGENT_DATABASE_URL 必须明确指定数据库和应用账号')
    if agent.get('dbname') == platform.get('dbname') or agent.get('user') == platform.get('user'):
        raise RuntimeError('Agent 与平台必须使用不同的 PostgreSQL 数据库和应用账号')
    return value


def make_checkpointer():
    return PostgresSaver.from_conn_string(database_url())


def async_checkpointer():
    return AsyncPostgresSaver.from_conn_string(database_url())


def sync_store():
    return PostgresStore.from_conn_string(database_url())


@asynccontextmanager
async def async_store():
    """Use the official Store's async methods without an orphaned batch task."""
    manager = sync_store()
    store = await anyio.to_thread.run_sync(manager.__enter__)
    try:
        yield store
    finally:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(lambda: manager.__exit__(None, None, None))


@asynccontextmanager
async def async_runtime():
    """Keep official checkpoint and cross-thread file stores alive for one request."""
    async with async_checkpointer() as saver, async_store() as store:
        yield saver, store


def initialize_checkpoints():
    with make_checkpointer() as saver:
        saver.setup()
    with sync_store() as store:
        store.setup()
