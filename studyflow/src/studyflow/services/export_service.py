from __future__ import annotations

from studyflow.models import CitedPoint, KeyConcept, PDFExtraction, Question, QuizMaterial, SummaryMaterial


QUESTION_TYPE_LABELS = {
    "multiple_choice": "Trắc nghiệm",
    "true_false": "Đúng / Sai",
    "short_answer": "Tự luận ngắn",
}


def _citation(pages: list[int]) -> str:
    label = "trang " + ", ".join(str(page) for page in pages)
    return f"*Nguồn: {label}*"


def _cited_bullets(items: list[CitedPoint]) -> str:
    return "\n".join(f"- {item.text} — {_citation(item.source_pages)}" for item in items)


def _concept_markdown(concept: KeyConcept) -> str:
    lines = [
        f"### {concept.name}",
        concept.simple_explanation,
        "",
        _citation(concept.source_pages),
    ]
    if concept.example:
        lines.extend(["", f"**Ví dụ trong tài liệu:** {concept.example}"])
    return "\n".join(lines)


def _question_markdown(index: int, question: Question) -> str:
    lines = [
        f"### Câu {index}: {question.question}",
        f"*{QUESTION_TYPE_LABELS[question.type]}* · {_citation(question.source_pages)}",
    ]
    if question.options:
        lines.extend(f"- {option}" for option in question.options)
    lines.extend(["", f"**Đáp án:** {question.answer}", f"**Giải thích:** {question.explanation}"])
    return "\n".join(lines)


def _metadata(extraction: PDFExtraction | None) -> str:
    metadata = ""
    if extraction is not None:
        metadata = (
            f"> Nguồn: {extraction.filename} · {extraction.page_count} trang · "
            f"{extraction.character_count:,} ký tự\n\n"
        )
    return metadata.rstrip()


def build_summary_markdown(summary: SummaryMaterial, extraction: PDFExtraction | None = None) -> str:
    """Export only the generated summary artifact."""

    objectives = _cited_bullets(summary.learning_objectives)
    concepts = "\n\n".join(_concept_markdown(concept) for concept in summary.key_concepts)
    process = _cited_bullets(summary.process_steps)
    misconceptions = _cited_bullets(summary.common_misconceptions)
    takeaways = _cited_bullets(summary.takeaways)
    sections = [
        f"# {summary.title}",
        _metadata(extraction),
        "## Tổng quan 30 giây",
        f"{summary.overview.text}\n\n{_citation(summary.overview.source_pages)}",
        "## Mục tiêu học tập",
        objectives,
        "## Khái niệm trọng tâm",
        concepts,
    ]
    if process:
        sections.extend(["## Quy trình từng bước", process])
    if misconceptions:
        sections.extend(["## Điểm dễ nhầm", misconceptions])
    sections.extend(["## Điều cần nhớ", takeaways])
    return "\n\n".join(section for section in sections if section) + "\n"


def build_quiz_markdown(
    quiz: QuizMaterial,
    extraction: PDFExtraction | None = None,
    *,
    title: str = "Bộ câu hỏi ôn tập",
) -> str:
    """Export only the generated quiz artifact."""

    questions = "\n\n".join(
        _question_markdown(index, question) for index, question in enumerate(quiz.questions, start=1)
    )
    sections = [
        f"# {title}",
        _metadata(extraction),
        "## Câu hỏi ôn tập",
        questions,
    ]
    return "\n\n".join(section for section in sections if section) + "\n"
