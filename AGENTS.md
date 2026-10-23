# Hướng dẫn Codex cho dự án

## Mục tiêu
Tạo chatbot hỏi đáp onboarding bằng tiếng Việt. Chạy trên console máy cá nhân. Dùng OpenRouter API cho embeddings và LLM generation. Chưa làm Telegram, website hoặc triển khai server.

## Phạm vi đơn giản
Dùng Python, argparse, SQLite và OpenRouter. Chỉ tạo các module cần thiết: CLI, knowledge base/importer, OpenRouter client, RAG service, storage/session. Không thêm FastAPI, PostgreSQL, vector database server, dashboard, Docker, agent framework, local model, retry framework phức tạp, nhiều provider, workflow CI hoặc benchmark phức tạp nếu người dùng chưa yêu cầu.

Dùng một vector search cosine đơn giản trên embeddings đọc từ SQLite (NumPy nếu cần). Dự án demo với số lượng tài liệu nhỏ, chưa cần tối ưu quy mô lớn. Chia tài liệu theo heading/đoạn và độ dài hợp lý; không cần thiết kế chunking cầu kỳ.

## OpenRouter
Dùng một API key `OPENROUTER_API_KEY` và OpenRouter base URL. Model embedding và model chat là hai cấu hình riêng: `OPENROUTER_EMBEDDING_MODEL`, `OPENROUTER_CHAT_MODEL`. Đọc tài liệu OpenRouter hiện tại để xác nhận request/response và model hỗ trợ embedding/chat trước khi code. Không giả định mọi model hỗ trợ cả hai tác vụ.
Không hard-code secret. Thiếu key/model thì giải thích cách cấu hình. Không tự chuyển sang fake khi API lỗi. Lưu embedding cùng model ID và dimension; nếu embedding model đổi thì index lại tài liệu. Không log key. Báo lỗi HTTP dễ hiểu.

## Code và dữ liệu
Giữ cấu trúc nhỏ và dễ đọc. CLI điều khiển, service xử lý RAG, storage chứa SQL, OpenRouter client gọi API. Dùng SQLite parameterized queries. `init` tạo DB tự động và chạy lặp không xóa dữ liệu. Import JSON/CSV có kiểm tra trường bắt buộc. Dữ liệu mẫu là giả lập. Câu trả lời chỉ dựa vào context lấy được, phải kèm nguồn. Nếu không tìm thấy nguồn phù hợp thì nói chưa có thông tin.

## Kiểm thử
Giữ kiểm thử đơn giản, tối thiểu:
- database khởi tạo được và import tài liệu;
- vector search chọn được đoạn mong đợi với vectors mẫu;
- RAG trả source hoặc fallback đúng;
- CLI chạy được help và một luồng hỏi đáp mẫu.
Dùng fake client cho test tự động để không tốn API. Chạy smoke test OpenRouter thật riêng với vài request khi có key. Không tạo nhiều test cases, benchmark hay metrics phức tạp; báo chính xác test nào pass và phần nào chưa chạy.

## Cách làm
Đọc prompt hiện tại và file liên quan. Thực hiện code đến mức chạy thử được, không chỉ đưa kế hoạch. Sửa README và `docs/STATUS.md`. Giữ code người dùng. Không tích hợp Telegram. Không commit hoặc deploy khi chưa được yêu cầu.

## Báo cáo
Trả lời tiếng Việt, nêu phần đã làm, cách chạy, test đã chạy và việc người dùng cần cấu hình (thường là API key/model). Phân biệt fake test với request OpenRouter thật.
