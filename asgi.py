"""Serve the native Harness stream alongside the existing business API."""
from starlette.applications import Starlette
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.routing import Mount


def create_app(flask_app=None):
    if flask_app is None:
        from app import app as flask_app
    from webapi.harness import routes
    return Starlette(routes=[*routes, Mount('/', WSGIMiddleware(flask_app))])
