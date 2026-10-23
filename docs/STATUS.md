# Trạng thái hiện tại

Cập nhật ngày 2026-10-23.

## Streaming cho ask và chat

Đã thêm Gemini streamGenerateContent?alt=sse, parser SSE từng event UTF-8 và callback in/flush từng đoạn. Dùng lại request body/config hiện tại; embeddings và check-chat không đổi. Ask/chat không in lần hai sau khi stream kết thúc. Chỉ trả Answer hoàn chỉnh sau STOP và text không rỗng; chỉ lúc đó chat mới lưu nguyên văn trong SQLite.

Luồng bị ngắt, payload lỗi, API error, hết token hoặc safety block báo lỗi, không lưu cặp hỏi/đáp dở dang và không retry. Text đã in không thu hồi, CLI thông báo chưa hoàn tất. Ctrl+C trong stream chat hủy lượt/quay lại prompt; ask thoát 130. Context manager đóng response cả khi lỗi/hủy, không in thought/secrets/raw payload.

Trước sửa 14/14 test offline pass; sau sửa 16/16 pass, compileall pass. Test mới xác nhận callback trước khi đọc event tiếp theo, UTF-8/khoảng trắng, không lộ thought, lỗi sau partial, đóng response; chat test xác nhận không in lặp hoặc lưu partial. Đã thử một request streaming thật với key/model cấu hình hiện có nhưng lỗi kết nối Gemini, chưa nhận event nên chưa xác nhận streaming thật. Không đổi key/model hoặc in secrets.

## Văn bản tự nhiên nguyên vẹn

Người dùng chọn bỏ JSON và in trực tiếp văn bản LLM. Đã thay system prompt bằng hướng dẫn văn bản tự nhiên, bỏ parse/validate JSON và phần thêm nhãn/nguồn/giả định. ask/chat in answer.text trực tiếp; Gemini client giữ khoảng trắng/xuống dòng của text cuối, vẫn bỏ thought và báo lỗi API/safety/MAX_TOKENS. Không in raw HTTP envelope. Model được yêu cầu tự trích nguồn và nêu rõ suy luận/ước đoán/giả định, không bịa chính sách; không còn kiểm tra trích dẫn bằng backend.

Câu mới lưu nguyên văn text với answer_type unknown, assumptions/source metadata rỗng; không giả định các đoạn retrieval đều được viện dẫn. SQLite và metadata lịch sử cũ giữ nguyên, không cần index lại. Tests JSON cũ được thay bằng test giữ nguyên văn bản và lưu lịch sử; test HTTP kiểm tra khoảng trắng/thought. API thật chưa xác minh cho thay đổi này.

## Chuyển sang Gemini API trực tiếp

Theo yêu cầu mới thay OpenRouter bằng Gemini cho cả embeddings và generation. Runtime chỉ có onboarding/gemini.py, không thêm provider hoặc SDK. Dùng REST batchEmbedContents (requests/embeddings.values, RETRIEVAL_DOCUMENT/RETRIEVAL_QUERY cho gemini-embedding-001) và generateContent (systemInstruction/contents/candidates). Xác thực x-goog-api-key, không dùng key trong URL, không in raw response/thought/secrets. MAX_TOKENS, safety block, content rỗng và HTTP errors báo lỗi; không tự retry/fallback provider. JSON qua prompt giữ nguyên, backend vẫn validate bốn loại/assumptions/nguồn.

Config chuyển sang GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL, GEMINI_CHAT_MODEL, GEMINI_BASE_URL; không đọc key OpenRouter. Không sửa .env hiện có, không sửa DB/index người dùng. Cần cấu hình key Gemini rồi index lại; đổi model làm index cũ bị từ chối. check-chat chỉ cần key/chat model, không đòi embedding model. .env.example có model ví dụ, người dùng chọn model được cấp quyền.

Trước sửa: 15/16 pass, một test thất bại do DEFAULT_MIN_SCORE lúc đọc đầu tiên là 0.0 nhưng test vẫn ép 0.3. Không sửa ngưỡng trong lần chuyển provider; bỏ ràng buộc giá trị cụ thể trong test phân loại không liên quan retrieval, giữ test retrieval với ngưỡng 0.3 tường minh. Ở lần kiểm tra cuối code đã là 0.3; README/PLAN phản ánh giá trị cuối này. Chưa hiệu chỉnh ngưỡng với Gemini.

Sau chuyển: 17/17 test offline pass, compileall và CLI help pass, gồm hợp đồng HTTP Gemini, task query/document, không lộ key, bỏ thought, safety/MAX_TOKENS/content rỗng, config, CLI, RAG và migration. Config kiểm tra cuối chưa có Gemini key/models nên không gọi API thật. Các phần OpenRouter bên dưới là lịch sử, không phải hướng dẫn runtime hiện hành.

## Sửa chẩn đoán chat khi smoke inferred lỗi

