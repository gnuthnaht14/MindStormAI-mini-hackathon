from __future__ import annotations

import json
import os
from typing import Any, Sequence

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from studyflow.models import QuestionType, StudyMaterial


# OpenRouter là một proxy tương thích OpenAI SDK, nhưng:
#   - dùng base_url riêng (https://openrouter.ai/api/v1)
#   - dùng API key riêng (OPENROUTER_API_KEY, lấy tại https://openrouter.ai/keys)
#   - KHÔNG hỗ trợ Responses API (client.responses.*) — chỉ hỗ trợ
#     Chat Completions API (client.chat.completions.*)
# Tài liệu: https://openrouter.ai/docs/quickstart
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT_TEMPLATE = """Bạn là AI Tutor hỗ trợ sinh viên ôn tập sau buổi học.

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin trong nội dung bài giảng được cung cấp.
2. Tóm tắt rõ ràng, ưu tiên khái niệm, quy trình và mối quan hệ quan trọng.
3. Câu hỏi phải kiểm tra khả năng hiểu, không chỉ sao chép từ khóa.
4. Mỗi câu hỏi có đáp án và giải thích ngắn.
5. Không bịa thông tin. Nếu tài liệu không đủ rõ, hãy ghi chú điều đó.
6. Toàn bộ đầu ra dùng tiếng Việt.
7. CHỈ trả về một object JSON DUY NHẤT đúng theo JSON Schema bên dưới.
   Không thêm markdown, không thêm ```json, không thêm bất kỳ văn bản nào
   khác ngoài JSON hợp lệ, không thêm field ngoài schema.

JSON SCHEMA:
{schema}"""


class MissingAPIKeyError(RuntimeError):
    """Raised before an API call when no OpenRouter credential is configured."""


class AIGenerationError(RuntimeError):
    """Raised with a safe message suitable for the UI."""


def _type_instructions(question_types: Sequence[QuestionType]) -> str:
    labels = {
        "multiple_choice": "trắc nghiệm nhiều lựa chọn",
        "true_false": "đúng/sai",
        "short_answer": "tự luận ngắn",
    }
    return ", ".join(labels[item] for item in question_types)


def build_generation_prompt(
    document_text: str,
    *,
    question_count: int,
    question_types: Sequence[QuestionType],
) -> str:
    return f"""Hãy phân tích nội dung bài giảng dưới đây.

Yêu cầu:
- Đặt một tiêu đề ngắn, sát nội dung.
- Viết bản tóm tắt đủ để ôn tập nhanh.
- Liệt kê từ 5 đến 10 ý chính.
- Tạo đúng {question_count} câu hỏi ôn tập.
- Dạng câu hỏi được phép: {_type_instructions(question_types)}.
- Với câu trắc nghiệm, cung cấp 4 phương án rõ ràng.
- Câu hỏi và đáp án phải bám sát tài liệu.
- Ngôn ngữ đầu ra: tiếng Việt.

NỘI DUNG BÀI GIẢNG:
{document_text}"""


def _build_client(api_key: str | None) -> OpenAI:
    resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not resolved_key:
        raise MissingAPIKeyError(
            "Hệ thống chưa được cấu hình OPENROUTER_API_KEY. "
            "Lấy API key tại https://openrouter.ai/keys rồi thêm vào file .env."
        )
    return OpenAI(
        api_key=resolved_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=60.0,
        max_retries=1,
        default_headers={
            # 2 header OpenRouter khuyến nghị gửi kèm (không bắt buộc, nhưng giúp
            # app hiện đúng tên/nguồn trên dashboard OpenRouter thay vì "unknown").
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://studyflow.local"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "StudyFlow AI"),
        },
    )


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    """Phòng khi model lỡ bọc kết quả trong ```json ... ``` dù đã dặn không làm vậy."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def _call_model(client: OpenAI, model: str, messages: list[dict[str, str]]) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=5_000,
        temperature=0.4,
        # "JSON mode" chuẩn Chat Completions, được hầu hết model trên
        # OpenRouter hỗ trợ (khác với response.parse/text_format của
        # Responses API vốn chỉ có ở OpenAI).
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise AIGenerationError("AI không trả về nội dung. Vui lòng thử tạo lại.")
    return content


def _describe_status_error(exc: APIStatusError) -> str:
    if exc.status_code == 401:
        return "OpenRouter từ chối API key (401). Kiểm tra lại OPENROUTER_API_KEY trong .env."
    if exc.status_code == 402:
        return "Tài khoản OpenRouter không đủ credit (402). Vui lòng nạp thêm tại openrouter.ai."
    if exc.status_code == 404:
        return "Model không tồn tại trên OpenRouter hoặc bạn chưa có quyền dùng (404)."
    if exc.status_code == 429:
        return "OpenRouter đang giới hạn tần suất gọi (429). Vui lòng thử lại sau."
    return f"Dịch vụ AI từ chối yêu cầu (mã {exc.status_code})."


def generate_study_material(
    document_text: str,
    *,
    question_count: int = 8,
    question_types: Sequence[QuestionType] = ("multiple_choice", "short_answer"),
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> StudyMaterial:
    """Create summary and quiz in one validated OpenRouter chat-completions call."""

    if not document_text.strip():
        raise AIGenerationError("Tài liệu chưa có nội dung để AI phân tích.")
    if question_count < 5 or question_count > 10:
        raise ValueError("question_count must be between 5 and 10")
    if not question_types:
        raise ValueError("At least one question type is required")

    selected_model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    if client is None:
        client = _build_client(api_key)

    prompt = build_generation_prompt(
        document_text,
        question_count=question_count,
        question_types=question_types,
    )
    schema_json = json.dumps(StudyMaterial.model_json_schema(), ensure_ascii=False)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)},
        {"role": "user", "content": prompt},
    ]

    last_error: Exception | None = None
    raw_content = ""
    for _ in range(2):  # gọi 1 lần, retry thêm 1 lần nếu JSON/schema sai
        try:
            raw_content = _call_model(client, selected_model, messages)
            parsed_json = _extract_json_object(raw_content)
            return StudyMaterial.model_validate(parsed_json)
        except APITimeoutError as exc:
            raise AIGenerationError("AI đang phản hồi chậm. Vui lòng thử lại sau ít phút.") from exc
        except RateLimitError as exc:
            raise AIGenerationError("Dịch vụ AI đang quá tải hoặc đã chạm giới hạn sử dụng.") from exc
        except APIConnectionError as exc:
            raise AIGenerationError("Không thể kết nối đến dịch vụ AI. Hãy kiểm tra mạng và thử lại.") from exc
        except APIStatusError as exc:
            raise AIGenerationError(_describe_status_error(exc)) from exc
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": raw_content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Kết quả trên chưa đúng định dạng JSON theo schema (lỗi: {exc}). "
                        "Hãy trả lại DUY NHẤT một JSON object hợp lệ, không kèm giải thích "
                        "hay markdown."
                    ),
                }
            )
            continue
        except Exception as exc:
            raise AIGenerationError("Không thể chuẩn hóa kết quả AI. Vui lòng thử tạo lại.") from exc

    raise AIGenerationError(
        "Không thể chuẩn hóa kết quả AI thành JSON hợp lệ sau khi thử lại."
    ) from last_error