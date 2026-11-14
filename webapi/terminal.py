"""Retired Docker terminal ticket endpoint."""
from flask import Blueprint

from webapi.legacy_runtime import unavailable

terminal_bp = Blueprint('terminal', __name__)


@terminal_bp.post('/api/v1/sessions/<session_id>/sandbox/terminal-ticket')
def terminal_ticket(session_id):
    unavailable(session_id)
