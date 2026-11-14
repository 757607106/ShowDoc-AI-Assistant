"""Flask blueprints；Wiki 通过 ContextDB 原生接口转发。"""

from flask import Blueprint

from webapi.agent import agent_bp
from webapi.knowledge import knowledge_bp
from webapi.auth import auth_bp
from webapi.contextdb import contextdb_bp
from webapi.platform import platform_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(contextdb_bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(agent_bp)
