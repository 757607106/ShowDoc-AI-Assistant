"""Flask blueprints；Wiki 通过 ContextDB 原生接口转发。"""

from flask import Blueprint

from webapi.agent import agent_bp
from webapi.knowledge import knowledge_bp
from webapi.auth import auth_bp
from webapi.contextdb import contextdb_bp
from webapi.platform import platform_bp
from webapi.agents import agents_bp
from webapi.runtime_settings import runtime_settings_bp
from webapi.chat_interactions import chat_interactions_bp
from webapi.chat_resources import chat_resources_bp
from webapi.chat_suggestions import chat_suggestions_bp
from webapi.browser import browser_bp
from webapi.terminal import terminal_bp
from webapi.mcp_runtime import mcp_runtime_bp
from webapi.model_runtime import model_runtime_bp
from webapi.skill_runtime import skill_runtime_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(contextdb_bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(runtime_settings_bp)
    app.register_blueprint(chat_interactions_bp)
    app.register_blueprint(chat_resources_bp)
    app.register_blueprint(chat_suggestions_bp)
    app.register_blueprint(browser_bp)
    app.register_blueprint(terminal_bp)
    app.register_blueprint(mcp_runtime_bp)
    app.register_blueprint(model_runtime_bp)
    app.register_blueprint(skill_runtime_bp)
