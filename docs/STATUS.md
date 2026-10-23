# Trạng thái hiện tại

Cập nhật ngày 2026-10-22.

## Hoàn thành console và xác nhận live RAG

Người dùng đã xác nhận trên máy cá nhân với OpenRouter thật:

- `check-chat` dùng recursive/flint-v1.0:free trả OK.
- Câu giờ làm việc chọn DEMO-ADM-001, cosine 0.366482 với ngưỡng 0.3; generation trả đúng 08:30–17:30 thứ Hai–thứ Sáu, nghỉ trưa 12:00–13:00, kèm nguồn.
- Câu “ngày mai trời có nắng không” cao nhất 0.094675; chọn 0 đoạn, fallback tại retrieval, không gọi chat.

Đã triển khai `chat` dùng lại ask, /help, /exit, bỏ dòng trống, xử lý EOF/Ctrl+C tại dấu nhắc và cho nhập tiếp sau lỗi API. Lưu session UUID và cặp user/assistant + sources trong SQLite bằng transaction. Lịch sử chỉ lưu, chưa dùng làm context hội thoại. Không triển khai Telegram/server.

Kiểm tra mới nhất: `python -m unittest discover -s tests -q` 12/12 pass (fake/mock offline); `python -m onboarding chat --help` pass. Chat tests xác nhận lệnh điều khiển, phục hồi sau lỗi API, nguồn/lịch sử còn sau init lại và EOF. Vòng chat dùng API thật chưa chạy trong môi trường agent vì hạn chế mạng; live ask ở trên là output người dùng cung cấp. Đã đóng HTTPError sau đọc để tránh ResourceWarning trong test.

## Chẩn đoán model chat khác file .env

Người dùng nhận Gemma trong check-chat dù đã chọn Flint. Kiểm tra tại môi trường agent: biến OPENROUTER_CHAT_MODEL không được đặt, cấu hình hiệu lực là recursive/flint-v1.0:free. Không tái hiện được môi trường terminal của người dùng. Config hiện ưu tiên biến môi trường hơn .env; đã thêm nguồn model vào output check-chat (biến môi trường hoặc đường dẫn file tuyệt đối), không hiển thị key. Test xác nhận môi trường override file và bỏ override sẽ đọc lại file. 10/10 test offline pass; không gọi API cho thay đổi chẩn đoán này, không sửa .env.

## Kiểm tra kết nối model chat riêng

Cấu hình đọc được: chat `recursive/flint-v1.0:free`, embeddings `nvidia/nemotron-3-embed-1b:free`, base URL chuẩn. Đường gọi chat dùng `/chat/completions` và model chat riêng; không dùng embedding model để generation. Đã thêm `check-chat` gửi đúng một request chat, không embeddings/SQLite. Thử thật trong môi trường agent vẫn lỗi kết nối mạng, chưa nhận response chat. Người dùng chạy `python -m onboarding check-chat` trên máy để xác nhận. HTTP errors nay ghi rõ endpoint/model và metadata giới hạn theo danh sách cho phép, không in key/raw body.

Kiểm thử mới nhất: 10/10 test offline pass; test check-chat xác nhận không gọi embed hoặc khởi tạo DB. Chưa có generation thật thành công được xác nhận. Output 429 trước đó của người dùng xảy ra sau retrieval thành công; cần phản hồi check-chat để phân biệt giới hạn provider/tài khoản.

## Sửa lỗi fallback câu giờ làm việc

Kết quả debug thật mới nhất do người dùng cung cấp: nguồn DEMO-ADM-001 đứng đầu với cosine 0.366482; nguồn tiếp theo 0.153325, 0.150082. Xác nhận ngưỡng 0.5 loại nguồn đúng trước khi gọi chat. Đã hạ mặc định dùng chung cho CLI/service xuống 0.3; không cần index lại. Test bổ sung xác nhận điểm 0.366482 đi tới generation, còn 0.2 fallback và không gọi chat. 9/9 test offline pass. Chưa xác nhận generation thật hay câu thời tiết ở ngưỡng mới; cần chạy lại hai câu --debug.

