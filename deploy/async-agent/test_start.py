"""The deployment must reject missing or mismatched authentication before serving."""
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class StartTests(unittest.TestCase):
    def test_authentication_is_required_before_uvicorn(self):
        auth_type = type('Auth', (), {})
        serve = Mock()
        modules = {'langgraph_sdk': SimpleNamespace(Auth=auth_type),
                   'agent.async_service': SimpleNamespace(auth=auth_type(), graph=lambda: None),
                   'uvicorn': SimpleNamespace(run=serve)}
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'aegra.json'
            for auth, key, path, allowed in (
                    ('noop', 'test-key', 'agent.async_service:auth', False),
                    ('custom', '', 'agent.async_service:auth', False),
                    ('custom', 'test-key', 'missing:auth', False),
                    ('custom', 'test-key', 'agent.async_service:auth', True)):
                config.write_text(json.dumps({'auth': {'path': path}}))
                serve.reset_mock()
                with self.subTest(auth=auth, key_present=bool(key), path=path), patch.dict(
                        'sys.modules', modules), patch.dict(os.environ, {
                            'AUTH_TYPE': auth, 'ASYNC_AGENT_RUNTIME_SIGNING_KEY': key,
                            'AEGRA_CONFIG': str(config)}, clear=True):
                    if allowed:
                        runpy.run_path(str(Path(__file__).with_name('start.py')))
                        serve.assert_called_once_with('aegra_api.main:app', host='0.0.0.0', port=2026)
                    else:
                        with self.assertRaises(RuntimeError):
                            runpy.run_path(str(Path(__file__).with_name('start.py')))
                        serve.assert_not_called()


if __name__ == '__main__':
    unittest.main()