Người dùng xác nhận SMOKE-001 đạt cosine 0.421750 và được gửi tới generation, sau đó client báo phản hồi chat không hợp lệ. Chưa có metadata phản hồi nên chưa xác định nguyên nhân thực tế. Phát hiện giới hạn 700 output token có thể bị reasoning dùng hết theo tài liệu OpenRouter. Tăng lên 4096, báo riêng finish_reason=length (kể cả content bị cắt nhưng không rỗng), content rỗng/sai kiểu và cấu trúc sai. Không dùng reasoning làm đáp án, không log raw response, không retry hoặc đổi model. Bổ sung mock kiểm tra các trường hợp này trong test HTTP hiện có. Cần chạy lại smoke để xác nhận với API thật; chưa tuyên bố nguyên nhân đã được chứng minh.

## Mở rộng suy luận và ước đoán

Theo yêu cầu mới, thay quy tắc context-only bằng grounded/inferred/estimate/clarification. Đã mở rộng Answer, prompt JSON và parse/validate ở backend: kiểu hợp lệ, câu trả lời không rỗng, assumptions chuỗi, source_ids số nguyên thuộc context, grounded/inferred phải có nguồn, estimate phải có giả định và không nguồn, [n] khớp nguồn. Chỉ hiện nguồn được viện dẫn. JSON sai trả thông báo chưa xác minh, không in raw response. Nhãn và giả định hiển thị trong console; không đưa tên trường JSON ra giao diện.

Kho rỗng hoặc không đoạn đạt ngưỡng gọi generation với context rỗng. API lỗi/index thiếu vector/sai model/dimension vẫn báo lỗi, không chuyển sang đoán. Prompt chỉ cho ước đoán lịch thông thường/gợi ý onboarding; không tự đặt lương, quyền lợi, điều kiện nghỉ phép, thông tin cá nhân, mật khẩu hoặc chính sách chính thức. Không chặn từ khóa; hướng dẫn có nguồn vẫn được phép. Không có bộ nhớ hội thoại, không nhập dự đoán vào KB hoặc tạo embeddings cho dự đoán.

Thống nhất DEFAULT_MIN_SCORE=0.3 trong service/CLI/README, thay mức 0.2 của lần rà soát trước. Lý do: 0.3 đã có smoke retrieval thật từ người dùng; không có bằng chứng đủ rộng để giữ mức thấp hơn. Không hạ ngưỡng nhằm ép nguồn. Test cũ được cập nhật vì thiếu nguồn nay gọi generation, không phải để che lỗi chọn nguồn.

Migration messages thêm answer_type (mặc định unknown) và assumptions_json ([]), giữ nguyên nội dung/nguồn lịch sử cũ. Không tự xem bản ghi cũ là grounded. Chạy init lặp không mất metadata mới.

Kiểm tra thực tế: trước sửa 12/12 test offline pass. Sau sửa 16/16 pass; compileall và ask --help pass. Bốn test mới bao phủ loại grounded/inferred, estimate/clarification thiếu chính sách, JSON/nguồn sai, migration và lưu metadata. Test dùng fake/mock chỉ chứng minh luồng xử lý; không chứng minh model thật suy luận đúng hoặc tuân thủ mọi hạn chế chính sách.

Đã đọc tài liệu structured outputs và catalog OpenRouter: recursive/flint-v1.0:free liệt kê response_format, nhưng hỗ trợ schema phụ thuộc endpoint. Chưa bật response_format; dùng prompt JSON và validation. Giữ nguyên key/model. Smoke generation thật dự kiến ba trường hợp với context giả lập: request đầu bị lỗi kết nối OpenRouter trong môi trường agent, nên dừng hai request còn lại. Chưa nhận được JSON thật, chưa xác minh suy luận/ước đoán/model tuân thủ chính sách. Smoke cũ của người dùng thuộc hành vi trước thay đổi này.

Hạn chế: backend kiểm tra cấu trúc và liên kết nguồn, chưa kiểm chứng ngữ nghĩa/phép tính hoặc mọi chính sách bịa đặt. Nhãn ước đoán không bảo đảm thông tin là chính sách thực tế. Cần smoke thật bằng terminal người dùng trước khi dựa vào hành vi mới.

## Rà soát nền tảng bước 4

Đủ nền tảng để phát triển tiếp trong phạm vi demo console: CLI, import/index, RAG và lưu phiên đã có kiểm thử offline. Phát hiện code hiện đặt DEFAULT_MIN_SCORE=0.2 trong khi README/test còn kỳ vọng 0.3. Giữ nguyên code hiện tại; sửa test kiểm tra ngưỡng 0.3 tường minh và cập nhật README. Không thay key/model hoặc index.

Smoke thật đã được người dùng xác nhận cho check-chat và ask ở ngưỡng 0.3; chưa xác nhận vòng chat thật hoặc chất lượng nhiều câu ở ngưỡng 0.2. Trước khi mở rộng đáng kể, nên chạy chat với một câu có nguồn, một câu ngoài kho rồi /exit. Lịch sử chỉ lưu trữ, chưa hỗ trợ câu hỏi nối tiếp; nguồn context chưa phải kiểm chứng độc lập nội dung generation.

Các mục bên dưới là lịch sử triển khai; những ghi chú “chưa triển khai/chưa xác nhận” cũ được thay thế bởi trạng thái mới hơn ở đầu file.

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
