from __future__ import annotations

import os
import re
from typing import Any, Sequence

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from studyflow.models import QuestionType, StudyMaterial
from studyflow.services.quiz_service import is_correct_answer


DEFAULT_MODEL = "gpt-5.6-sol"
SYSTEM_PROMPT = """Bạn là AI Tutor hỗ trợ sinh viên ôn tập sau buổi học.

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin trong nội dung bài giảng được cung cấp.
2. Giải thích theo cách một sinh viên mới học có thể hiểu, ưu tiên khái niệm, quy trình và mối quan hệ quan trọng.
3. Câu hỏi phải kiểm tra khả năng hiểu, không chỉ sao chép từ khóa.
4. Mỗi câu hỏi có đáp án và giải thích ngắn.
5. Không bịa thông tin. Nếu tài liệu không đủ rõ, hãy ghi chú điều đó.
6. Mọi source_pages phải là số trang xuất hiện trong nhãn --- Trang N --- và thật sự hỗ trợ nội dung được dẫn.
7. Không gắn citation vào trang không chứa căn cứ. Không tạo ví dụ mới rồi trình bày như ví dụ có trong tài liệu.
8. Toàn bộ đầu ra dùng tiếng Việt và tuân thủ đúng schema."""

PAGE_LABEL_PATTERN = re.compile(r"--- Trang (\d+) ---")


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
    return f"""Hãy biến nội dung bài giảng dưới đây thành Summary V2 dễ hiểu và có dẫn nguồn theo trang.

Yêu cầu:
- Đặt một tiêu đề ngắn, sát nội dung.
- overview: giải thích bài học trong 3–5 câu để đọc trong khoảng 30 giây.
- learning_objectives: 2–5 điều người học cần hiểu hoặc làm được sau bài.
- key_concepts: 3–8 khái niệm trọng tâm; giải thích bằng ngôn ngữ đơn giản.
- example của key concept chỉ được lấy từ tài liệu; nếu tài liệu không có ví dụ thì trả null.
- process_steps: các bước theo đúng thứ tự nếu tài liệu có quy trình; nếu không có thì trả list rỗng.
- common_misconceptions: điểm dễ nhầm có căn cứ trực tiếp; nếu không đủ căn cứ thì trả list rỗng.
- takeaways: 3–6 điều quan trọng nhất cần nhớ.
- Mỗi overview/objective/concept/process/misconception/takeaway phải có source_pages chính xác.
- Tạo đúng {question_count} câu hỏi ôn tập.
- Dạng câu hỏi được phép: {_type_instructions(question_types)}.
- Với câu trắc nghiệm, cung cấp 4 phương án rõ ràng.
- Không tạo câu hỏi tự luận ngắn nếu dạng này không nằm trong danh sách được phép.
- answer của câu trắc nghiệm/đúng-sai phải khớp nguyên văn một phần tử trong options.
- Mỗi câu hỏi, đáp án và giải thích phải bám sát tài liệu và có source_pages.
- Chỉ dùng số trang có trong nhãn --- Trang N ---; ưu tiên tập trang nhỏ nhất đủ làm căn cứ.
- Ngôn ngữ đầu ra: tiếng Việt.

NỘI DUNG BÀI GIẢNG:
{document_text}"""


def _response_kwargs(model: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_output_tokens": 5_000,
        "store": False,
    }
    if model.startswith("gpt-5"):
        kwargs["text"] = {"verbosity": "low"}
        kwargs["reasoning"] = {"effort": "low"}
    return kwargs


def create_openai_client(api_key: str | None = None) -> OpenAI:
    """Create the shared OpenAI client without exposing credentials."""

    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise MissingAPIKeyError("Hệ thống chưa được cấu hình OPENAI_API_KEY.")
    return OpenAI(
        api_key=resolved_key,
        timeout=60.0,
        max_retries=1,
    )


def generate_study_material(
    document_text: str,
    *,
    question_count: int = 8,
    question_types: Sequence[QuestionType] = ("multiple_choice", "true_false"),
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> StudyMaterial:
    """Create summary and quiz through the OpenAI Responses API."""

    if not document_text.strip():
        raise AIGenerationError("Tài liệu chưa có nội dung để AI phân tích.")
    if question_count < 5 or question_count > 10:
        raise ValueError("question_count must be between 5 and 10")
    if not question_types:
        raise ValueError("At least one question type is required")

    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    if client is None:
        client = create_openai_client(api_key)

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
    if len(material.questions) != question_count:
        raise AIGenerationError(
            f"AI trả về {len(material.questions)} câu hỏi thay vì {question_count}. Vui lòng tạo lại."
        )
    unexpected_types = sorted({question.type for question in material.questions} - set(question_types))
    if unexpected_types:
        raise AIGenerationError(
            "AI trả về dạng câu hỏi không được yêu cầu. Vui lòng tạo lại bộ câu hỏi."
        )
    ungradeable_questions = [
        question for question in material.questions
        if not question.options or not any(is_correct_answer(question, option) for option in question.options)
    ]
    if ungradeable_questions:
        raise AIGenerationError(
            "AI trả về câu hỏi không có đáp án khớp với lựa chọn. Vui lòng tạo lại bộ câu hỏi."
        )
    _validate_page_citations(material, document_text)
    return material


def _validate_page_citations(material: StudyMaterial, document_text: str) -> None:
    """Reject page references that cannot exist in the uploaded document."""

    available_pages = {int(value) for value in PAGE_LABEL_PATTERN.findall(document_text)}
    if not available_pages:
        return

    cited_pages: list[int] = []
    cited_pages.extend(material.overview.source_pages)
    for item in material.learning_objectives:
        cited_pages.extend(item.source_pages)
    for concept in material.key_concepts:
        cited_pages.extend(concept.source_pages)
    for item in material.process_steps:
        cited_pages.extend(item.source_pages)
    for item in material.common_misconceptions:
        cited_pages.extend(item.source_pages)
    for item in material.takeaways:
        cited_pages.extend(item.source_pages)
    for question in material.questions:
        cited_pages.extend(question.source_pages)

    invalid_pages = sorted(set(cited_pages) - available_pages)
    if invalid_pages:
        invalid = ", ".join(str(page) for page in invalid_pages)
        raise AIGenerationError(f"AI dẫn nguồn đến trang không tồn tại ({invalid}). Vui lòng tạo lại.")
