import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onboarding.cli import main
from onboarding.config import Config
from onboarding.storage import connect, initialize


class BasicsTest(unittest.TestCase):
    def test_init_preserves_data_and_enforces_foreign_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nested" / "test.sqlite3"
            initialize(database)
            with connect(database) as connection:
                connection.execute(
                    "INSERT INTO documents(document_id,title,content,source_title) VALUES(?,?,?,?)",
                    ("demo", "Giờ làm việc", "08:30", "Nguồn giả lập"),
                )
            initialize(database)
            with connect(database) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_config_environment_precedence_and_secret(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            env = Path(directory) / ".env"
            env.write_text('GEMINI_API_KEY="secret"\nGEMINI_CHAT_MODEL=file-model\n', encoding="utf-8")
            os.environ["GEMINI_CHAT_MODEL"] = "environment-model"
            config = Config.load(env)
            self.assertEqual(config.chat_model, "environment-model")
            self.assertIn("biến môi trường", config.chat_model_source)
            del os.environ["GEMINI_CHAT_MODEL"]
            file_config = Config.load(env)
            self.assertEqual(file_config.chat_model, "file-model")
            self.assertEqual(file_config.chat_model_source, str(env.resolve()))
            self.assertEqual(config.api_key, "secret")
            self.assertNotIn("secret", repr(config))
            with self.assertRaisesRegex(ValueError, "GEMINI_EMBEDDING_MODEL"):
                config.require_gemini()

    def test_cli_help_and_init_without_api_key(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as result:
                main(["--help"])
            self.assertEqual(result.exception.code, 0)
            self.assertIn("init", output.getvalue())
            with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
                database = Path(directory) / "cli.sqlite3"
                self.assertEqual(main(["--env-file", str(Path(directory) / "missing"), "--db", str(database), "init"]), 0)
                self.assertTrue(database.exists())


if __name__ == "__main__":
    unittest.main()
