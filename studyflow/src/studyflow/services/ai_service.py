from __future__ import annotations

import os
from typing import Any, Sequence

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from studyflow.models import QuestionType, StudyMaterial


DEFAULT_MODEL = "gpt-5.6-sol"
SYSTEM_PROMPT = """Bạn là AI Tutor hỗ trợ sinh viên ôn tập sau buổi học.

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin trong nội dung bài giảng được cung cấp.
2. Tóm tắt rõ ràng, ưu tiên khái niệm, quy trình và mối quan hệ quan trọng.
3. Câu hỏi phải kiểm tra khả năng hiểu, không chỉ sao chép từ khóa.
4. Mỗi câu hỏi có đáp án và giải thích ngắn.
5. Không bịa thông tin. Nếu tài liệu không đủ rõ, hãy ghi chú điều đó.
6. Toàn bộ đầu ra dùng tiếng Việt và tuân thủ đúng schema."""


class MissingAPIKeyError(RuntimeError):
    """Raised before an API call when no OpenAI credential is configured."""


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


def _response_kwargs(model: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_output_tokens": 5_000,
        "store": False,
        "verbosity": "low",
    }
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        kwargs["reasoning"] = {"effort": "low"}
    return kwargs


def generate_study_material(
    document_text: str,
    *,
    question_count: int = 8,
    question_types: Sequence[QuestionType] = ("multiple_choice", "short_answer"),
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> StudyMaterial:
    """Create summary and quiz in one validated OpenAI Responses API call."""

    if not document_text.strip():
        raise AIGenerationError("Tài liệu chưa có nội dung để AI phân tích.")
    if question_count < 5 or question_count > 10:
        raise ValueError("question_count must be between 5 and 10")
    if not question_types:
        raise ValueError("At least one question type is required")

    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    if client is None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise MissingAPIKeyError("Hệ thống chưa được cấu hình OPENAI_API_KEY.")
        client = OpenAI(api_key=resolved_key, timeout=60.0, max_retries=1)

    prompt = build_generation_prompt(
        document_text,
        question_count=question_count,
        question_types=question_types,
    )
    try:
        response = client.responses.parse(
            instructions=SYSTEM_PROMPT,
            input=prompt,
            text_format=StudyMaterial,
            **_response_kwargs(selected_model),
        )
    except APITimeoutError as exc:
        raise AIGenerationError("AI đang phản hồi chậm. Vui lòng thử lại sau ít phút.") from exc
    except RateLimitError as exc:
        raise AIGenerationError("Dịch vụ AI đang quá tải hoặc đã chạm giới hạn sử dụng.") from exc
    except APIConnectionError as exc:
        raise AIGenerationError("Không thể kết nối đến dịch vụ AI. Hãy kiểm tra mạng và thử lại.") from exc
    except APIStatusError as exc:
        raise AIGenerationError(f"Dịch vụ AI từ chối yêu cầu (mã {exc.status_code}).") from exc
    except Exception as exc:
        raise AIGenerationError("Không thể chuẩn hóa kết quả AI. Vui lòng thử tạo lại.") from exc

    material = getattr(response, "output_parsed", None)
    if material is None:
        raise AIGenerationError("AI không trả về nội dung có cấu trúc. Vui lòng thử tạo lại.")
    return material
