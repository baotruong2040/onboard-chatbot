"""Gemini REST API; không chuyển provider hoặc tạo dữ liệu giả."""
import json
import math
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiError(ValueError):
    pass


def validate_vectors(vectors, count):
    if not isinstance(vectors, list) or len(vectors) != count:
        raise GeminiError("API trả sai số lượng embeddings.")
    dimension = None
    for vector in vectors:
        if not isinstance(vector, list) or not vector:
            raise GeminiError("Embedding phải là vector không rỗng.")
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
            raise GeminiError("Embedding chứa giá trị không hợp lệ.")
        if not any(vector):
            raise GeminiError("Embedding có độ dài bằng 0.")
        dimension = dimension or len(vector)
        if len(vector) != dimension:
            raise GeminiError("Dimension embeddings không đồng nhất.")
    return dimension


def model_path(model):
    name = model.removeprefix("models/")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise GeminiError("Model Gemini phải là ID hoặc models/ID, không phải ID OpenRouter.")
    return "models/" + name


class GeminiClient:
    def __init__(self, config):
        self.config = config
        if not config.base_url.startswith("https://"):
            raise GeminiError("GEMINI_BASE_URL phải dùng HTTPS.")

    def embed(self, texts, *, input_type=None):
        self.config.require_gemini(chat=False)
        model = model_path(self.config.embedding_model)
        task = {"search_document": "RETRIEVAL_DOCUMENT", "search_query": "RETRIEVAL_QUERY"}.get(input_type)
        requests = []
        for text in texts:
            item = {"model": model, "content": {"parts": [{"text": text}]}}
            if task:
                item["taskType"] = task
            requests.append(item)
        if not requests:
            return []
        payload = self._post("/" + model + ":batchEmbedContents", {"requests": requests})
        try:
            vectors = [item["values"] for item in payload["embeddings"]]
        except (KeyError, TypeError):
            raise GeminiError("Gemini trả cấu trúc embeddings không hợp lệ.") from None
        validate_vectors(vectors, len(texts))
        return vectors

    def _chat_body(self, messages):
        self.config.require_gemini(embedding=False)
        model = model_path(self.config.chat_model)
        system, contents = [], []
        for message in messages:
            if message["role"] == "system":
                system.append({"text": message["content"]})
            else:
                contents.append({"role": "model" if message["role"] == "assistant" else "user",
                                 "parts": [{"text": message["content"]}]})
        body = {"contents": contents, "generationConfig": {"temperature": 0, "maxOutputTokens": 4096}}
        if system:
            body["systemInstruction"] = {"parts": system}
        return model, body

    def stream_chat(self, messages, on_text):
        model, body = self._chat_body(messages)
        return self._post("/" + model + ":streamGenerateContent?alt=sse", body, on_text=on_text)

    def chat(self, messages):
        model, body = self._chat_body(messages)
        payload = self._post("/" + model + ":generateContent", body)
        try:
            candidate = payload["candidates"][0]
            reason = candidate.get("finishReason")
            if reason == "MAX_TOKENS":
                raise GeminiError("Gemini hết giới hạn 4096 token (MAX_TOKENS); thử câu hỏi ngắn hơn.")
            if reason != "STOP":
                raise GeminiError("Gemini chưa hoàn thành câu trả lời hoặc bị chặn an toàn; thử diễn đạt lại.")
            parts = candidate["content"]["parts"]
            text = "".join(part["text"] for part in parts
                           if not part.get("thought", False) and isinstance(part.get("text"), str))
            if not text.strip():
                raise GeminiError("Gemini trả content rỗng; không dùng thought làm câu trả lời.")
        except GeminiError:
            raise
        except (KeyError, IndexError, TypeError, AttributeError):
            raise GeminiError("Gemini không trả câu trả lời hợp lệ hoặc prompt đã bị chặn.") from None
        return text

    def _post(self, endpoint, body, *, on_text=None):
        request = Request(self.config.base_url + endpoint, data=json.dumps(body).encode("utf-8"),
                          headers={"x-goog-api-key": self.config.api_key, "Content-Type": "application/json"},
                          method="POST")
        try:
            with urlopen(request, timeout=60) as response:
                if on_text is not None:
                    return read_stream(response, on_text)
                return json.load(response)
        except HTTPError as error:
            code = error.code
            retry = error.headers.get("Retry-After") if error.headers else None
            error.close()
            hints = {400: "Kiểm tra key, model và dữ liệu đầu vào.", 401: "Kiểm tra Gemini API key.",
                     403: "Kiểm tra API key, quyền truy cập và khu vực hỗ trợ.",
                     404: "Kiểm tra model và base URL.", 429: "Vượt quota/rate limit; thử lại sau."}
            detail = f" Thử lại sau {retry} giây." if retry and retry.isdigit() else ""
            raise GeminiError(f"Gemini HTTP {code}. " + hints.get(code, "Dịch vụ gặp lỗi; thử lại sau.") + detail) from None
        except (URLError, TimeoutError, OSError, HTTPException):
            raise GeminiError("Không kết nối được Gemini; kiểm tra mạng hoặc timeout.") from None
        except GeminiError:
            raise
        except (ValueError, UnicodeError):
            raise GeminiError("Gemini trả JSON không hợp lệ.") from None


def read_stream(response, on_text):
    """Đọc từng SSE event, không đợi tải toàn bộ response."""
    pieces, data = [], []
    finished = False

    def consume():
        nonlocal finished
        payload = json.loads("\n".join(data))
        if not isinstance(payload, dict) or "error" in payload:
            raise GeminiError("Gemini báo lỗi trong stream; phản hồi chưa hoàn tất.")
        feedback = payload.get("promptFeedback") or {}
        if not isinstance(feedback, dict):
            raise GeminiError("Gemini trả stream không hợp lệ.")
        if feedback.get("blockReason"):
            raise GeminiError("Gemini đã chặn prompt; stream chưa hoàn tất.")
        candidates = payload.get("candidates", [])
        if not candidates:
            return
        try:
            candidate = candidates[0]
            reason = candidate.get("finishReason")
            if reason and reason != "STOP":
                raise GeminiError("Gemini dừng stream do giới hạn token hoặc bị chặn; phản hồi chưa hoàn tất.")
            parts = candidate.get("content", {}).get("parts", [])
            text = "".join(part["text"] for part in parts
                           if not part.get("thought", False) and isinstance(part.get("text"), str))
            if text:
                if finished:
                    raise GeminiError("Stream Gemini không hợp lệ sau khi kết thúc.")
                pieces.append(text)
                on_text(text)
            finished = finished or reason == "STOP"
        except (KeyError, TypeError, AttributeError, IndexError):
            raise GeminiError("Gemini trả stream không hợp lệ.") from None

    for raw in response:
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line:
            if data:
                consume()
                data.clear()
        elif line.startswith("data:"):
            value = line[5:]
            data.append(value[1:] if value.startswith(" ") else value)
    if data:
        consume()
    text = "".join(pieces)
    if not finished or not text.strip():
        raise GeminiError("Stream Gemini bị ngắt hoặc không có nội dung; phản hồi chưa hoàn tất.")
    return text
