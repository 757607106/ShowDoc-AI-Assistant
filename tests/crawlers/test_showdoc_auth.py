from unittest.mock import Mock

import httpx
import pytest

from integrations.showdoc.auth import ShowDocAuthenticator
from integrations.showdoc.project import ShowDocProjectManager


@pytest.mark.parametrize('content', ['a1B2', [{'type': 'text', 'text': 'a1'}, {'type': 'text', 'text': 'B2'}]])
def test_captcha_uses_sdk_with_original_credentials_endpoint_and_reply_rules(monkeypatch, content):
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'showdoc-key')
    authenticator = ShowDocAuthenticator()
    authenticator.qwen_api_url = 'https://llm.example/compatible-mode/v1/chat/completions/'
    authenticator.qwen_vl_model = 'custom-vision'
    completion = Mock(return_value={'choices': [{'message': {'content': content}}]})
    monkeypatch.setattr('integrations.showdoc.auth.chat_completion', completion)
    monkeypatch.setattr('integrations.showdoc.auth.requests.post', Mock(side_effect=AssertionError('model calls must use SDK')))
    assert authenticator.recognize_captcha(b'image') == 'a1B2'
    options = completion.call_args.kwargs
    assert options['model'] == 'custom-vision'
    assert options['base_url'] == 'https://llm.example/compatible-mode/v1'
    assert options['api_key'] == 'showdoc-key' and options['timeout'] == 60
    assert options['messages'][0]['content'][0]['image_url']['url'] == 'data:image/png;base64,aW1hZ2U='
    completion.assert_called_once()


def test_captcha_sdk_failure_keeps_existing_none_contract_without_fallback(monkeypatch):
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'showdoc-key')
    completion = Mock(side_effect=httpx.ConnectError('unavailable'))
    monkeypatch.setattr('integrations.showdoc.auth.chat_completion', completion)
    assert ShowDocAuthenticator().recognize_captcha(b'image') is None
    completion.assert_called_once()


def test_project_cache_is_scoped_to_token_and_group():
    manager = ShowDocProjectManager()
    projects = [{'item_id': '1', 'item_name': '项目一'}]
    manager.cache_projects(projects, 'token-a', 0)

    assert manager.get_cached_projects('token-a', 0) == projects
    assert manager.get_cached_projects('token-a', 1) is None
    assert manager.get_cached_projects('token-b', 0) is None
