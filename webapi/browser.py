"""Keep retired browser URLs explicit without starting the browser daemon."""
from flask import Blueprint

from webapi.legacy_runtime import unavailable

browser_bp = Blueprint('browser', __name__)


@browser_bp.route('/api/v1/me/browser', methods=['GET', 'POST'])
@browser_bp.get('/api/v1/me/browser/extension')
@browser_bp.route('/api/v1/sessions/<session_id>/local-browser', methods=['GET', 'POST'])
@browser_bp.post('/api/v1/local-browser/extension/<endpoint>/authorize')
def retired_browser(session_id=None, endpoint=None):
    unavailable(session_id)
