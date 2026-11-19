"""Only the native SHA command may run, and it stops before its client closes."""
import asyncio
import threading
from types import SimpleNamespace

import pytest

from agent.sandbox import ManagedOpenSandboxBackend, SandboxArtifacts


@pytest.mark.parametrize('late_init', [False, True])
def test_cancelled_archive_checksum_stops_before_backend_client_closes(monkeypatch, late_init):
    started, release, stopped, finished = (threading.Event() for _ in range(4))
    cancelled = threading.Event()
    state = {'running': False, 'closed': False}
    commands, interrupted, cancellations = [], [], []
    entry = SimpleNamespace(path='/workspace/output.txt', entry_type='file')

    def run(command, *, opts, handlers):
        assert not state['closed']
        assert 'hashlib.file_digest' in command
        commands.append(command)
        state['running'] = True
        try:
            if late_init:
                started.set()
                assert release.wait(3)
            handlers.on_init(SimpleNamespace(id='native-sha'))
            if not late_init:
                started.set()
            assert stopped.wait(3)
            return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), exit_code=143)
        finally:
            finished.set()

    def interrupt(identifier):
        assert not state['closed'], 'Late init must interrupt while its SDK client is open'
        interrupted.append(identifier)
        state['running'] = False
        stopped.set()

    def close():
        assert finished.is_set() and not state['running']
        state['closed'] = True

    native = SimpleNamespace(id='memory-only-archive', close=close,
        files=SimpleNamespace(search=lambda request: [entry]),
        commands=SimpleNamespace(run=run, interrupt=interrupt,
            get_command_status=lambda identifier: SimpleNamespace(running=state['running'])))
    backend = ManagedOpenSandboxBackend(sandbox=native, timeout=3)
    cancel = backend.cancel

    def record_cancel():
        result = cancel()
        cancellations.append(result['command_state'])
        cancelled.set()
        return result

    monkeypatch.setattr(backend, 'cancel', record_cancel)

    async def exercise():
        try:
            task = asyncio.create_task(SandboxArtifacts(backend)._asnapshot())
            assert await asyncio.to_thread(started.wait, 2)
            task.cancel()
            if late_init:
                assert await asyncio.to_thread(cancelled.wait, 2)
                assert cancellations[0] == 'interrupt_requested'
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 3)
        finally:
            # backend_for_session owns this order: cancel, then close the SDK client.
            await asyncio.to_thread(backend.cancel)
            native.close()

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        stopped.set()
    assert len(commands) == 1 and interrupted == ['native-sha']
    assert state['closed'] and not backend._commands and backend._inflight == 0
