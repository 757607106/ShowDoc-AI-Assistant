"""Real PostgreSQL Store lifecycle through its native asynchronous methods."""
import asyncio
import threading
from contextlib import contextmanager

import anyio
import pytest
from langgraph.store.postgres import PostgresStore

from agent import checkpointer


def pending_batch_tasks():
    return [task for task in asyncio.all_tasks() if not task.done()
            and task.get_coro().__qualname__ == '_run'
            and task.get_coro().cr_code.co_filename.endswith('langgraph/store/base/batch.py')]


def test_official_store_native_async_methods_persist_without_background_batch():
    async def exercise():
        async with checkpointer.async_store() as store:
            assert isinstance(store, PostgresStore)
            await store.aput(('lifecycle', 'native'), 'proof', {'content': 'native-async'}, index=False)
            assert (await store.aget(('lifecycle', 'native'), 'proof')).value == {'content': 'native-async'}
            assert len(await store.asearch(('lifecycle', 'native'))) == 1
        assert store.conn.closed and pending_batch_tasks() == []
        async with checkpointer.async_store() as reopened:
            assert (await reopened.aget(('lifecycle', 'native'), 'proof')).value['content'] == 'native-async'
            await reopened.adelete(('lifecycle', 'native'), 'proof')
            assert await reopened.aget(('lifecycle', 'native'), 'proof') is None
        assert reopened.conn.closed and pending_batch_tasks() == []
    asyncio.run(exercise())


@pytest.mark.parametrize('exit_kind', ['exception', 'cancel'])
def test_store_connection_closes_off_loop_even_when_request_is_cancelled(monkeypatch, exit_kind):
    native_factory = checkpointer.sync_store
    threads = []

    @contextmanager
    def observed_factory():
        threads.append(threading.get_ident())
        try:
            with native_factory() as native:
                yield native
        finally:
            threads.append(threading.get_ident())

    monkeypatch.setattr(checkpointer, 'sync_store', observed_factory)

    async def exercise():
        loop_thread = threading.get_ident()
        if exit_kind == 'exception':
            with pytest.raises(RuntimeError, match='request failed'):
                async with checkpointer.async_store() as store:
                    assert await store.aget(('lifecycle',), 'missing') is None
                    raise RuntimeError('request failed')
        else:
            with anyio.CancelScope() as scope:
                async with checkpointer.async_store() as store:
                    await store.aput(('lifecycle',), 'cancelled', {'committed': True}, index=False)
                    scope.cancel()
                    await anyio.sleep(0)
        assert store.conn.closed and pending_batch_tasks() == []
        assert len(threads) == 2 and all(thread != loop_thread for thread in threads)
    asyncio.run(exercise())
