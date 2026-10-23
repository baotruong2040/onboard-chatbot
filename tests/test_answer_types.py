import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from onboarding import storage
from onboarding.gemini import GeminiError
from onboarding.rag import ask, format_answer


class NaturalAnswerTest(unittest.TestCase):
    def test_complete_text_preserved_and_stored_without_classification(self):
        text = "  **Chi tiết**\n\n1. Bắt đầu 08:00.\n2. Có thể kết thúc 17:00.\n\nGiả định: nghỉ 1 giờ.\n  "
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "chat.db"
            storage.initialize(db)
            client = Mock()
            client.chat.return_value = text
            answer = ask(db, client, "fake", "Giờ làm?")
            self.assertEqual(answer.text, text)
            self.assertEqual(format_answer(answer), text)
            self.assertEqual(answer.answer_type, "unknown")
            self.assertEqual(answer.sources, [])
            client.embed.assert_not_called()
            prompt = client.chat.call_args.args[0][0]["content"]
            self.assertIn("không trả JSON", prompt)
            session = storage.create_session(db)
            storage.save_exchange(db, session, "Giờ làm?", answer)
            storage.initialize(db)
            with storage.connect(db) as connection:
                row = connection.execute("SELECT * FROM messages WHERE role='assistant'").fetchone()
                self.assertEqual(row["content"], text)
                self.assertEqual(row["answer_type"], "unknown")
                self.assertEqual(row["sources_json"], "[]")
            client.chat.side_effect = GeminiError("HTTP 429")
            with self.assertRaises(GeminiError):
                ask(db, client, "fake", "Giờ làm?")
