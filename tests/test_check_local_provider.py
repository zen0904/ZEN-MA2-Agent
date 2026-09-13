from __future__ import annotations

import socket
import unittest
from urllib.error import URLError

from scripts.check_local_provider import check_slot_1, models_url


class _Response:
    def __init__(self, body: bytes): self.body = body
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.body


class LocalProviderHealthCheckTests(unittest.TestCase):
    def test_connection_refused_is_not_reachable(self):
        def refused(*_, **__):
            raise URLError(ConnectionRefusedError("refused"))
        result = check_slot_1("http://127.0.0.1:8080/v1", opener=refused)
        self.assertEqual(result.status, "NOT_REACHABLE")
        self.assertEqual(result.base_url, "http://127.0.0.1:8080/v1")

    def test_timeout_is_not_reachable(self):
        def timed_out(*_, **__):
            raise socket.timeout()
        result = check_slot_1("http://127.0.0.1:8080/v1", opener=timed_out)
        self.assertEqual(result.status, "NOT_REACHABLE")

    def test_non_json_response_is_unexpected_response(self):
        result = check_slot_1("http://127.0.0.1:8080/v1", opener=lambda *_args, **_kwargs: _Response(b"not json"))
        self.assertEqual(result.status, "UNEXPECTED_RESPONSE")

    def test_openai_models_inventory_is_reported(self):
        body = b'{"object":"list","data":[{"id":"qwen2.5-7b-instruct-q4_k_m"},{"id":"another-model"}]}'
        result = check_slot_1("http://127.0.0.1:8080/v1/", opener=lambda *_args, **_kwargs: _Response(body))
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.models, ("qwen2.5-7b-instruct-q4_k_m", "another-model"))
        self.assertEqual(models_url(result.base_url), "http://127.0.0.1:8080/v1/models")


if __name__ == "__main__":
    unittest.main()
