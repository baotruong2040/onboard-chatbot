import tempfile
import unittest
from pathlib import Path

from onboarding import storage
from onboarding.config import Config
from onboarding.gemini import GeminiError

try:
    from fastapi.testclient import TestClient
    from onboarding.api import create_app
except ModuleNotFoundError as error:
    if error.name not in {"fastapi", "httpx"}:
        raise
    TestClient = None


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.error = False

    def chat(self, messages):
        self.calls += 1
        if self.error:
            raise GeminiError("secret-key-must-not-appear")
        return "  Xin chào\n<script>alert(1)</script>  "


@unittest.skipIf(TestClient is None, "Cần pip install -e .[test] (FastAPI/httpx)")
class ApiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "web.sqlite3"
        self.provider = FakeClient()
        self.config = Config(self.database, api_key="secret-key-must-not-appear", embedding_model="fake", chat_model="fake")
        self.client = self.enterContext(TestClient(create_app(self.config, self.provider)))

    def new(self):
        response = self.client.post("/api/conversations")
        self.assertEqual(response.status_code, 201)
        return response.json()["conversation_id"]

    def test_create_send_reload_and_new_session(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        self.assertEqual(self.provider.calls, 0)
        first, second = self.new(), self.new()
        path = f"/api/conversations/{first}/messages"
        self.assertEqual(self.client.get(path).json()["messages"], [])
        response = self.client.post(path, json={"message": "Giờ làm việc?"})
        self.assertEqual(response.status_code, 200)
        answer = response.json()
        self.assertEqual(answer["answer"], "  Xin chào\n<script>alert(1)</script>  ")
        rows = self.client.get(path).json()["messages"]
        self.assertEqual([r["role"] for r in rows], ["user", "assistant"])
        self.assertEqual(rows[1]["id"], answer["message_id"])
        self.assertEqual(rows[1]["content"], answer["answer"])
        self.assertEqual(self.client.get(f"/api/conversations/{second}/messages").json()["messages"], [])
        self.assertIn("Trợ lý Onboarding", self.client.get("/").text)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        with storage.connect(self.database) as connection:
            row = connection.execute("SELECT answer_type,sources_json FROM messages WHERE id=?", (answer["message_id"],)).fetchone()
            self.assertEqual(tuple(row), ("unknown", "[]"))

    def test_validation_missing_session_and_provider_error(self):
        path = f"/api/conversations/{self.new()}/messages"
        for message in ["", "  ", "x" * 4001, 42]:
            self.assertEqual(self.client.post(path, json={"message": message}).status_code, 422)
        self.assertEqual(self.client.get("/api/conversations/missing/messages").status_code, 404)
        self.assertEqual(self.client.post("/api/conversations/missing/messages", json={"message": "Hi"}).status_code, 404)
        self.assertEqual(self.provider.calls, 0)
        self.provider.error = True
        response = self.client.post(path, json={"message": "Hi"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn(self.config.api_key, response.text)
        self.assertEqual(self.client.get(path).json()["messages"], [])
