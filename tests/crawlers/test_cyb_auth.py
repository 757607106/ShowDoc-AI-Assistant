import unittest
from unittest.mock import patch

import httpx

from crawlers.cyb import CYBAuthenticator


class CYBAuthTests(unittest.TestCase):
    def setUp(self):
        CYBAuthenticator.clear_token_cache()

    def tearDown(self):
        CYBAuthenticator.clear_token_cache()

    def test_reuses_token_between_authenticator_instances(self):
        first = CYBAuthenticator(phone="13800000000", password="secret")
        second = CYBAuthenticator(phone="13800000000", password="secret")

        with patch.object(CYBAuthenticator, "_login_uncached", return_value="token-1") as login:
            self.assertEqual(first.login(), "token-1")
            self.assertEqual(second.login(), "token-1")

        login.assert_called_once_with(max_retries=3)

    def test_force_login_replaces_cached_token(self):
        authenticator = CYBAuthenticator(phone="13800000000", password="secret")

        with patch.object(
            CYBAuthenticator,
            "_login_uncached",
            side_effect=["token-1", "token-2"],
        ) as login:
            self.assertEqual(authenticator.login(), "token-1")
            self.assertEqual(authenticator.login(force=True), "token-2")

        self.assertEqual(login.call_count, 2)

    def test_captcha_uses_model_api_and_preserves_base_url_and_image(self):
        authenticator = CYBAuthenticator(phone="13800000000", password="secret")
        authenticator.qwen_api_key = "crawler-key"
        authenticator.vl_model = "custom-vision"
        with patch('crawlers.cyb.DASHSCOPE_API_URL', 'https://llm.example/v1/chat/completions/'), \
                patch.object(authenticator, '_request_json', side_effect=AssertionError('model calls must use SDK')), \
                patch('crawlers.cyb.chat_completion', return_value={
                    'choices': [{'message': {'content': '验证码：a1B2'}}]}) as completion:
            self.assertEqual(authenticator.recognize_captcha('aW1hZ2U='), 'a1B2')
        options = completion.call_args.kwargs
        self.assertEqual(options['model'], 'custom-vision')
        self.assertEqual(options['base_url'], 'https://llm.example/v1')
        self.assertEqual(options['api_key'], 'crawler-key')
        self.assertEqual(options['timeout'], 45)
        self.assertEqual(options['messages'][0]['content'][0]['image_url']['url'], 'data:image/png;base64,aW1hZ2U=')
        completion.assert_called_once()

    def test_captcha_keeps_segmented_reply_and_validates_image_before_call(self):
        authenticator = CYBAuthenticator()
        authenticator.qwen_api_key = 'crawler-key'
        response = {'choices': [{'message': {'content': [{'type': 'text', 'text': 'A1'}, {'type': 'text', 'text': 'b2'}]}}]}
        with patch('crawlers.cyb.chat_completion', return_value=response) as completion:
            self.assertEqual(authenticator.recognize_captcha('data:image/png;base64,aW1hZ2U='), 'A1b2')
            with self.assertRaisesRegex(RuntimeError, 'Base64'):
                authenticator.recognize_captcha('not valid base64!')
        completion.assert_called_once()

    def test_captcha_preserves_sdk_error_without_retrying_or_http_fallback(self):
        authenticator = CYBAuthenticator()
        authenticator.qwen_api_key = 'crawler-key'
        failure = httpx.ConnectError('unavailable')
        with patch('crawlers.cyb.chat_completion', side_effect=failure) as completion:
            with self.assertRaises(httpx.ConnectError):
                authenticator.recognize_captcha('aW1hZ2U=')
        completion.assert_called_once()


if __name__ == "__main__":
    unittest.main()
