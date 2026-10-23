# Cấu hình OpenRouter

Ứng dụng gọi hai endpoint qua cùng OpenRouter API:
- Embeddings: `https://openrouter.ai/api/v1/embeddings`
- Chat completion: `https://openrouter.ai/api/v1/chat/completions`

OpenRouter nhận bearer token. Model cho embeddings và chat cấu hình riêng; xem catalog OpenRouter để chọn model hiện hỗ trợ tác vụ tương ứng. Không chọn model chỉ theo thứ hạng; kiểm tra khả năng tiếng Việt, giới hạn đầu vào và mức phí hiện tại. Cùng một embeddings model/config phải dùng khi index tài liệu và embed câu hỏi.

Tạo API key trên OpenRouter rồi lưu vào `.env` ở máy:

```dotenv
OPENROUTER_API_KEY=điền_key_của_bạn
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_EMBEDDING_MODEL=nhà_cung_cấp/model_embedding
OPENROUTER_CHAT_MODEL=nhà_cung_cấp/model_chat
```

Không commit `.env`, không dán key vào prompt, không ghi key vào log. Dùng fake client để chạy unit tests. Khi cấu hình key/model, chạy một smoke test nhỏ cho embedding và chat; mỗi lần gọi API có thể phát sinh phí tùy model và tài khoản.

Tham khảo tài liệu chính thức:
- https://openrouter.ai/docs/api/api-reference/embeddings/submit-an-embedding-request
- https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion
- https://openrouter.ai/docs/guides/evaluate-and-optimize/rag
- https://openrouter.ai/models
