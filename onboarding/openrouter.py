"""OpenRouter embeddings qua HTTP chuẩn; không tự chuyển sang dữ liệu giả."""

import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OpenRouterError(ValueError):
    pass


def validate_vectors(vectors, count):
    if not isinstance(vectors, list) or len(vectors) != count:
        raise OpenRouterError("API trả sai số lượng embeddings.")
    dimension = None
    for vector in vectors:
        if not isinstance(vector, list) or not vector:
            raise OpenRouterError("Embedding phải là vector không rỗng.")
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
            raise OpenRouterError("Embedding chứa giá trị không hợp lệ.")
        if not any(vector):
            raise OpenRouterError("Embedding có độ dài bằng 0.")
        dimension = dimension or len(vector)
        if len(vector) != dimension:
            raise OpenRouterError("Dimension embeddings không đồng nhất.")
    return dimension


class OpenRouterClient:
    def __init__(self, config):
        config.require_openrouter(chat=False)
        if not config.base_url.startswith("https://"):
            raise OpenRouterError("OPENROUTER_BASE_URL phải dùng HTTPS.")
        self.config = config

    def embed(self, texts, *, input_type=None):
        body = {"model": self.config.embedding_model, "input": texts,
                "encoding_format": "float"}
        if input_type and self.config.embedding_model.split(":")[0] == "nvidia/nemotron-3-embed-1b":
            body["input_type"] = {"search_document": "passage", "search_query": "query"}[input_type]
        payload = self._post("/embeddings", body)
        try:
            data = payload["data"]
            if sorted(item["index"] for item in data) != list(range(len(texts))):
                raise ValueError
            vectors = [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
        except (KeyError, TypeError, ValueError):
            raise OpenRouterError("OpenRouter trả cấu trúc embeddings không hợp lệ.") from None
        validate_vectors(vectors, len(texts))
        return vectors

    def chat(self, messages):
        self.config.require_openrouter()
        payload = self._post("/chat/completions", {
            "model": self.config.chat_model, "messages": messages,
            "temperature": 0, "max_tokens": 700,
        })
        try:
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError
        except (KeyError, IndexError, TypeError, ValueError):
            raise OpenRouterError("OpenRouter trả câu trả lời chat không hợp lệ.") from None
        return content.strip()

    def _post(self, endpoint, body):
        request = Request(
            self.config.base_url + endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.config.api_key,
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.load(response)
        except HTTPError as error:
            details = []
            try:
                failure = json.load(error).get("error", {})
                metadata = failure.get("metadata") or {}
                # Chỉ hiện mã định danh hạn chế, không in raw response/provider prompt.
                for name in ("provider_name", "limit_source"):
                    value = metadata.get(name)
                    if isinstance(value, str) and len(value) <= 100 and all(
                        char.isalnum() or char in "_- ." for char in value
                    ) and self.config.api_key not in value:
                        details.append(f"{name}={value}")
            except (ValueError, TypeError, AttributeError, OSError):
                pass
            finally:
                error.close()
            retry = error.headers.get("Retry-After") if error.headers else None
            if retry and retry.isdigit():
                details.append(f"thử lại sau {retry} giây")
            hints = {401: "Kiểm tra API key.", 402: "Kiểm tra số dư tài khoản.",
                     429: "Đã vượt giới hạn; thử lại sau.",
                     400: "Kiểm tra model và dữ liệu đầu vào.",
                     404: "Kiểm tra base URL và model."}
            raise OpenRouterError(
                f"OpenRouter {endpoint} (model={body.get('model')}) HTTP {error.code}. "
                + hints.get(error.code, "Dịch vụ gặp lỗi; thử lại sau.")
                + (" " + "; ".join(details) if details else "")
            ) from None
        except (URLError, TimeoutError, OSError):
            raise OpenRouterError("Không kết nối được OpenRouter; kiểm tra mạng hoặc timeout.") from None
        except (ValueError, UnicodeError):
            raise OpenRouterError("OpenRouter trả JSON không hợp lệ.") from None
        return payload
