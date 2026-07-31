from __future__ import annotations

import os
import re
from math import sqrt
from typing import Any, Sequence, TypeVar

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel

from studyflow.models import QuestionType, QuizMaterial, SummaryMaterial
from studyflow.services.quiz_service import is_correct_answer


DEFAULT_MODEL = "gpt-5.6-sol"
PAGE_LABEL_PATTERN = re.compile(r"--- Trang (\d+) ---")
PAGE_SECTION_PATTERN = re.compile(
    r"--- Trang (\d+) ---\s*(.*?)(?=\n\s*--- Trang \d+ ---|\Z)",
    re.DOTALL,
)
StructuredResult = TypeVar("StructuredResult", bound=BaseModel)

VIETNAMESE_STOP_WORDS = {
    "các", "có", "của", "cho", "được", "giữa", "khi", "là", "một", "những",
    "này", "theo", "trong", "trên", "từ", "và", "với", "về", "để",
}

COMMON_RULES = """Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin trong nội dung bài giảng được cung cấp.
2. Không bịa thông tin và không dùng kiến thức bên ngoài tài liệu.
3. Mọi source_pages phải là số trang xuất hiện trong nhãn --- Trang N --- và thật sự hỗ trợ nội dung.
4. Không gắn citation vào trang không chứa căn cứ.
5. Toàn bộ đầu ra dùng tiếng Việt và tuân thủ đúng schema."""

SUMMARY_SYSTEM_PROMPT = f"""Bạn là AI Tutor chuyên tạo bản tóm tắt bài giảng dễ hiểu cho sinh viên.

{COMMON_RULES}"""

QUIZ_SYSTEM_PROMPT = f"""Bạn là AI Tutor chuyên tạo bài quiz để sinh viên tự kiểm tra kiến thức.

{COMMON_RULES}
6. Chỉ tạo câu hỏi trắc nghiệm hoặc đúng/sai theo dạng được yêu cầu.
7. Mỗi câu hỏi phải có đáp án khớp với một lựa chọn và có giải thích ngắn."""


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


def _available_pages(document_text: str) -> set[int]:
    return {int(value) for value in PAGE_LABEL_PATTERN.findall(document_text)}


def _valid_pages_instruction(document_text: str) -> str:
    pages = sorted(_available_pages(document_text))
    page_list = ", ".join(str(page) for page in pages)
    return (
        f"source_pages chỉ được chứa số trang trong danh sách: [{page_list}]. "
        "Không dùng năm, số liệu, token, phiên bản hoặc số thứ tự trong nội dung làm số trang."
    )


def build_summary_prompt(document_text: str) -> str:
    return f"""Hãy tạo Summary V2 dễ hiểu và có dẫn nguồn theo trang từ bài giảng dưới đây.

Yêu cầu:
- Đặt một tiêu đề ngắn, sát nội dung.
- overview: giải thích bài học trong 3–5 câu để đọc trong khoảng 30 giây.
- learning_objectives: 2–5 điều người học cần hiểu hoặc làm được sau bài.
- key_concepts: 3–8 khái niệm trọng tâm; giải thích bằng ngôn ngữ đơn giản.
- example của key concept chỉ được lấy từ tài liệu; nếu tài liệu không có ví dụ thì trả null.
- process_steps: các bước theo đúng thứ tự nếu tài liệu có quy trình; nếu không có thì trả list rỗng.
- common_misconceptions: điểm dễ nhầm có căn cứ trực tiếp; nếu không đủ căn cứ thì trả list rỗng.
- takeaways: 3–6 điều quan trọng nhất cần nhớ.
- Mọi thành phần phải có source_pages chính xác.
- {_valid_pages_instruction(document_text)}
- Không tạo câu hỏi hoặc quiz trong response này.

NỘI DUNG BÀI GIẢNG:
{document_text}"""


