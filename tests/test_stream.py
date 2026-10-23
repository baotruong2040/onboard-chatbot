import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from onboarding.config import Config
from onboarding.gemini import GeminiClient, GeminiError


def event(text=None, reason=None, thought=False):
    candidate = {}
    if text is not None:
        candidate["content"] = {"parts": [{"text": text, "thought": thought}]}
    if reason:
        candidate["finishReason"] = reason
    return ("data: " + json.dumps({"candidates": [candidate]}, ensure_ascii=False) + "\n\n").encode("utf-8")


class StreamTest(unittest.TestCase):
    def setUp(self):
        self.client = GeminiClient(Config(Path("unused"), api_key="secret", chat_model="gemini-test"))

    def test_incremental_utf8_and_exact_text(self):
        received = []
        first = event("  Xin chào\n")

        class LiveResponse(io.BytesIO):
            def readline(self, *args):
                if self.tell() >= len(first):
                    # Callback đã được gọi trước khi đọc event tiếp theo.
                    assert received == ["  Xin chào\n"] or len(received) == 2
                return super().readline(*args)

        response = LiveResponse(first + event("private", thought=True) + event("Việt Nam  ", "STOP"))
        with patch("onboarding.gemini.urlopen", return_value=response) as request:
            result = self.client.stream_chat([{"role": "user", "content": "hello"}], received.append)
            self.assertEqual(received, ["  Xin chào\n", "Việt Nam  "])
            self.assertEqual(result, "".join(received))
            self.assertTrue(request.call_args.args[0].full_url.endswith(":streamGenerateContent?alt=sse"))
            self.assertNotIn("secret", request.call_args.args[0].full_url)
        self.assertTrue(response.closed)

    def test_errors_after_partial_do_not_succeed(self):
        for tail in (b"", event(reason="MAX_TOKENS"), event(reason="SAFETY"), b"data: invalid\n\n",
                     b'data: {"error":{"message":"private"}}\n\n'):
            with self.subTest(tail=tail):
                received = []
                response = io.BytesIO(event("partial") + tail)
                with patch("onboarding.gemini.urlopen", return_value=response):
                    with self.assertRaises(GeminiError) as error:
                        self.client.stream_chat([], received.append)
                    self.assertEqual(received, ["partial"])
                    self.assertNotIn("private", str(error.exception))
                self.assertTrue(response.closed)
