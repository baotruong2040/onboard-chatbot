# Kiểm tra cơ bản

Chỉ cần kiểm tra các luồng chính:
1. `init` tạo SQLite và chạy lại không xóa dữ liệu.
2. Import bộ JSON mẫu thành công, `kb list` hiển thị tài liệu.
3. Dùng vectors mẫu xác nhận cosine search trả đúng tài liệu gần nhất.
4. Câu hỏi có trong kho trả lời kèm nguồn; câu hỏi ngoài kho fallback.
5. Smoke test OpenRouter với một câu hỏi đơn giản khi có key và model đã cấu hình.

Tests tự động dùng fake OpenRouter client nên không cần mạng và không phát sinh phí. Smoke test thật chạy riêng; nếu chưa có key hoặc model phù hợp thì ghi chưa chạy. Không cần tạo benchmark hoặc bộ test lớn cho bản console ban đầu.
