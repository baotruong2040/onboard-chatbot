"""Cấu hình từ môi trường và file .env, không ghi log secrets."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    database: Path
    api_key: str = field(default="", repr=False)
    embedding_model: str = ""
    chat_model: str = ""
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    chat_model_source: str = "cấu hình trực tiếp"

    @classmethod
    def load(cls, env_file: Path = Path(".env")):
        values = {}
        if env_file.exists():
            for number, raw in enumerate(
                env_file.read_text(encoding="utf-8-sig").splitlines(), 1
            ):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                key, separator, value = line.partition("=")
                if not separator or not key.strip():
                    raise ValueError(f"Dòng {number} trong .env phải có dạng KEY=VALUE.")
                value = value.strip()
                if value.startswith(("'", '"')):
                    if len(value) < 2 or value[-1] != value[0]:
                        raise ValueError(f"Dòng {number} trong .env thiếu dấu đóng nháy.")
                    value = value[1:-1]
                values[key.strip()] = value

        def get(name, default=""):
            return os.environ.get(name, values.get(name, default))

        return cls(
            database=Path(get("ONBOARDING_DB_PATH", ".local/onboarding.sqlite3")),
            api_key=get("GEMINI_API_KEY"),
            embedding_model=get("GEMINI_EMBEDDING_MODEL"),
            chat_model=get("GEMINI_CHAT_MODEL"),
            base_url=get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/"),
            chat_model_source=(
                "biến môi trường GEMINI_CHAT_MODEL"
                if "GEMINI_CHAT_MODEL" in os.environ
                else str(env_file.resolve())
            ),
        )

    def require_gemini(self, *, chat=True, embedding=True):
        missing = [
            name
            for name, value in (
                ("GEMINI_API_KEY", self.api_key),
                ("GEMINI_EMBEDDING_MODEL", self.embedding_model),
                ("GEMINI_CHAT_MODEL", self.chat_model),
            )
            if (chat or name != "GEMINI_CHAT_MODEL") and (embedding or name != "GEMINI_EMBEDDING_MODEL") and not value.strip()
        ]
        if missing:
            raise ValueError("Cần cấu hình trong .env hoặc môi trường: " + ", ".join(missing))
