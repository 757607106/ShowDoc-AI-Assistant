"""In-process Agent Protocol runs for harness tests: official graph, SDK-shaped client."""
import asyncio

from langgraph_sdk.schema import StreamPart


class FakeClient:
    def __init__(self, api, grant, records):
        self.api = api
        self.grant = grant
        self.records = records
        self.runs = _Runs(self)
        self.threads = _Threads(self)


class _Runs:
    def __init__(self, client):
        self.client = client

    async def create(self, thread_id, graph_id, *, input=None, command=None, context=None,
                     stream_mode=None, stream_subgraphs=False, multitask_strategy=None,
                     durability=None, metadata=None, **kwargs):
        import httpx
        if multitask_strategy == 'reject':
            for record in self.client.records.values():
                if record['thread_id'] == thread_id and record['status'] in ('pending', 'running'):
                    request = httpx.Request('POST', f'/threads/{thread_id}/runs')
                    raise httpx.HTTPStatusError('run already active', request=request,
                                                response=httpx.Response(409, request=request))
        run_id = f'run-{len(self.client.records) + 1}'
        record = {'run_id': run_id, 'thread_id': thread_id, 'status': 'pending', 'grant': self.client.grant,
                  'metadata': metadata or {}, 'input': input, 'command': command,
                  'context': context, 'stream_mode': stream_mode or ['values'],
                  'events': [], 'done': False, 'error': None}
        self.client.records[run_id] = record
        record['task'] = asyncio.create_task(self._execute(record))
        return dict(record)

    async def _execute(self, record):
        from agent import sessions
        from agent.checkpointer import async_checkpointer
        from agent.sandbox import backend_for_session
        from langgraph.types import Command
        grant = record['grant']
        selected = await asyncio.to_thread(sessions.get_session, grant['session_id'], grant['owner_id'])
        user = {'id': grant['owner_id'], 'role': 'admin'}
        resolved = {'agent_config': grant['agent_config'], 'knowledge_base_ids': grant['knowledge_base_ids']}
        try:
            async with backend_for_session(record['thread_id'], grant['owner_id'], grant['agent_config'], 'admin') as backend:
                async with async_checkpointer() as saver:
                    graph = await self.client.api._graph(saver, user, selected, resolved, load_tools=True, backend=backend)
                    config = {'configurable': {'thread_id': record['thread_id']}}
                    inputs = record['input']
                    if record['command'] is not None:
                        cmd = record['command']
                        inputs = Command(resume=cmd['resume'], update=cmd.get('update') or None)
                    stream = graph.astream(inputs, config, context=record['context'],
                                           stream_mode=record['stream_mode'], subgraphs=True,
                                           version='v2', durability='sync')
                    async for part in stream:
                        record['events'].append(part)
                    record['status'] = 'success'
        except asyncio.CancelledError:
            record['status'] = 'cancelled'
            raise
        except Exception as exc:
            record['status'] = 'error'
            record['error'] = str(exc)
            record['status_code'] = getattr(exc, 'status', 500)
        finally:
            record['done'] = True

    def join_stream(self, thread_id, run_id, *, cancel_on_disconnect=False, **kwargs):
        record = self.client.records[run_id]

        async def generate():
            index = 0
            while True:
                while index < len(record['events']):
                    part = record['events'][index]
                    index += 1
                    namespace = part.get('ns') or []
                    yield StreamPart(event=part['type'] + ('|' + '|'.join(namespace) if namespace else ''),
                                     data=part['data'])
                if record['done']:
                    break
                await asyncio.sleep(0.005)
            yield StreamPart(event='end', data={'status': record['status']})

        return generate()

    async def get(self, thread_id, run_id, **kwargs):
        record = self.client.records[run_id]
        return {'run_id': run_id, 'status': record['status'], 'error': record['error'],
                'metadata': record['metadata'], 'status_code': record.get('status_code')}

    async def list(self, thread_id, *, status=None, limit=100, offset=0, **kwargs):
        return [{'run_id': record['run_id'], 'status': record['status'], 'metadata': record['metadata']}
                for record in self.client.records.values()
                if record['thread_id'] == thread_id and (status is None or record['status'] == status)][:limit]

    async def cancel(self, thread_id, run_id, *, wait=False, **kwargs):
        record = self.client.records[run_id]
        record['task'].get_loop().call_soon_threadsafe(record['task'].cancel)
        if wait:
            while not record['done']:
                await asyncio.sleep(0.005)
        return dict(record)


class _Threads:
    def __init__(self, client):
        self.client = client

    async def create(self, *, thread_id=None, metadata=None, if_exists=None, **kwargs):
        return {'thread_id': thread_id, 'metadata': metadata or {}}

    async def delete(self, thread_id):
        for record in list(self.client.records.values()):
            if record['thread_id'] == thread_id:
                record['task'].cancel()


def install(monkeypatch, api):
    """Route the official SDK boundary to in-process runs; checkpoints stay in the test schema."""
    from agent import async_runtime
    records = {}
    monkeypatch.setattr(async_runtime, 'client', lambda grant: FakeClient(api, grant, records))
    monkeypatch.setattr(async_runtime, 'enabled', lambda: True)
