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
from onboarding.knowledge import import_documents, index_documents, split_chunks
from onboarding.openrouter import OpenRouterClient, OpenRouterError


class FakeClient:
    def embed(self, texts, *, input_type=None):
        return [[1.0, 0.5] for _ in texts]


class KnowledgeTest(unittest.TestCase):
    def test_import_index_update_and_failure_atomicity(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            storage.initialize(database)
            self.assertEqual(import_documents(database, Path("data/demo_knowledge.json")), 12)
            self.assertEqual(index_documents(database, FakeClient(), "fake-v1"), 12)
            import_documents(database, Path("data/demo_knowledge.json"))
            self.assertEqual(storage.list_documents(database)[0]["indexed"], 1)
            index_documents(database, FakeClient(), "fake-v2")
            self.assertTrue(all(row["embedding_model"] == "fake-v2" for row in storage.read_chunks(database)))
            self.assertEqual(storage.read_chunks(database)[0]["embedding_dimension"], 2)
            with patch.object(FakeClient, "embed", return_value=[[float("nan")]]):
                with self.assertRaises(OpenRouterError):
                    index_documents(database, FakeClient(), "broken")
            self.assertEqual(storage.read_chunks(database)[0]["embedding_model"], "fake-v2")
            document = json.loads(Path("data/demo_knowledge.json").read_text(encoding="utf-8"))["documents"][0]
            document["content"] = "Nội dung mới"
            source = Path(directory) / "update.json"
            source.write_text(json.dumps([document]), encoding="utf-8")
            import_documents(database, source)
            self.assertEqual(storage.list_documents(database)[0]["indexed"], 0)

    def test_csv_validation_and_cli(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            database = Path(directory) / "test.db"
            source = Path(directory) / "demo.csv"
            source.write_text('document_id,title,content,source_title\ndemo,Tiêu đề,Nội dung,Nguồn\n', encoding="utf-8-sig")
            args = ["--env-file", str(Path(directory) / "missing"), "--db", str(database), "kb"]
            self.assertEqual(main(args + ["import", str(source)]), 0)
            self.assertEqual(main(args + ["list"]), 0)
            with patch("onboarding.cli.OpenRouterClient", return_value=FakeClient()):
                self.assertEqual(main(args + ["index"]), 0)
            source.write_text("document_id,title\nbad,Thiếu content\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_documents(database, source)
            self.assertEqual(len(storage.list_documents(database)), 1)
            self.assertTrue(all(len(chunk) <= 1000 for chunk in split_chunks("a" * 2500)))

    def test_http_contract_order_and_errors(self):
        config = Config(Path("unused"), api_key="test-secret", embedding_model="fake")
        response = io.StringIO(json.dumps({"data": [
            {"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}
        ]}))
        with patch("onboarding.openrouter.urlopen", return_value=response) as request:
            self.assertEqual(OpenRouterClient(config).embed(["a", "b"]), [[1, 0], [0, 1]])
            body = json.loads(request.call_args.args[0].data)
            self.assertEqual(body["input"], ["a", "b"])
            self.assertEqual(body["encoding_format"], "float")
        from urllib.error import HTTPError
        with patch("onboarding.openrouter.urlopen", side_effect=HTTPError("url", 401, "secret", {}, None)):
            with self.assertRaisesRegex(OpenRouterError, "HTTP 401") as error:
                OpenRouterClient(config).embed(["a"])
            self.assertNotIn("secret", str(error.exception))


if __name__ == "__main__":
    unittest.main()
