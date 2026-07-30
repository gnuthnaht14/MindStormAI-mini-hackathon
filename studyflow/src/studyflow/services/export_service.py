from __future__ import annotations

from studyflow.models import PDFExtraction, Question, StudyMaterial


QUESTION_TYPE_LABELS = {
    "multiple_choice": "Trắc nghiệm",
    "true_false": "Đúng / Sai",
    "short_answer": "Tự luận ngắn",
}


def _question_markdown(index: int, question: Question) -> str:
    lines = [f"### Câu {index}: {question.question}", f"*{QUESTION_TYPE_LABELS[question.type]}*"]
    if question.options:
        lines.extend(f"- {option}" for option in question.options)
    lines.extend(["", f"**Đáp án:** {question.answer}", f"**Giải thích:** {question.explanation}"])
    return "\n".join(lines)


def build_markdown(material: StudyMaterial, extraction: PDFExtraction | None = None) -> str:
    """Convert generated study content to a portable Markdown document."""

    metadata = ""
    if extraction is not None:
        metadata = (
            f"> Nguồn: {extraction.filename} · {extraction.page_count} trang · "
            f"{extraction.character_count:,} ký tự\n\n"
        )
    key_points = "\n".join(f"- {item}" for item in material.key_points)
    questions = "\n\n".join(
        _question_markdown(index, question) for index, question in enumerate(material.questions, start=1)
    )
    return (
        f"# {material.title}\n\n{metadata}## Tóm tắt\n\n{material.summary}\n\n"
        f"## Ý chính\n\n{key_points}\n\n## Câu hỏi ôn tập\n\n{questions}\n"
    )