Người dùng báo cả câu giờ làm việc và thời tiết đều fallback. Chưa có điểm cosine nên chưa kết luận ngưỡng 0.5 là nguyên nhân. Phát hiện client bỏ qua chế độ query/passage mà Nemotron yêu cầu; đã sửa request riêng cho model này, thêm trường embedding_input_type bằng migration không xóa dữ liệu, yêu cầu index lại index Nemotron cũ. Đã thêm `ask --debug` để hiển thị điểm/top nguồn, số đoạn được chọn và fallback ở retrieval/generation. Giữ ngưỡng mặc định chờ kết quả thật.

Kiểm thử sau sửa: 9/9 offline pass, bao gồm request query/passage, index cũ cần tạo lại và debug fallback. Smoke trước sửa với ngưỡng 0.3 tiếp tục lỗi mạng tại môi trường agent; chưa có xác nhận live sau sửa. Người dùng cần chạy lại kb index rồi hai câu ask --debug theo README. Giữ nguyên API key và dữ liệu tài liệu, không tự thay model.

| Bước | Trạng thái |
|---|---|
| 1. App/config/SQLite | Hoàn thành CLI, .env, init không xóa dữ liệu |
| 2. Kho tri thức | Hoàn thành import JSON/CSV, list, chunking và index OpenRouter |
| 3. RAG và generation | Đã triển khai cosine search, ask có nguồn/fallback và chat completion client |
| 4. Console chat | Đã triển khai và kiểm thử offline; chưa smoke vòng chat thật |

Giữ nguyên `.env` có sẵn. Đã sửa README/STATUS bị mất dấu từ lần ghi trước. Workspace ban đầu chưa có mã Python; các ghi chú pytest 10/10 cũ không có kết quả để xác nhận.

## Kết quả thực tế

- `python -m unittest discover -s tests -v`: 8/8 pass, offline. Gồm kiểm tra SQLite/config, import/index/update, CSV/CLI, HTTP request/response, cosine chọn nguồn, fallback không gọi chat, lỗi khác model/dimension và CLI hỏi đáp mẫu bằng fake client.
- `python -m onboarding kb import data/demo_knowledge.json`: thành công, 12 tài liệu.
- `python -m onboarding kb list`: thành công, 12 tài liệu và 12 chunks; chưa có embeddings thật.
- OpenRouter embeddings thật: người dùng đã chạy `kb index` thành công trên máy với `nvidia/nemotron-3-embed-1b:free`. Đã đọc và kiểm tra DB: 12/12 vectors hợp lệ, cùng model, dimension 2048. Không index lại hoặc sửa các vectors này trong Bước 3.
- `python -m onboarding ask --help`: thành công.
- Smoke `python -m onboarding ask "Giờ làm việc của công ty là mấy giờ?"`: lỗi kết nối OpenRouter trong môi trường agent ở request embeddings câu hỏi; chưa tới generation. Chưa xác nhận generation thật hoặc chất lượng retrieval với model này. Không chuyển sang fake.
- Bước 1 đã chạy help và init hai lần thành công; test xác nhận dữ liệu được giữ.
- Ruff chưa cài; chưa chạy lint/format. Chat liên tục/session history chưa triển khai.

Index ghi toàn bộ vectors/model/dimension trong một transaction sau khi API hoàn tất; lỗi batch hoặc tài liệu thay đổi không ghi index dở dang. Thay đổi nội dung/title khi import làm mất hiệu lực embeddings liên quan. Đổi model cần chạy lại `kb index`.

Bước tiếp theo theo `prompts/03_CONSOLE_CHAT.md`: vòng chat /help, /exit và lưu session/messages. Trước đó cần chạy hai câu ask trong/ngoài kho để xác nhận generation thật và ngưỡng retrieval mới 0.3. Ngưỡng chỉ là heuristic; prompt giới hạn câu trả lời theo context chưa thay thế kiểm chứng nội dung. Tài liệu API chính thức được liên kết trong README.
