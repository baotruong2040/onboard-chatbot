"""Khởi tạo SQLite; các câu SQL được giữ trong module storage."""

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


@contextmanager
def connect(database: Path):
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(database: Path):
    database.parent.mkdir(parents=True, exist_ok=True)
    with connect(database) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_title TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding_json TEXT,
                embedding_model TEXT,
                embedding_dimension INTEGER,
                UNIQUE(document_id, position)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(chunks)")}
        if "embedding_input_type" not in columns:
            connection.execute("ALTER TABLE chunks ADD COLUMN embedding_input_type TEXT")
        message_columns = {row["name"] for row in connection.execute("PRAGMA table_info(messages)")}
        if "answer_type" not in message_columns:
            connection.execute("ALTER TABLE messages ADD COLUMN answer_type TEXT NOT NULL DEFAULT 'unknown'")
        if "assumptions_json" not in message_columns:
            connection.execute("ALTER TABLE messages ADD COLUMN assumptions_json TEXT NOT NULL DEFAULT '[]'")


def save_documents(database, documents, splitter):
    with connect(database) as connection:
        for document in documents:
            values = tuple(document[key] for key in ("document_id", "title", "content", "source_title"))
            previous = connection.execute(
                "SELECT title,content FROM documents WHERE document_id=?", (values[0],)
            ).fetchone()
            metadata = json.dumps({k: v for k, v in document.items()
                                   if k not in ("document_id", "title", "content", "source_title")}, ensure_ascii=False)
            connection.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET "
                "title=excluded.title,content=excluded.content,source_title=excluded.source_title,"
                "metadata_json=excluded.metadata_json", (*values, metadata)
            )
            if previous is None or tuple(previous) != (values[1], values[2]):
                connection.execute("DELETE FROM chunks WHERE document_id=?", (values[0],))
                connection.executemany(
                    "INSERT INTO chunks(document_id,position,content) VALUES(?,?,?)",
                    [(values[0], position, text) for position, text in enumerate(splitter(values[2]))]
                )


def list_documents(database):
    with connect(database) as connection:
        return connection.execute(
            "SELECT d.document_id,d.title,d.source_title,COUNT(c.id) AS chunks,"
            "COUNT(c.embedding_json) AS indexed FROM documents d LEFT JOIN chunks c "
            "ON c.document_id=d.document_id GROUP BY d.document_id ORDER BY d.document_id"
        ).fetchall()


def read_chunks(database):
    with connect(database) as connection:
        return connection.execute(
            "SELECT c.*,d.title,d.source_title FROM chunks c JOIN documents d ON d.document_id=c.document_id ORDER BY c.id"
        ).fetchall()


def save_embeddings(database, pending, model, dimension, snapshot):
    with connect(database) as connection:
        current = connection.execute(
            "SELECT c.id,c.content,d.title FROM chunks c JOIN documents d ON d.document_id=c.document_id ORDER BY c.id"
        ).fetchall()
        if [tuple(row) for row in current] != [(r["id"], r["content"], r["title"]) for r in snapshot]:
            raise ValueError("Tài liệu đã thay đổi khi index; chạy kb index lại.")
        connection.executemany(
            "UPDATE chunks SET embedding_json=?,embedding_model=?,embedding_dimension=?,embedding_input_type=? WHERE id=?",
            [(json.dumps(vector), model, dimension, "search_document", chunk_id) for chunk_id, _, vector in pending]
        )


def create_session(database):
    session_id = uuid4().hex
    with connect(database) as connection:
        connection.execute("INSERT INTO sessions(id) VALUES(?)", (session_id,))
    return session_id


def save_exchange(database, session_id, question, answer):
    with connect(database) as connection:
        connection.executemany(
            "INSERT INTO messages(session_id,role,content,sources_json,answer_type,assumptions_json) VALUES(?,?,?,?,?,?)",
            [(session_id, "user", question, "[]", "unknown", "[]"),
             (session_id, "assistant", answer.text, json.dumps(answer.sources, ensure_ascii=False),
              answer.answer_type, json.dumps(answer.assumptions, ensure_ascii=False))],
        )
        return connection.execute("SELECT last_insert_rowid()").fetchone()[0]


def session_exists(database, session_id):
    with connect(database) as connection:
        return connection.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone() is not None


def read_messages(database, session_id):
    with connect(database) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id,role,content,created_at FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        )]
