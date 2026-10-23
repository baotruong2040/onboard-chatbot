"""Import, chia đoạn và index kho tri thức nhỏ."""

import csv
import json
import re
from pathlib import Path

from . import storage
from .gemini import validate_vectors

REQUIRED = ("document_id", "title", "content", "source_title")


def split_chunks(content, limit=1000):
    chunks = []
    current = ""
    for paragraph in re.split(r"\n\s*\n|\n(?=#{1,6} )", content.strip()):
        for start in range(0, len(paragraph), limit):
            piece = paragraph[start:start + limit].strip()
            if not piece:
                continue
            if current and len(current) + len(piece) + 2 > limit:
                chunks.append(current)
                current = ""
            current = (current + "\n\n" + piece).strip()
    if current:
        chunks.append(current)
    return chunks


def import_documents(database, path):
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as file:
        if path.suffix.lower() == ".json":
            payload = json.load(file)
            rows = payload.get("documents") if isinstance(payload, dict) else payload
        elif path.suffix.lower() == ".csv":
            rows = list(csv.DictReader(file))
        else:
            raise ValueError("Chỉ hỗ trợ tài liệu JSON hoặc CSV.")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Cần danh sách documents không rỗng.")
    seen = set()
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict) or any(
            not isinstance(row.get(key), str) or not row[key].strip() for key in REQUIRED
        ):
            raise ValueError(f"Tài liệu {number}: cần document_id, title, content, source_title dạng chuỗi không rỗng.")
        row["document_id"] = row["document_id"].strip()
        if row["document_id"] in seen:
            raise ValueError(f"Tài liệu {number}: document_id bị trùng.")
        seen.add(row["document_id"])
    storage.save_documents(database, rows, split_chunks)
    return len(rows)


def index_documents(database, client, model):
    chunks = storage.read_chunks(database)
    if not chunks:
        return 0
    pending = []
    dimension = None
    for start in range(0, len(chunks), 32):
        batch = chunks[start:start + 32]
        vectors = client.embed([row["title"] + "\n" + row["content"] for row in batch],
                               input_type="search_document")
        size = validate_vectors(vectors, len(batch))
        if dimension is not None and dimension != size:
            raise ValueError("Dimension thay đổi giữa các batch; chưa lưu index.")
        dimension = size
        pending.extend((row["id"], row["content"], vector) for row, vector in zip(batch, vectors))
    storage.save_embeddings(database, pending, model, dimension, chunks)
    return len(pending)
