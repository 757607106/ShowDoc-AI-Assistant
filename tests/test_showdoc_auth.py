from unittest.mock import Mock

import litellm
import pytest

from integrations.showdoc.auth import ShowDocAuthenticator


@pytest.mark.parametrize('content', ['a1B2', [{'type': 'text', 'text': 'a1'}, {'type': 'text', 'text': 'B2'}]])
def test_captcha_uses_sdk_with_original_credentials_endpoint_and_reply_rules(monkeypatch, content):
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'showdoc-key')
    authenticator = ShowDocAuthenticator()
    authenticator.qwen_api_url = 'https://llm.example/compatible-mode/v1/chat/completions/'
    authenticator.qwen_vl_model = 'custom-vision'
    completion = Mock(return_value={'choices': [{'message': {'content': content}}]})
    monkeypatch.setattr('integrations.showdoc.auth.litellm.completion', completion)
    monkeypatch.setattr('integrations.showdoc.auth.requests.post', Mock(side_effect=AssertionError('model calls must use SDK')))
    assert authenticator.recognize_captcha(b'image') == 'a1B2'
    options = completion.call_args.kwargs
    assert options['model'] == 'custom-vision'
    assert options['api_base'] == 'https://llm.example/compatible-mode/v1'
    assert options['custom_llm_provider'] == 'openai'
    assert options['api_key'] == 'showdoc-key' and options['timeout'] == 60
    assert options['messages'][0]['content'][0]['image_url']['url'] == 'data:image/png;base64,aW1hZ2U='
    completion.assert_called_once()


def test_captcha_sdk_failure_keeps_existing_none_contract_without_fallback(monkeypatch):
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'showdoc-key')
    completion = Mock(side_effect=litellm.APIError(status_code=503, message='unavailable', llm_provider='openai', model='vision'))
    monkeypatch.setattr('integrations.showdoc.auth.litellm.completion', completion)
    assert ShowDocAuthenticator().recognize_captcha(b'image') is None
    completion.assert_called_once()
