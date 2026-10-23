# Chatbot onboarding tiếng Việt trên console

Ứng dụng Python và SQLite chạy cục bộ. Đã triển khai Bước 1–4: CLI, cấu hình, database, import JSON/CSV, index embeddings, hỏi đáp RAG và chat liên tục qua OpenRouter.

## Chạy trên Windows PowerShell

Yêu cầu Python 3.10+, chỉ dùng thư viện chuẩn. Chạy từ thư mục gốc:

```powershell
python -m onboarding --help
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m onboarding init
python -m onboarding kb import data/demo_knowledge.json
python -m onboarding kb list
python -m onboarding kb index
python -m onboarding ask "Giờ làm việc của công ty là mấy giờ?"
```

Có thể dùng `.\.venv\Scripts\python.exe` thay `python`. Cài tùy chọn bằng `python -m pip install -e .` để dùng lệnh `onboarding`.

Database mặc định `.local/onboarding.sqlite3`. `init` không xóa dữ liệu. Chọn file riêng bằng `python -m onboarding --db .local/demo.sqlite3 init`; tùy chọn chung đặt trước lệnh. `--env-file PATH` chọn file cấu hình khác. Các lệnh kho tri thức tự tạo database khi chưa có.

## Cấu hình

Biến môi trường ưu tiên hơn `.env`; `--db` ưu tiên hơn `ONBOARDING_DB_PATH`. `.env` hỗ trợ `KEY=VALUE`, dòng chú thích `#`, giá trị có cặp dấu nháy; chưa hỗ trợ nội suy, nhiều dòng hay chú thích cuối dòng.

| Biến | Ý nghĩa |
|---|---|
| `ONBOARDING_DB_PATH` | Mặc định `.local/onboarding.sqlite3` |
| `OPENROUTER_API_KEY` | Key riêng, cần cho index |
| `OPENROUTER_BASE_URL` | Mặc định `https://openrouter.ai/api/v1`, phải dùng HTTPS |
| `OPENROUTER_EMBEDDING_MODEL` | Model embeddings, cần cho index |
| `OPENROUTER_CHAT_MODEL` | Model generation riêng cho Bước 3; chưa cần khi index |

Không gửi key vào hội thoại hoặc commit `.env`. Import/list/init không cần key. API lỗi được báo rõ và không tự chuyển sang fake.

