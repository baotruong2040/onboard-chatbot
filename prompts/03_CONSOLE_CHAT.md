# Bước 4: Chat và hoàn thiện

Thêm console chat liên tục dùng chung `ask`/RAG service, lệnh `/help` và `/exit`, lưu session/message trong SQLite nếu phù hợp code hiện tại. Không kết nối Telegram.
Chạy luồng demo: init→import→index→ask một câu có nguồn→ask câu ngoài kho→chat. Chạy các kiểm tra cơ bản trong docs/TESTS.md. Tách kết quả fake và API thật; không báo API thật nếu chưa gọi. Hoàn thiện README hướng dẫn tạo `.env`, cài dependencies và dùng OpenRouter. Cập nhật STATUS.
