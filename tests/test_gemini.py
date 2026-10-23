import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from onboarding.config import Config
from onboarding.gemini import GeminiClient, GeminiError


class GeminiTest(unittest.TestCase):
    def test_chat_contract_and_rejected_responses(self):
        client = GeminiClient(Config(Path("unused"), api_key="secret", chat_model="gemini-test"))
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"thought": True, "text": "private"}, {"text": "  OK\n"}]}}]}
        with patch("onboarding.gemini.urlopen", return_value=io.StringIO(json.dumps(payload))) as request:
            self.assertEqual(client.chat([{"role": "system", "content": "system"}, {"role": "user", "content": "hello"}]), "  OK\n")
            body = json.loads(request.call_args.args[0].data)
            self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "system")
            self.assertEqual(body["contents"][0]["role"], "user")
            self.assertEqual(body["generationConfig"]["maxOutputTokens"], 4096)
            self.assertTrue(request.call_args.args[0].full_url.endswith("models/gemini-test:generateContent"))
            self.assertNotIn("secret", request.call_args.args[0].full_url)
        for bad in ({"candidates": []}, {"candidates": [{"finishReason": "MAX_TOKENS"}]},
                    {"candidates": [{"finishReason": "SAFETY"}]},
                    {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"thought": True, "text": "private"}]}}]}):
            with patch("onboarding.gemini.urlopen", return_value=io.StringIO(json.dumps(bad))):
                with self.assertRaises(GeminiError) as error:
                    client.chat([])
                self.assertNotIn("private", str(error.exception))

    def test_query_task_and_missing_vectors(self):
        client = GeminiClient(Config(Path("unused"), api_key="secret", embedding_model="gemini-embedding-001"))
        payload = {"embeddings": [{"values": [1, 0]}]}
        with patch("onboarding.gemini.urlopen", return_value=io.StringIO(json.dumps(payload))) as request:
            client.embed(["query"], input_type="search_query")
            self.assertEqual(json.loads(request.call_args.args[0].data)["requests"][0]["taskType"], "RETRIEVAL_QUERY")
        with patch("onboarding.gemini.urlopen", return_value=io.StringIO('{"embeddings":[]}')):
            with self.assertRaises(GeminiError):
                client.embed(["query"])
