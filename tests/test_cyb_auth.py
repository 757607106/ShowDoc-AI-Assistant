import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
