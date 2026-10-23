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
    base_url: str = "https://openrouter.ai/api/v1"
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
            api_key=get("OPENROUTER_API_KEY"),
            embedding_model=get("OPENROUTER_EMBEDDING_MODEL"),
            chat_model=get("OPENROUTER_CHAT_MODEL"),
            base_url=get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
            chat_model_source=(
                "biến môi trường OPENROUTER_CHAT_MODEL"
                if "OPENROUTER_CHAT_MODEL" in os.environ
                else str(env_file.resolve())
            ),
        )

    def require_openrouter(self, *, chat=True):
        missing = [
            name
            for name, value in (
                ("OPENROUTER_API_KEY", self.api_key),
                ("OPENROUTER_EMBEDDING_MODEL", self.embedding_model),
                ("OPENROUTER_CHAT_MODEL", self.chat_model),
            )
            if (chat or name != "OPENROUTER_CHAT_MODEL") and not value.strip()
        ]
        if missing:
            raise ValueError("Cần cấu hình trong .env hoặc môi trường: " + ", ".join(missing))