def build_quiz_prompt(
    document_text: str,
    *,
    question_count: int,
    question_types: Sequence[QuestionType],
) -> str:
    return f"""Hãy tạo một bài quiz độc lập từ nội dung bài giảng dưới đây.

Yêu cầu:
- Tạo đúng {question_count} câu hỏi.
- Dạng câu hỏi được phép: {_type_instructions(question_types)}.
- Với câu trắc nghiệm, cung cấp đúng 4 phương án rõ ràng.
- Với câu đúng/sai, options phải là [\"Đúng\", \"Sai\"].
- answer phải khớp nguyên văn một phần tử trong options.
- Mỗi câu hỏi, đáp án và giải thích phải bám sát tài liệu và có source_pages.
- {_valid_pages_instruction(document_text)}
- Không tạo summary, mục tiêu học tập hoặc key concepts trong response này.

NỘI DUNG BÀI GIẢNG:
{document_text}"""


def _response_kwargs(model: str, *, max_output_tokens: int) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_output_tokens": max_output_tokens,
        "store": False,
    }
    if model.startswith("gpt-5"):
        kwargs["text"] = {"verbosity": "low"}
        kwargs["reasoning"] = {"effort": "low"}
    return kwargs


def create_openai_client(api_key: str | None = None) -> OpenAI:
    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise MissingAPIKeyError("Hệ thống chưa được cấu hình OPENAI_API_KEY.")
    return OpenAI(api_key=resolved_key, timeout=60.0, max_retries=1)