Đã đối chiếu tài liệu [embeddings](https://openrouter.ai/docs/api/api-reference/embeddings/submit-an-embedding-request), [catalog embeddings](https://openrouter.ai/docs/api/api-reference/embeddings/list-all-embeddings-models) và [chat completions](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion). Ví dụ model embeddings: [openai/text-embedding-3-small](https://openrouter.ai/openai/text-embedding-3-small); model chat: [openai/gpt-4o-mini](https://openrouter.ai/openai/gpt-4o-mini). Không dùng model chat thay cho embeddings.

## Kho tri thức

JSON nhận danh sách tài liệu hoặc object có trường `documents` như dữ liệu mẫu. CSV dùng hàng tiêu đề. Bốn trường bắt buộc là chuỗi không rỗng: `document_id`, `title`, `content`, `source_title`. Trường khác được giữ dưới dạng metadata; CSV lưu các giá trị metadata dạng chuỗi.

Import kiểm tra toàn bộ file trước khi ghi. Trùng ID trong cùng file là lỗi. Import lại ID đã có sẽ cập nhật tài liệu. Khi title/content thay đổi, chunks cũ và embeddings tương ứng được xóa để tránh dùng vector lỗi thời; import y nguyên giữ embeddings.

Chia đoạn theo heading/đoạn văn, giới hạn 1.000 ký tự; đoạn quá dài được cắt nhỏ. Index dùng title cùng nội dung đoạn, gửi tối đa 32 đoạn mỗi request, lưu vector JSON cùng model ID/dimension. `kb index` luôn tạo lại toàn bộ embeddings, phù hợp bộ demo nhỏ. Chạy lại sau khi đổi model; chỉ lưu khi mọi batch thành công và tài liệu chưa thay đổi. Nếu lỗi, index trước đó vẫn được giữ. `kb list` hiển thị số đoạn có vector, không xác nhận chúng trùng model hiện cấu hình.

## Chat liên tục

```powershell
python -m onboarding chat
python -m onboarding chat --debug
```

Nhập câu hỏi rồi Enter. `/help` xem hướng dẫn; `/exit`, Ctrl+C tại dấu nhắc hoặc EOF để thoát. Bỏ qua dòng trống; lỗi API được báo và cho phép nhập tiếp, không tự retry. Mỗi lần chạy tạo một session; cặp câu hỏi/câu trả lời thành công và nguồn được lưu cùng nhau trong SQLite, kể cả fallback. Câu hỏi lỗi và lệnh điều khiển không được lưu.

Mỗi câu hỏi retrieval độc lập; lịch sử hiện chỉ để lưu trữ, chưa gửi lại model và chưa hỗ trợ tiếp tục phiên cũ hoặc hiểu đại từ từ câu trước. Lệnh `ask` riêng lẻ không lưu lịch sử. Chưa có lệnh xem/xóa lịch sử; dữ liệu nằm trong bảng `sessions`, `messages` tại database đã cấu hình.

## Kiểm tra kết nối và tests

Thử riêng model chat, bỏ qua embeddings/retrieval và không mở database:

```powershell
python -m onboarding check-chat
```

Lệnh gửi một request tới `/chat/completions` với `OPENROUTER_CHAT_MODEL`, mong đợi `OK`. Nếu bị HTTP 429, lỗi hiển thị endpoint/model, `provider_name`, `limit_source` và số giây Retry-After khi có; không in raw response hoặc API key. [Tài liệu lỗi OpenRouter](https://openrouter.ai/docs/api-reference/errors-and-debugging) giải thích 429 có thể liên quan giới hạn upstream; cần đọc thông tin trả về để xác định nguyên nhân cụ thể.

`check-chat` cũng hiển thị nguồn model: biến môi trường hoặc đường dẫn `.env`. Nếu model khác file đã sửa, kiểm tra `$env:OPENROUTER_CHAT_MODEL` trong đúng terminal đang chạy. Biến môi trường ưu tiên hơn file; dùng `Remove-Item Env:OPENROUTER_CHAT_MODEL -ErrorAction SilentlyContinue` để bỏ override trong phiên PowerShell hiện tại rồi chạy lại. Lưu file `.env` trước khi chạy. Không in toàn bộ `.env` vì có API key.

Lệnh `ask` embed câu hỏi bằng đúng model đã index, tìm cosine top-k rồi gửi context tới model chat. Backend hiển thị danh sách nguồn context cùng ID tài liệu. Nếu kho rỗng hoặc không có đoạn đạt ngưỡng, trả “Chưa có thông tin…” và không gọi chat. Nếu model báo context không đủ, cũng trả fallback không kèm nguồn.

Với `nvidia/nemotron-3-embed-1b` (gồm `:free`), client gửi `input_type=passage` khi index và `input_type=query` khi hỏi, theo [tài liệu NVIDIA](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-embed-1b-infer). Các model khác giữ request mặc định hiện tại. Sau khi cập nhật từ bản chưa phân biệt chế độ, cần chạy `python -m onboarding kb index` một lần. SQLite tự thêm trường ghi chế độ embedding và vẫn giữ dữ liệu cũ; `ask` sẽ yêu cầu index lại với index Nemotron cũ.

Nếu câu trong kho bị fallback, dùng `--debug` để xem top điểm cosine và fallback ở retrieval hay generation:

```powershell
python -m onboarding kb index
python -m onboarding ask "Giờ làm việc của công ty là mấy giờ?" --debug
python -m onboarding ask "Thời tiết hôm nay thế nào?" --debug
```

Ngưỡng mặc định đã giảm từ 0.5 xuống 0.3 sau khi câu giờ làm việc thật tìm đúng nguồn với cosine 0.366482. Đây là điều chỉnh ban đầu từ một câu hỏi; cần kiểm chứng thêm câu ngoài kho bằng `--debug`. Thay đổi ngưỡng không cần index lại.

```powershell
python -m onboarding ask "Xin nghỉ phép thế nào?" --top-k 3 --min-score 0.3
python -m onboarding ask "Thời tiết hôm nay thế nào?"
```

`--min-score` mặc định 0.3 là ngưỡng thử nghiệm, không phải xác suất đúng. Phân bố cosine phụ thuộc model; cần thử câu trong/ngoài kho trên model thật để điều chỉnh. Prompt yêu cầu model chỉ dùng context nhưng chưa có bước kiểm chứng độc lập từng khẳng định. Danh sách “Nguồn context” thể hiện các đoạn đã gửi cho model, không phải xác nhận mọi nguồn đều được dùng trong câu trả lời. Thiếu vector, đổi model hoặc dimension không khớp sẽ báo chạy lại `kb index`, không tự tạo lại index hay chuyển sang fake.

```powershell
python -m unittest discover -s tests -v
```

Tests chạy offline với fake client/mock HTTP, không tốn API. Có kiểm tra SQLite, config, CLI, import JSON/CSV, cập nhật/index lại và lỗi API. Smoke thật chạy riêng bằng `kb index` sau khi cấu hình key/model; có thể phát sinh phí.

Dữ liệu mẫu là giả lập, không đại diện doanh nghiệp thật. Chưa có Telegram, website hoặc server. Xem tiến độ thực tế trong `docs/STATUS.md`.
