"""Align Aegra 0.11 HITL status with the pinned DeepAgents AsyncSubAgent protocol."""
import hashlib
import importlib.util
from pathlib import Path

root = Path(importlib.util.find_spec('aegra_api').origin).parent
path = root / 'services' / 'run_executor.py'
source = path.read_text()
if hashlib.sha256(source.encode()).hexdigest() != '8db539539f7bc95c13a41f67be2f20c9ce9a872b3a7d08d8fd386b2c50104e55':
    raise RuntimeError('Review Aegra run status compatibility before changing the pinned version')
source = source.replace('status="interrupted",\n                thread_status="interrupted",',
                        'status="success",\n                thread_status="interrupted",', 1)
source = source.replace('status = "interrupted" if final_output.has_interrupt else "success"',
                        'status = "success"', 1)
assert source.count('\n                status="interrupted",') == 1  # Real cancellation keeps its native status.
compile(source, str(path), 'exec')
path.write_text('# Modified by ShowDoc: DeepAgents 0.7.35 HITL status compatibility.\n' + source)

path = root / 'models' / 'threads.py'
source = path.read_text()
if hashlib.sha256(source.encode()).hexdigest() != '17a860d5764452b1fbbfed4a212c493b22929e08600703aff9c069f9ebb1469c':
    raise RuntimeError('Review Aegra Thread model compatibility')
source = source.replace('class Thread(BaseModel):', '''class Thread(BaseModel):
    values: dict[str, Any] | None = None
    interrupts: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
''', 1)
compile(source, str(path), 'exec')
path.write_text('# Modified by ShowDoc: Agent Protocol Thread values and interrupts.\n' + source)

path = root / 'api' / 'threads.py'
source = path.read_text()
if hashlib.sha256(source.encode()).hexdigest() != 'd4184c29b9a9712b6e2d976560aa178be212a18118a7b62e52f25e3527506f2e':
    raise RuntimeError('Review Aegra Thread GET compatibility')
source = source.replace('''    return _serialize_thread(thread)


@router.patch("/threads/{thread_id}",''', '''    result = _serialize_thread(thread)
    if result.metadata.get("graph_id"):
        from agent.async_work import _interrupts
        state = await get_thread_state(thread_id, subgraphs=True, checkpoint_ns=None, user=user)
        result.values = state.values
        result.interrupts = {"": _interrupts(state.model_dump())}
    return result


@router.patch("/threads/{thread_id}",''', 1)
assert 'result.interrupts = {"": _interrupts(state.model_dump())}' in source
compile(source, str(path), 'exec')
path.write_text('# Modified by ShowDoc: hydrate Thread GET from native graph state.\n' + source)