def _parse_structured(
    *,
    client: Any,
    model: str,
    instructions: str,
    prompt: str,
    text_format: type[StructuredResult],
    max_output_tokens: int,
) -> StructuredResult:
    try:
        response = client.responses.parse(
            instructions=instructions,
            input=prompt,
            text_format=text_format,
            **_response_kwargs(model, max_output_tokens=max_output_tokens),
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

    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise AIGenerationError("AI không trả về nội dung có cấu trúc. Vui lòng thử tạo lại.")
    return parsed


def generate_summary(
    document_text: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> SummaryMaterial:
    """Generate only the summary artifact in one API call."""

    if not document_text.strip():
        raise AIGenerationError("Tài liệu chưa có nội dung để AI phân tích.")
    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    resolved_client = client or create_openai_client(api_key)
    summary = _parse_structured(
        client=resolved_client,
        model=selected_model,
        instructions=SUMMARY_SYSTEM_PROMPT,
        prompt=build_summary_prompt(document_text),
        text_format=SummaryMaterial,
        max_output_tokens=3_500,
    )
    _repair_summary_citations(summary, document_text)
    _validate_summary_citations(summary, document_text)
    return summary


def generate_quiz(
    document_text: str,
    *,
    question_count: int = 8,
    question_types: Sequence[QuestionType] = ("multiple_choice", "true_false"),
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> QuizMaterial:
    """Generate only the quiz artifact in one API call."""

    if not document_text.strip():
        raise AIGenerationError("Tài liệu chưa có nội dung để AI phân tích.")
    if question_count < 5 or question_count > 10:
        raise ValueError("question_count must be between 5 and 10")
    if not question_types:
        raise ValueError("At least one question type is required")

    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    resolved_client = client or create_openai_client(api_key)
    quiz = _parse_structured(
        client=resolved_client,
        model=selected_model,
        instructions=QUIZ_SYSTEM_PROMPT,
        prompt=build_quiz_prompt(
            document_text,
            question_count=question_count,
            question_types=question_types,
        ),
        text_format=QuizMaterial,
        max_output_tokens=3_000,
    )
    _repair_quiz_citations(quiz, document_text)
    _validate_quiz(quiz, document_text, question_count, question_types)
    return quiz


def _page_sections(document_text: str) -> dict[int, str]:
    return {
        int(page_number): content.strip()
        for page_number, content in PAGE_SECTION_PATTERN.findall(document_text)
    }


def _content_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[^\W\d_]{3,}", text.casefold(), flags=re.UNICODE))
    return tokens - VIETNAMESE_STOP_WORDS


def _best_matching_page(query: str, document_text: str) -> int | None:
    sections = _page_sections(document_text)
    if not sections:
        return None
    query_tokens = _content_tokens(query)
    if not query_tokens:
        return min(sections)

    def score(item: tuple[int, str]) -> tuple[float, int]:
        page_number, page_text = item
        page_tokens = _content_tokens(page_text)
        overlap = len(query_tokens & page_tokens)
        normalized_score = overlap / sqrt(max(len(query_tokens), 1))
        return normalized_score, -page_number

    return max(sections.items(), key=score)[0]


def _repair_source_pages(
    cited_pages: Sequence[int],
    *,
    query: str,
    document_text: str,
) -> list[int]:
    available_pages = _available_pages(document_text)
    if not available_pages:
        return sorted(set(cited_pages))
    valid_pages = sorted(set(cited_pages) & available_pages)
    if valid_pages:
        return valid_pages
    matched_page = _best_matching_page(query, document_text)
    return [matched_page if matched_page is not None else min(available_pages)]


def _repair_summary_citations(summary: SummaryMaterial, document_text: str) -> None:
    summary.overview.source_pages = _repair_source_pages(
        summary.overview.source_pages,
        query=summary.overview.text,
        document_text=document_text,
    )
    for item in [
        *summary.learning_objectives,
        *summary.process_steps,
        *summary.common_misconceptions,
        *summary.takeaways,
    ]:
        item.source_pages = _repair_source_pages(
            item.source_pages,
            query=item.text,
            document_text=document_text,
        )
    for concept in summary.key_concepts:
        query = " ".join(
            part for part in [concept.name, concept.simple_explanation, concept.example] if part
        )
        concept.source_pages = _repair_source_pages(
            concept.source_pages,
            query=query,
            document_text=document_text,
        )


def _repair_quiz_citations(quiz: QuizMaterial, document_text: str) -> None:
    for question in quiz.questions:
        query = " ".join([question.question, question.answer, question.explanation])
        question.source_pages = _repair_source_pages(
            question.source_pages,
            query=query,
            document_text=document_text,
        )


def _validate_pages(cited_pages: Sequence[int], document_text: str) -> None:
    available_pages = _available_pages(document_text)
    if not available_pages:
        return
    invalid_pages = sorted(set(cited_pages) - available_pages)
    if invalid_pages:
        invalid = ", ".join(str(page) for page in invalid_pages)
        raise AIGenerationError(f"AI dẫn nguồn đến trang không tồn tại ({invalid}). Vui lòng tạo lại.")


def _validate_summary_citations(summary: SummaryMaterial, document_text: str) -> None:
    cited_pages: list[int] = list(summary.overview.source_pages)
    for item in summary.learning_objectives:
        cited_pages.extend(item.source_pages)
    for concept in summary.key_concepts:
        cited_pages.extend(concept.source_pages)
    for item in summary.process_steps:
        cited_pages.extend(item.source_pages)
    for item in summary.common_misconceptions:
        cited_pages.extend(item.source_pages)
    for item in summary.takeaways:
        cited_pages.extend(item.source_pages)
    _validate_pages(cited_pages, document_text)


def _validate_quiz(
    quiz: QuizMaterial,
    document_text: str,
    question_count: int,
    question_types: Sequence[QuestionType],
) -> None:
    if len(quiz.questions) != question_count:
        raise AIGenerationError(
            f"AI trả về {len(quiz.questions)} câu hỏi thay vì {question_count}. Vui lòng tạo lại."
        )
    unexpected_types = sorted({question.type for question in quiz.questions} - set(question_types))
    if unexpected_types:
        raise AIGenerationError("AI trả về dạng câu hỏi không được yêu cầu. Vui lòng tạo lại bộ câu hỏi.")
    ungradeable = [
        question for question in quiz.questions
        if not question.options or not any(is_correct_answer(question, option) for option in question.options)
    ]
    if ungradeable:
        raise AIGenerationError(
            "AI trả về câu hỏi không có đáp án khớp với lựa chọn. Vui lòng tạo lại bộ câu hỏi."
        )
    cited_pages = [page for question in quiz.questions for page in question.source_pages]
    _validate_pages(cited_pages, document_text)
