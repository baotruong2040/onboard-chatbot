"""Local web API; reuse the console RAG service without streaming."""

from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from . import storage
from .config import Config
from .gemini import GeminiClient, GeminiError
from .rag import ask

WEB = Path(__file__).with_name("web")


class Question(BaseModel):
    message: str = Field(min_length=1, max_length=4000, strict=True)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Câu hỏi không được rỗng.")
        return value


def create_app(config=None, client=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.config = config if config is not None else Config.load()
        await run_in_threadpool(storage.initialize, app.state.config.database)
        yield

    app = FastAPI(title="Trợ lý Onboarding", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo the request body or Pydantic input values.
        return JSONResponse(status_code=422, content={"detail": "Câu hỏi phải là chuỗi từ 1 đến 4000 ký tự, không chỉ chứa khoảng trắng."})

    @app.exception_handler(sqlite3.Error)
    @app.exception_handler(OSError)
    async def storage_error(request, error):
        return JSONResponse(status_code=503, content={"detail": "Không truy cập được dữ liệu. Hãy kiểm tra SQLite rồi thử lại."})

    def require_session(database, conversation_id):
        if not storage.session_exists(database, conversation_id):
            raise HTTPException(404, "Cuộc trò chuyện không tồn tại.")

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/conversations", status_code=201)
    def new_conversation(request: Request):
        return {"conversation_id": storage.create_session(request.app.state.config.database)}

    @app.get("/api/conversations/{conversation_id}/messages")
    def history(conversation_id: str, request: Request):
        database = request.app.state.config.database
        require_session(database, conversation_id)
        return {"conversation_id": conversation_id, "messages": storage.read_messages(database, conversation_id)}

    @app.post("/api/conversations/{conversation_id}/messages")
    def send(conversation_id: str, body: Question, request: Request):
        settings = request.app.state.config
        require_session(settings.database, conversation_id)
        try:
            # Sync route runs in FastAPI's worker pool; no DB transaction spans HTTP.
            provider = client if client is not None else GeminiClient(settings)
            answer = ask(settings.database, provider, settings.embedding_model, body.message)
        except GeminiError:
            raise HTTPException(502, "Gemini chưa trả lời được. Kiểm tra kết nối, quota và cấu hình key/model ở backend rồi thử lại.") from None
        except ValueError:
            raise HTTPException(503, "Chưa thể xử lý câu hỏi. Kiểm tra cấu hình Gemini và index (kb list/kb index nếu thiếu vector hoặc đổi model).") from None
        message_id = storage.save_exchange(settings.database, conversation_id, body.message, answer)
        return {"conversation_id": conversation_id, "message_id": message_id, "answer": answer.text}

    return app


app = create_app()
