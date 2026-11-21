import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from affine_lab.providers import GeminiProvider, ProviderError, ReplayProvider


class ProviderTests(unittest.TestCase):
    def test_replay_never_invents_an_unknown_case(self):
        with self.assertRaises(ProviderError):
            ReplayProvider().generate("Unknown", 5, "Not in the synthetic corpus")

    def test_model_name_is_not_an_arbitrary_url(self):
        with self.assertRaises(ProviderError):
            GeminiProvider(api_key="private-test-key", model="../escape?key=value")

    def test_request_uses_https_and_header_not_query_key(self):
        reply = {"candidates": [{"content": {"parts": [{"text": "Synthetic reply."}]}}]}
        provider = GeminiProvider(api_key="private-test-key", model="test-model")
        with patch(
            "urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(reply).encode()),
        ) as send:
            self.assertEqual(
                provider.generate("Rohaan", 3, "Synthetic input"), "Synthetic reply."
            )
        request = send.call_args.args[0]
        self.assertTrue(
            request.full_url.startswith("https://generativelanguage.googleapis.com/")
        )
        self.assertNotIn("private-test-key", request.full_url)
        self.assertNotIn("private-test-key", request.data.decode())
        self.assertEqual(request.get_header("X-goog-api-key"), "private-test-key")

    def test_http_error_does_not_leak_body_or_fall_back(self):
        provider = GeminiProvider(api_key="private-test-key", model="test-model")
        error = HTTPError(
            "https://example.invalid",
            403,
            "Forbidden",
            {},
            io.BytesIO(b"private-test-key"),
        )
        with (
            patch("urllib.request.urlopen", side_effect=error),
            self.assertRaises(ProviderError) as caught,
        ):
            provider.generate("Rohaan", 3, "Synthetic input")
        self.assertIn("403", str(caught.exception))
        self.assertNotIn("private-test-key", str(caught.exception))

    def test_empty_response_is_explicit_failure(self):
        provider = GeminiProvider(api_key="private-test-key", model="test-model")
        with (
            patch(
                "urllib.request.urlopen", return_value=io.BytesIO(b'{"candidates":[]}')
            ),
            self.assertRaisesRegex(ProviderError, "no text"),
        ):
            provider.generate("Rohaan", 3, "Synthetic input")
