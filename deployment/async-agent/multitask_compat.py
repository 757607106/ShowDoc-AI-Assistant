"""SHA-gated Aegra 0.11 multitask compatibility using its existing queue and lease."""
import asyncio
import hashlib
import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path


@asynccontextmanager
async def _lock(key, *, wait=True):
    from psycopg import AsyncConnection
    from aegra_api.settings import settings
    async with await AsyncConnection.connect(settings.db.database_url_sync, connect_timeout=5) as conn:
        function = 'pg_advisory_xact_lock' if wait else 'pg_try_advisory_xact_lock'
        cursor = await conn.execute(f'SELECT {function}(hashtextextended(%s,0))', (key,))
        yield True if wait else (await cursor.fetchone())[0]


async def prepare(original, session, thread_id, request, user, **kwargs):
    from fastapi import HTTPException
    from sqlalchemy import select
    from aegra_api.core.orm import Run as RunORM
    strategy = request.multitask_strategy or 'reject'
    if strategy not in ('reject', 'interrupt', 'enqueue'):
        raise HTTPException(422, 'Supported multitask strategies: reject, interrupt, enqueue')
    active_query = select(RunORM).where(RunORM.thread_id == thread_id, RunORM.user_id == user.identity,
                                        RunORM.status.in_(('pending', 'running')))
    try:
        async with asyncio.timeout(15), _lock('showdoc:aegra:admit:' + thread_id):
            active = (await session.scalars(active_query)).all()
            if strategy == 'reject' and active:
                raise HTTPException(409, 'Thread already has an active run')
            if strategy == 'interrupt':
                from aegra_api.api.runs import _request_run_interruption
                for run in active:
                    await _request_run_interruption(session, run, 'interrupt')
                # The execution lock survives terminal status until the old worker actually exits.
                async with _lock('showdoc:aegra:execute:' + thread_id):
                    if (await session.scalars(active_query.execution_options(populate_existing=True))).first():
                        raise HTTPException(409, 'Existing run has not stopped; retry after recovery')
                    return await original(session, thread_id, request, user, **kwargs)
            return await original(session, thread_id, request, user, **kwargs)
    except TimeoutError:
        raise HTTPException(409, 'Existing run has not stopped; retry later') from None


async def execute(original, run_id, worker_name):
    from sqlalchemy import select
    from aegra_api.core.orm import Run as RunORM, _get_session_maker
    from aegra_api.services.worker_executor import _push_back
    maker = _get_session_maker()
    async with maker() as session:
        thread_id = await session.scalar(select(RunORM.thread_id).where(
            RunORM.run_id == run_id, RunORM.status == 'pending'))
    if thread_id is None:
        return
    async with _lock('showdoc:aegra:execute:' + thread_id, wait=False) as acquired:
        if acquired:
            async with maker() as session:
                oldest = await session.scalar(select(RunORM.run_id).where(
                    RunORM.thread_id == thread_id, RunORM.status.in_(('pending', 'running'))).order_by(
                    RunORM.created_at, RunORM.run_id).limit(1))
            if oldest == run_id:
                return await original(run_id, worker_name)
    # shortcut: blocked runs retry at 50ms; use per-thread wakeups if queue contention grows.
    await asyncio.sleep(.05)
    await _push_back(run_id)


def apply():
    directory = Path(importlib.util.find_spec('aegra_api').origin).parent / 'services'
    changes = {
        'run_preparation.py': (
            '146889547b6fb14f786747f789f1e5a61949a162e3a71dc24d1514caaaa6dafc',
            'async def _prepare_run(\n', 'async def _prepare_run_unserialized(\n',
            '\n\nasync def _prepare_run(session, thread_id, request, user, **kwargs):\n'
            '    from aegra_api.services.showdoc_multitask import prepare\n'
            '    return await prepare(_prepare_run_unserialized, session, thread_id, request, user, **kwargs)\n'),
        'worker_executor.py': (
            'f84e0bfe621f399f04673711b818215d0857b1d170bfecc0a60e5311f0fd4873',
            '    async def _execute_with_lease(self, run_id: str, worker_name: str) -> None:\n',
            '    async def _execute_with_lease(self, run_id: str, worker_name: str) -> None:\n'
            '        from aegra_api.services.showdoc_multitask import execute\n'
            '        await execute(self._execute_with_lease_unserialized, run_id, worker_name)\n\n'
            '    async def _execute_with_lease_unserialized(self, run_id: str, worker_name: str) -> None:\n', '')}
    patched = {}
    for name, (digest, before, after, suffix) in changes.items():
        path = directory / name
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest or raw.decode().count(before) != 1:
            raise RuntimeError(f'Unexpected Aegra 0.11 source: {name}')
        patched[path] = raw.decode().replace(before, after, 1) + suffix
        compile(patched[path], str(path), 'exec')
    for path, source in patched.items():
        path.write_text('# Modified by ShowDoc: PostgreSQL thread admission and execution locks.\n' + source)
    (directory / 'showdoc_multitask.py').write_bytes(Path(__file__).read_bytes())


if __name__ == '__main__':
    apply()
