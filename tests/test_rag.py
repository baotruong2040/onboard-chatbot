import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onboarding import storage
from onboarding.cli import main
from onboarding.config import Config
from onboarding.knowledge import import_documents, index_documents
from onboarding.openrouter import OpenRouterClient, OpenRouterError
from onboarding.rag import FALLBACK, ask, cosine


class FakeClient:
    query = [1, 0]
    calls = 0

    def embed(self, texts, *, input_type=None):
        if len(texts) == 2:
            return [[1, 0], [0, 1]]
        return [self.query]

    def chat(self, messages):
        self.calls += 1
        self.context = json.loads(messages[-1]["content"])["context"]
        return "Giờ làm việc là 08:30–17:30. [1]"


class RagTest(unittest.TestCase):
    def test_check_chat_does_not_embed_or_open_database(self):
        config = Config(Path("unused"), api_key="fake", embedding_model="embed", chat_model="chat")
        client = FakeClient()
        with patch("onboarding.cli.Config.load", return_value=config), patch(
            "onboarding.cli.OpenRouterClient", return_value=client
        ), patch.object(client, "chat", return_value="OK") as chat, patch.object(
            client, "embed"
        ) as embed, patch("onboarding.cli.initialize") as initialize, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["check-chat"]), 0)
            chat.assert_called_once()
            embed.assert_not_called()
            initialize.assert_not_called()
            self.assertIn("/chat/completions", output.getvalue())
            self.assertIn("OK", output.getvalue())

    def test_retrieval_fallback_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            storage.initialize(database)
            source = Path(directory) / "docs.json"
            source.write_text(json.dumps([
                {"document_id": "hours", "title": "Giờ làm việc", "content": "08:30–17:30", "source_title": "Demo"},
                {"document_id": "vpn", "title": "VPN", "content": "Gửi yêu cầu IT", "source_title": "Demo"}
            ]), encoding="utf-8")
            import_documents(database, source)
            client = FakeClient()
            index_documents(database, client, "fake")
            self.assertAlmostEqual(cosine([1, 0], [1, 0]), 1)
            answer = ask(database, client, "fake", "Giờ làm việc?")
            self.assertEqual(answer.sources[0]["document_id"], "hours")
            self.assertEqual(len(answer.sources), 1)
            self.assertEqual(client.context[0]["content"], "08:30–17:30")
            # Điểm thực tế người dùng báo: 0.366482, nằm dưới ngưỡng cũ 0.5.
            client.query = [0.366482, -(1 - 0.366482 ** 2) ** 0.5]
            self.assertEqual(ask(database, client, "fake", "Giờ làm việc?").sources[0]["document_id"], "hours")
            client.query = [0.2, -(1 - 0.2 ** 2) ** 0.5]
            calls = client.calls
            self.assertEqual(ask(database, client, "fake", "Ngoài kho?").text, FALLBACK)
            self.assertEqual(client.calls, calls)
            client.query = [-1, -1]
            trace = []
            self.assertEqual(ask(database, client, "fake", "Thời tiết?", debug=trace.append).text, FALLBACK)
            self.assertTrue(any("Fallback ở retrieval" in line for line in trace))
            self.assertEqual(client.calls, calls)
            with self.assertRaisesRegex(ValueError, "kb index"):
                ask(database, client, "changed-model", "Giờ làm việc?")
            client.query = [1, 0, 0]
            with self.assertRaisesRegex(ValueError, "Dimension"):
                ask(database, client, "fake", "Giờ làm việc?")
            client.query = [1, 0]
            config = Config(database, api_key="fake", embedding_model="fake", chat_model="fake")
            with patch("onboarding.cli.Config.load", return_value=config), patch(
                "onboarding.cli.OpenRouterClient", return_value=client
            ), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["ask", "Giờ làm việc?"]), 0)
                self.assertIn("hours", output.getvalue())
            with patch.object(client, "chat", return_value=FALLBACK):
                self.assertEqual(ask(database, client, "fake", "Thiếu thông tin").sources, [])
            model = "nvidia/nemotron-3-embed-1b:free"
            with storage.connect(database) as connection:
                connection.execute("UPDATE chunks SET embedding_model=?,embedding_input_type=NULL", (model,))
            with self.assertRaisesRegex(ValueError, "passage"):
                ask(database, client, model, "Giờ làm việc?")
            index_documents(database, client, model)
            self.assertEqual(ask(database, client, model, "Giờ làm việc?").sources[0]["document_id"], "hours")

    def test_empty_kb_and_chat_http_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "empty.db"
            storage.initialize(database)
            self.assertEqual(ask(database, None, "fake", "Hỏi?").text, FALLBACK)
        config = Config(Path("unused"), api_key="fake", embedding_model="fake", chat_model="chat")
        response = io.StringIO(json.dumps({"choices": [{"message": {"content": "Trả lời"}}]}))
        with patch("onboarding.openrouter.urlopen", return_value=response) as request:
            self.assertEqual(OpenRouterClient(config).chat([{"role": "user", "content": "Hỏi"}]), "Trả lời")
            self.assertTrue(request.call_args.args[0].full_url.endswith("/chat/completions"))
            self.assertEqual(json.loads(request.call_args.args[0].data)["model"], "chat")
        with patch("onboarding.openrouter.urlopen", return_value=io.StringIO('{"choices": []}')):
            with self.assertRaises(OpenRouterError):
                OpenRouterClient(config).chat([])

    def test_nemotron_embedding_modes(self):
        config = Config(Path("unused"), api_key="fake",
                        embedding_model="nvidia/nemotron-3-embed-1b:free")
        for purpose, expected in [("search_document", "passage"), ("search_query", "query")]:
            response = io.StringIO(json.dumps({"data": [{"index": 0, "embedding": [1, 0]}]}))
            with patch("onboarding.openrouter.urlopen", return_value=response) as request:
                OpenRouterClient(config).embed(["Nội dung"], input_type=purpose)
                self.assertEqual(json.loads(request.call_args.args[0].data)["input_type"], expected)
