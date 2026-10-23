# Hướng dẫn Codex cho dự án

## Mục tiêu và phạm vi
Chatbot onboarding tiếng Việt trên console và web local 127.0.0.1. Dùng Python, argparse, SQLite, Gemini API trực tiếp, FastAPI + Uvicorn và HTML/CSS/JavaScript thuần. Không thêm React, đăng nhập, Telegram, Docker, PostgreSQL, vector server, dashboard, agent framework, local model, nhiều provider, CI hoặc triển khai public khi chưa được yêu cầu.

## Gemini
Dùng GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_EMBEDDING_MODEL và GEMINI_CHAT_MODEL. Embedding/chat là hai cấu hình riêng. Đọc tài liệu Gemini hiện tại trước khi thay hợp đồng API; không giả định mọi model hỗ trợ cả hai tác vụ. Không hard-code/log secrets hoặc gửi key ra frontend. Thiếu cấu hình phải giải thích cách xử lý. Không đổi model, fallback fake/provider hoặc index lại tự động. Lưu model và dimension cùng vector; đổi embedding model cần người dùng index lại. Báo lỗi HTTP dễ hiểu, không in raw provider response.

## Kiến trúc và dữ liệu
CLI/API dùng chung RAG service, GeminiClient và storage. Không gọi CLI qua subprocess hoặc chép logic RAG vào route. Gemini HTTP đồng bộ dùng route đồng bộ/threadpool. Console giữ streaming; web hiện nhận response hoàn chỉnh. SQLite parameterized queries, connection riêng từng thao tác, không giữ transaction khi chờ Gemini. Lưu cặp hỏi/đáp thành công cùng transaction; lỗi không lưu partial. Init chạy lặp không xóa dữ liệu; migration chỉ khi cần và giữ lịch sử. Import JSON/CSV kiểm tra trường bắt buộc. Chunking đơn giản, cosine search trên vectors SQLite, giữ top-k/ngưỡng hiện có. Dữ liệu mẫu là giả lập.

Trả answer.text tự nhiên nguyên vẹn, không ép JSON hoặc thêm nhãn/nguồn ở backend. Model tự nêu nguồn, cách suy luận và giả định. Cho phép ước đoán lịch trình/gợi ý onboarding có nhãn chưa xác nhận; không bịa lương, quyền lợi, nghỉ phép, mật khẩu, thông tin cá nhân hoặc quy định chính thức. Lỗi kỹ thuật phải báo lỗi, không chuyển sang đoán. Metadata unknown không được coi là grounded. Không nhập dự đoán vào kho hoặc tạo vector cho dự đoán. Chưa có bộ nhớ hội thoại; lịch sử chỉ lưu/hiển thị.

## Web local
Phục vụ frontend cùng origin, không CORS rộng. Render textContent và white-space: pre-wrap, không thực thi HTML từ người dùng/model. Không gọi AI hoặc index lúc khởi động. localStorage chỉ lưu conversation_id, không key. Không dùng một connection SQLite toàn cục giữa các thread.

## Kiểm thử và cách làm
Đọc prompt, README, docs/STATUS.md và mã liên quan trước khi sửa. Chạy tests trước/sau. Giữ tests đơn giản với fake/mock: DB/import, cosine/RAG, CLI/streaming, tạo phiên/lịch sử/API validation/provider lỗi. Smoke Gemini thật riêng khi có key và mạng; phân biệt rõ fake tests với API thật. Không tạo benchmark/retry framework phức tạp. Giữ code người dùng, cập nhật README và docs/STATUS.md, triển khai đến mức chạy thử được. Không commit hoặc deploy khi chưa được yêu cầu.

## Báo cáo
Trả lời tiếng Việt: phần đã làm, lệnh cài/chạy, tests thực sự chạy và phần chưa xác minh với Gemini thật. Nêu rõ phụ thuộc/cấu hình còn thiếu, không in secrets.
