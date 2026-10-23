# Kế hoạch xây dựng

## Module
| Module | Nhiệm vụ |
|---|---|
| CLI | Lệnh init, kb import, kb index, ask, chat |
| Knowledge Base | Nạp JSON/CSV, chuẩn hóa đơn giản, chia chunks |
| OpenRouter client | Embeddings và chat completion qua OpenRouter |
| RAG service | Tìm top-k, tạo context, gọi LLM, gắn nguồn/fallback |
| SQLite storage | Lưu tài liệu/chunks/vectors/session/messages |

## Các bước triển khai

### Bước 1: Ứng dụng và SQLite
Tạo cấu trúc Python, `--help`, config `.env`, lệnh `init`, SQLite và README. Kiểm tra init tạo database, chạy lặp vẫn giữ dữ liệu.

### Bước 2: Kho tri thức
Tạo importer JSON/CSV, lưu tài liệu/chunks/metadata. Tạo `kb import`, `kb list`, `kb index`. Index gọi OpenRouter embedding API theo lô nhỏ và lưu vectors trong SQLite. Nếu tài liệu thay đổi hoặc model embedding đổi, tạo lại embeddings tương ứng.

### Bước 3: Hỏi đáp RAG
Tạo `ask`: embedding câu hỏi qua cùng OpenRouter embedding model, cosine search top-k, gửi câu hỏi cùng các đoạn tìm được tới OpenRouter chat completion API. Hiển thị câu trả lời và nguồn. Nếu không có đoạn phù hợp thì fallback, không gọi LLM đoán.

### Bước 4: Chat console và hoàn thiện
Tạo vòng chat đơn giản, lệnh `/help`, `/exit`, lưu lịch sử SQLite. Chạy một luồng demo từ import đến hỏi đáp. Ghi cách cấu hình API key và model IDs trong README.

Telegram có thể bổ sung sau bằng một module giao tiếp mới dùng lại RAG service, không cần viết lại logic hỏi đáp.

## Định nghĩa hoàn thành
- Chạy được `init`, import tài liệu, tạo embeddings qua OpenRouter, hỏi bằng console và nhận câu trả lời có nguồn.
- Câu ngoài phạm vi trả lời rõ không tìm thấy dữ liệu.
- Có một số kiểm tra cơ bản và một smoke test API thật nếu key/model khả dụng.
- README hướng dẫn chạy trên máy cá nhân.
