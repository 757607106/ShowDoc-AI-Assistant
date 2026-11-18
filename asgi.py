"""Serve the native Harness stream alongside the existing business API."""
from contextlib import asynccontextmanager

import anyio
from starlette.applications import Starlette
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.routing import Mount


@asynccontextmanager
async def lifespan(app):
    from agent.checkpointer import initialize_checkpoints
    from governance.database import initialize
    await anyio.to_thread.run_sync(initialize_checkpoints)
    await anyio.to_thread.run_sync(initialize)
    yield


def create_app(flask_app=None):
    if flask_app is None:
        from app import app as flask_app
    from webapi.harness import routes
    from webapi.sandbox_terminal import routes as terminal_routes
    return Starlette(routes=[*routes, *terminal_routes, Mount('/', WSGIMiddleware(flask_app))], lifespan=lifespan)
