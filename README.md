# Chatbot onboarding tiếng Việt trên console

Python 3.10+, argparse, SQLite và **Gemini API trực tiếp** cho embeddings + generation. Chỉ dùng thư viện chuẩn; không cần SDK. CLI, kho tri thức, chat và lịch sử giữ nguyên; OpenRouter không còn được runtime sử dụng.

## Cấu hình Gemini

Lấy key từ [Google AI Studio](https://aistudio.google.com/apikey). Thêm các dòng sau vào `.env` hiện có, tự điền key trên máy:

```dotenv
GEMINI_API_KEY=YOUR_GEMINI_KEY
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_CHAT_MODEL=gemini-3.8-flash
ONBOARDING_DB_PATH=.local/onboarding.sqlite3
```

Model trên là ví dụ; chọn model tài khoản được phép dùng. Không dùng ID OpenRouter như `recursive/flint-v1.0:free`. Chat và embedding là hai model riêng. Các biến `OPENROUTER_*` cũ được bỏ qua, không tự dùng lại key cũ. Không gửi key vào hội thoại hoặc commit `.env`.

Biến môi trường ưu tiên hơn file; `--db` ưu tiên hơn ONBOARDING_DB_PATH. `--env-file PATH` chọn file khác. `.env` nhận KEY=VALUE, dòng chú thích # và cặp nháy; không hỗ trợ nội suy/nhiều dòng/chú thích cuối dòng. `check-chat` hiển thị nguồn model để kiểm tra override. Init/import/list không cần key. Index chỉ cần key/embedding model; check-chat chỉ cần key/chat model; ask/chat cần cả hai.

## Chuyển kho hiện tại và chạy

Chạy từ thư mục dự án trong PowerShell; có thể dùng `.\.venv\Scripts\python.exe` thay `python`:

```powershell
python -m onboarding check-chat
python -m onboarding kb index
python -m onboarding ask "Giờ làm việc của công ty là mấy giờ?" --debug --min-score 0.3
python -m onboarding chat --debug --min-score 0.3
```

**Bắt buộc index lại khi chuyển từ OpenRouter**. Vectors Nemotron không dùng chung với vectors Gemini. Không cần import lại tài liệu đã có; lịch sử được giữ. Mỗi database smoke riêng cũng cần index lại nếu muốn sử dụng tiếp.

Với kho mới:

```powershell
python -m onboarding init
python -m onboarding kb import data/demo_knowledge.json
python -m onboarding kb list
python -m onboarding kb index
```

`init` chạy lặp không xóa dữ liệu. Tùy chọn chung đứng trước subcommand: `python -m onboarding --db .local/demo.sqlite3 init`. Cài tùy chọn `python -m pip install -e .` để dùng lệnh `onboarding`.

JSON nhận danh sách hoặc object có documents; CSV có header. Bắt buộc document_id/title/content/source_title là chuỗi không rỗng. Import kiểm tra toàn bộ trước khi ghi; trùng ID trong file bị từ chối, ID đã có được cập nhật. Title/content đổi làm mất hiệu lực embeddings liên quan; nội dung giữ nguyên thì giữ vector. Metadata khác được lưu.

Chunk theo đoạn, tối đa 1000 ký tự. Index theo batch 32, lưu vector JSON/model/dimension/task vào SQLite. Chỉ ghi sau khi mọi batch thành công và tài liệu chưa đổi. API lỗi không ghi index dở dang. `kb list` đếm vector, không xác nhận chúng thuộc model hiện cấu hình.

## Retrieval và câu trả lời

Giữ cosine search/top-k hiện có. **DEFAULT_MIN_SCORE hiện là 0.3** theo code ở lần kiểm tra cuối. Chưa hiệu chỉnh cho Gemini; không coi điểm Nemotron cũ là bằng chứng cho model mới. Dùng --debug kiểm tra các câu trong/ngoài kho, chỉ đoạn đạt ngưỡng mới được gửi. Thay ngưỡng không cần index lại.

| Loại | Hiển thị |
|---|---|
| grounded | Theo tài liệu — thông tin trực tiếp và nguồn [n] |
| inferred | Suy luận từ tài liệu — cách suy luận/phép tính, giả định và nguồn |
| estimate | Ước đoán — chưa xác nhận; có giả định, không nguồn |
| clarification | Câu hỏi làm rõ ngắn khi thiếu dữ kiện |

Thiếu tri thức (kho rỗng/không nguồn đạt ngưỡng) vẫn gọi generation với context rỗng. Lỗi API, index thiếu vector/sai model/dimension vẫn báo lỗi, không âm thầm chuyển sang đoán. Chỉ ước đoán lịch thông thường hoặc gợi ý onboarding; không tự đặt mức lương, quyền lợi, điều kiện nghỉ phép, thông tin cá nhân, mật khẩu hoặc chính sách chính thức. Hướng dẫn chung có nguồn vẫn được phép.

Generation trả văn bản tự nhiên, không yêu cầu JSON. `ask` và `chat` in đầy đủ text từ Gemini, giữ xuống dòng/Markdown/khoảng trắng; console chỉ thêm ký tự xuống dòng khi in. Không thêm nhãn, giả định hoặc danh sách nguồn bằng backend. Model được yêu cầu tự nêu nguồn, suy luận, giả định và nhãn ước đoán trong nội dung. Bảng trên là hướng dẫn nội dung cho model, không phải khuôn hiển thị cố định. Không còn parse/validate JSON hoặc kiểm tra trích dẫn ở backend; chưa kiểm chứng ngữ nghĩa/phép tính. Không tự retry.

Ví dụ minh họa, không phải kết quả API thật:

- Kho ghi 08:30–17:30 → “Theo tài liệu: Giờ tan làm là 17:30. [1]”
- Kho ghi 08:00 + 8 giờ làm + 1 giờ nghỉ → “Suy luận từ tài liệu: giờ kết thúc là 17:00. [1]”
- Không có lịch → “Ước đoán — chưa xác nhận: có thể 17:00”, giả định lịch 08:00–17:00, không nguồn.

## Chat và lịch sử

`ask` và `chat` mặc định stream text qua Gemini `streamGenerateContent?alt=sse`: mỗi đoạn được in ngay với flush, không cần thêm cờ. Embedding/retrieval vẫn hoàn tất trước khi bắt đầu generation. `check-chat` vẫn dùng một response thông thường.

Nếu mạng ngắt, JSON SSE lỗi, hết token hoặc bị chặn, phần đã in có thể còn trên màn hình nhưng được báo chưa hoàn tất và không lưu lượt đó. Chỉ lưu sau khi nhận STOP và text không rỗng; không tự retry. Ctrl+C trong lúc chat đang stream hủy lượt và quay lại dấu nhắc; Ctrl+C với ask thoát mã 130. Response HTTP được đóng khi xong/lỗi/hủy. Giữ nguyên text, bỏ thought; không có bộ nhớ hội thoại.

`/help` xem hướng dẫn, `/exit`, EOF hoặc Ctrl+C tại dấu nhắc để thoát. Dòng trống được bỏ qua; lỗi API cho nhập tiếp. Mỗi lần chạy tạo session UUID. Cặp hỏi/đáp lưu cùng transaction, text giữ nguyên; câu lỗi API/lệnh điều khiển không lưu. Câu mới lưu answer_type=unknown, assumptions=[] và sources=[] vì không còn metadata JSON được xác minh; nguồn/giả định do model viết nằm trong text. Không coi context retrieval là nguồn đã được trích dẫn. Lịch sử và metadata cũ giữ nguyên.

Không có bộ nhớ hội thoại, resume phiên hoặc lệnh xem/xóa lịch sử. Mỗi câu hỏi độc lập; câu phụ thuộc lượt trước cần hỏi lại. Dự đoán không nhập vào kho, không tạo vector và không dùng làm dữ kiện ở lượt sau. `ask` riêng lẻ không lưu lịch sử.

## API và kiểm tra

Client dùng header x-goog-api-key; embeddings qua [batchEmbedContents](https://ai.google.dev/api/embeddings), task RETRIEVAL_DOCUMENT/RETRIEVAL_QUERY cho gemini-embedding-001. Không giả định gemini-embedding-2 có cùng cách thiết lập task. Generation dùng generateContent với systemInstruction/contents, đọc candidates và bỏ thought. Giới hạn maxOutputTokens=4096; MAX_TOKENS/content rỗng/safety block báo lỗi và không dùng phản hồi bị cắt. Xem [tài liệu Gemini](https://ai.google.dev/gemini-api/docs) và [embeddings](https://ai.google.dev/gemini-api/docs/embeddings).

HTTP 400/401/403/404/429 được giải thích ngắn, không log raw body/key. Lỗi quota cần kiểm tra tài khoản Google; không còn provider shared pool của OpenRouter.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q onboarding
```

Tests dùng fake/mock, không tốn API và không chứng minh model thật suy luận đúng. Smoke thật riêng bằng check-chat, kb index, ask/chat sau khi cấu hình key Gemini; có thể phát sinh phí. Dữ liệu mẫu là giả lập. Xem docs/STATUS.md để phân biệt kết quả offline và API thật. Không có Telegram, website, server hoặc nhiều provider.
