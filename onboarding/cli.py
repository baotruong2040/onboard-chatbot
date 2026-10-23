"""Điểm vào argparse của ứng dụng."""

import argparse
import sqlite3
import sys
from pathlib import Path

from .config import Config
from .storage import initialize
from . import storage
from .knowledge import import_documents, index_documents
from .gemini import GeminiClient
from .rag import DEFAULT_MIN_SCORE, ask


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chatbot onboarding tiếng Việt trên console")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="File cấu hình .env")
    parser.add_argument("--db", type=Path, help="Đường dẫn SQLite, ưu tiên hơn cấu hình")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Tạo database, giữ nguyên dữ liệu đã có")
    commands.add_parser("check-chat", help="Thử một request chat trực tiếp, không gọi embeddings")
    question = commands.add_parser("ask", help="Hỏi đáp có nguồn từ kho tri thức")
    question.add_argument("question")
    question.add_argument("--top-k", type=int, default=3)
    question.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    question.add_argument("--debug", action="store_true", help="Hiện điểm retrieval và trạng thái thiếu nguồn")
    chat = commands.add_parser("chat", help="Chat liên tục và lưu lịch sử SQLite")
    chat.add_argument("--top-k", type=int, default=3)
    chat.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    chat.add_argument("--debug", action="store_true")
    kb = commands.add_parser("kb", help="Quản lý kho tri thức")
    actions = kb.add_subparsers(dest="action", required=True)
    importer = actions.add_parser("import", help="Import JSON/CSV")
    importer.add_argument("path", type=Path)
    actions.add_parser("list", help="Liệt kê tài liệu và trạng thái index")
    actions.add_parser("index", help="Tạo lại toàn bộ embeddings qua Gemini")
    args = parser.parse_args(argv)
    try:
        config = Config.load(args.env_file)
        if args.command == "check-chat":
            config.require_gemini(embedding=False)
            print(f"Nguồn model chat: {config.chat_model_source}")
            print(f"Đang gọi Gemini generateContent | model={config.chat_model}")
            print(GeminiClient(config).chat([
                {"role": "user", "content": "Chỉ trả lời đúng một từ: OK"}
            ]))
            return 0
        database = args.db if args.db is not None else config.database
        initialize(database)
        if args.command == "init":
            print(f"Đã khởi tạo SQLite: {database.resolve()}")
        elif args.command == "ask":
            config.require_gemini()
            stream_answer(database, GeminiClient(config), config.embedding_model, args.question, args)
        elif args.command == "chat":
            config.require_gemini()
            return chat_loop(database, GeminiClient(config), config.embedding_model, args)
        elif args.action == "import":
            print(f"Đã import {import_documents(database, args.path)} tài liệu.")
        elif args.action == "list":
            for row in storage.list_documents(database):
                print(f"{row['document_id']} | {row['title']} | {row['indexed']}/{row['chunks']} đoạn có vector | {row['source_title']}")
        elif args.action == "index":
            client = GeminiClient(config)
            count = index_documents(database, client, config.embedding_model)
            print(f"Đã index {count} đoạn bằng model {config.embedding_model}.")
        return 0
    except KeyboardInterrupt:
        print("\nĐã hủy phản hồi.", file=sys.stderr)
        return 130
    except ValueError as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print("Lỗi: không thể đọc/ghi dữ liệu. Kiểm tra đường dẫn và quyền ghi SQLite.", file=sys.stderr)
        return 1


def stream_answer(database, client, model, question, args):
    emitted = False

    def output(text):
        nonlocal emitted
        emitted = True
        print(text, end="", flush=True)

    try:
        return ask(database, client, model, question, top_k=args.top_k,
                   min_score=args.min_score, on_text=output,
                   debug=(lambda message: print(message, file=sys.stderr)) if args.debug else None)
    except ValueError as error:
        if emitted:
            raise ValueError(f"{error} Phần đã hiển thị chưa hoàn tất; chưa lưu lượt hỏi đáp.") from None
        raise
    finally:
        if emitted:
            print(flush=True)


def chat_loop(database, client, model, args):
    session_id = storage.create_session(database)
    print(f"Phiên chat: {session_id}\n/help: hướng dẫn | /exit: thoát")
    print("Mỗi câu hỏi được tìm nguồn độc lập; hãy nêu rõ chủ đề.")
    while True:
        try:
            question = input("Bạn> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nĐã kết thúc phiên chat.")
            return 0
        if not question:
            continue
        if question == "/exit":
            print("Đã kết thúc phiên chat.")
            return 0
        if question == "/help":
            print("Nhập câu hỏi onboarding có chủ đề rõ ràng. /exit để thoát.")
            print("Lịch sử lưu trong SQLite; chưa dùng lịch sử để hiểu câu hỏi nối tiếp.")
            continue
        if question.startswith("/"):
            print("Lệnh chưa hỗ trợ. Nhập /help để xem hướng dẫn.")
            continue
        try:
            answer = stream_answer(database, client, model, question, args)
        except KeyboardInterrupt:
            print("\nĐã hủy phản hồi; chưa lưu lượt hỏi đáp.")
            continue
        except ValueError as error:
            print(f"Lỗi: {error}", file=sys.stderr)
            continue
        storage.save_exchange(database, session_id, question, answer)
