# Bước 2: Kho tri thức

Đọc AGENTS.md và docs/PLAN.md. Triển khai importer JSON/CSV cho `data/demo_knowledge.json`, lưu documents/chunks/source metadata SQLite. Thêm `kb import`, `kb list`, `kb index`. Index chia chunks hợp lý, gọi OpenRouter embedding endpoint bằng `OPENROUTER_EMBEDDING_MODEL`, lưu vector và model ID/dimension. Có thể dùng fake client cho tests; smoke thật chỉ khi key/model có sẵn. Không làm admin UI, upload web, batch framework phức tạp. Kiểm tra init/import/index bằng một vài test luồng chính, cập nhật README/STATUS.
