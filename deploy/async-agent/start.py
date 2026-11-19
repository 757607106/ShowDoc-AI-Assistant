"""Fail closed before Aegra's optional-auth fallback can serve requests."""
import os
import json
from pathlib import Path

from langgraph_sdk import Auth
import uvicorn

from agent.async_service import auth, graph


if os.environ.get('AUTH_TYPE') != 'custom' or not os.environ.get('ASYNC_AGENT_RUNTIME_SIGNING_KEY'):
    raise RuntimeError('Custom authentication and a runtime signing key are required')
if not isinstance(auth, Auth) or not callable(graph):
    raise RuntimeError('The configured runtime auth and graph factory are required')
config = json.loads(Path(os.environ['AEGRA_CONFIG']).read_text())
if config.get('auth', {}).get('path') != 'agent.async_service:auth':
    raise RuntimeError('The runtime configuration must use the verified custom auth instance')
uvicorn.run('aegra_api.main:app', host='0.0.0.0', port=2026)
