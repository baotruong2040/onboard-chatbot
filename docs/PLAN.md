# Kế hoạch xây dựng

## Module
| Module | Nhiệm vụ |
|---|---|
| CLI | Lệnh init, kb import, kb index, ask, chat |
| Knowledge Base | Nạp JSON/CSV, chuẩn hóa đơn giản, chia chunks |
| Gemini client | Embeddings và generateContent qua Gemini REST |
| RAG service | Tìm top-k, tạo context, gọi LLM trả văn bản tự nhiên |
| SQLite storage | Lưu tài liệu/chunks/vectors/session/messages |

## Các bước triển khai

### Bước 1: Ứng dụng và SQLite
Tạo cấu trúc Python, `--help`, config `.env`, lệnh `init`, SQLite và README. Kiểm tra init tạo database, chạy lặp vẫn giữ dữ liệu.

### Bước 2: Kho tri thức
Tạo importer JSON/CSV, lưu tài liệu/chunks/metadata. Tạo `kb import`, `kb list`, `kb index`. Index gọi Gemini batchEmbedContents theo lô nhỏ, dùng RETRIEVAL_DOCUMENT/RETRIEVAL_QUERY cho gemini-embedding-001 và lưu vectors/model/dimension trong SQLite. Chuyển từ OpenRouter cần index lại, không trộn hai không gian vector.

### Bước 3: Hỏi đáp RAG
Tạo `ask`: embedding câu hỏi qua cùng model, cosine search top-k, ngưỡng code hiện tại 0.3; đây chưa phải ngưỡng đã hiệu chỉnh cho Gemini. Khi thiếu tri thức, generation nhận context rỗng để ước đoán có điều kiện hoặc hỏi thêm; lỗi kỹ thuật tiếp tục báo lỗi.

### Bước 4: Chat console và hoàn thiện
Tạo vòng chat đơn giản, lệnh `/help`, `/exit`, lưu lịch sử SQLite. Chạy một luồng demo từ import đến hỏi đáp. Ghi cách cấu hình API key và model IDs trong README.

Ask/chat dùng streaming SSE qua callback CLI, in từng đoạn và gom text để lưu khi STOP thành công. Lỗi/hủy không ghi phản hồi dở dang, không tự retry; check-chat tiếp tục non-stream.

Telegram có thể bổ sung sau bằng một module giao tiếp mới dùng lại RAG service, không cần viết lại logic hỏi đáp.

## Định nghĩa hoàn thành
- Chạy được `init`, import tài liệu, tạo embeddings qua Gemini, hỏi bằng console và nhận câu trả lời có nguồn.
- Generation trả văn bản tự nhiên đầy đủ; console in nguyên văn, không yêu cầu JSON hoặc định dạng lại. Prompt yêu cầu model tự phân biệt nguồn/suy luận/ước đoán; backend không kiểm tra trích dẫn.
- Ước đoán chỉ cho lịch thông thường/gợi ý onboarding, không bịa chính sách nhạy cảm. Nhãn không bảo đảm đó là chính sách thực tế; kiểm tra ngữ nghĩa vẫn là hạn chế.
- Lưu nguyên văn câu trả lời; metadata mới unknown/[] vì không phân loại tự động. Giữ metadata lịch sử cũ. Không ghi ước đoán vào kho hoặc dùng lịch sử làm context.
- Có một số kiểm tra cơ bản và một smoke test API thật nếu key/model khả dụng.
- README hướng dẫn chạy trên máy cá nhân.
