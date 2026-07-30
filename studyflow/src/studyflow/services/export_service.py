from __future__ import annotations

from studyflow.models import CitedPoint, KeyConcept, PDFExtraction, Question, StudyMaterial


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


def build_markdown(material: StudyMaterial, extraction: PDFExtraction | None = None) -> str:
    """Convert generated study content to a portable Markdown document."""

    metadata = ""
    if extraction is not None:
        metadata = (
            f"> Nguồn: {extraction.filename} · {extraction.page_count} trang · "
            f"{extraction.character_count:,} ký tự\n\n"
        )
    objectives = _cited_bullets(material.learning_objectives)
    concepts = "\n\n".join(_concept_markdown(concept) for concept in material.key_concepts)
    process = _cited_bullets(material.process_steps)
    misconceptions = _cited_bullets(material.common_misconceptions)
    takeaways = _cited_bullets(material.takeaways)
    questions = "\n\n".join(
        _question_markdown(index, question) for index, question in enumerate(material.questions, start=1)
    )
    sections = [
        f"# {material.title}",
        metadata.rstrip(),
        "## Tổng quan 30 giây",
        f"{material.overview.text}\n\n{_citation(material.overview.source_pages)}",
        "## Mục tiêu học tập",
        objectives,
        "## Khái niệm trọng tâm",
        concepts,
    ]
    if process:
        sections.extend(["## Quy trình từng bước", process])
    if misconceptions:
        sections.extend(["## Điểm dễ nhầm", misconceptions])
    sections.extend(["## Điều cần nhớ", takeaways, "## Câu hỏi ôn tập", questions])
    return "\n\n".join(section for section in sections if section) + "\n"
