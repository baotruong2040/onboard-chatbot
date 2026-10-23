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
from onboarding.rag import Answer, FALLBACK


class ChatTest(unittest.TestCase):
    def test_chat_commands_errors_and_persisted_exchanges(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "chat.db"
            config = Config(database, api_key="fake", embedding_model="fake", chat_model="fake")
            source = {"source": 1, "document_id": "hours", "title": "Giờ", "source_title": "Demo"}
            replies = iter([ValueError("HTTP 429"), Answer("08:30 [1]", [source]), Answer(FALLBACK, [])])

            def streaming_ask(*args, on_text, **kwargs):
                reply = next(replies)
                if isinstance(reply, Exception):
                    on_text("partial")
                    raise reply
                on_text(reply.text[:3])
                on_text(reply.text[3:])
                return reply
            with patch("onboarding.cli.Config.load", return_value=config), patch(
                "onboarding.cli.GeminiClient"
            ), patch("builtins.input", side_effect=["", "/help", "/unknown", "Lỗi mạng", "Giờ?", "Thời tiết?", "/exit"]), patch(
                "onboarding.cli.ask", side_effect=streaming_ask
            ) as ask, contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["chat"]), 0)
                self.assertEqual(ask.call_count, 3)
                self.assertIn("08:30", output.getvalue())
                self.assertEqual(output.getvalue().count("08:30 [1]"), 1)
            storage.initialize(database)
            with storage.connect(database) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
                rows = connection.execute("SELECT role,content,sources_json FROM messages ORDER BY id").fetchall()
                self.assertEqual([row["role"] for row in rows], ["user", "assistant", "user", "assistant"])
                self.assertEqual(json.loads(rows[1]["sources_json"])[0]["document_id"], "hours")
                self.assertEqual(rows[3]["content"], FALLBACK)

    def test_eof_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Config(Path(directory) / "chat.db", api_key="fake", embedding_model="fake", chat_model="fake")
            with patch("onboarding.cli.Config.load", return_value=config), patch(
                "onboarding.cli.GeminiClient"
            ), patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["chat"]), 0)
