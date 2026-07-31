from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pymupdf

from studyflow.models import PDFExtraction


DEFAULT_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_INPUT_CHARACTERS = 60_000
MIN_EXTRACTED_CHARACTERS = 40

_PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")
_NOISE_LINE_RE = re.compile(r"^[\s•·▪◦・\-*=]+$")
_BOILERPLATE_KEYWORDS = (
    "thank you",
    "cảm ơn",
    "q&a",
    "questions?",
    "hỏi đáp",
    "kết thúc",
    "the end",
)
_BOILERPLATE_MAX_BODY = 20
_HEADER_REPEAT_THRESHOLD = 0.6


class PDFValidationError(ValueError):
    """Raised when an upload is not a valid MVP input."""


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot provide usable text."""


def validate_pdf(
    *,
    filename: str,
    file_bytes: bytes,
    mime_type: str | None = None,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> None:
    """Raise a user-facing validation error for an unsupported upload."""

    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise PDFValidationError("Chỉ hỗ trợ file PDF trong phiên bản MVP.")
    if not file_bytes:
        raise PDFValidationError("File PDF đang rỗng. Vui lòng chọn file khác.")
    if len(file_bytes) > max_size_bytes:
        limit_mb = max_size_bytes // (1024 * 1024)
        raise PDFValidationError(f"File vượt quá giới hạn {limit_mb} MB của bản demo.")
    if not file_bytes.lstrip().startswith(b"%PDF-"):
        raise PDFValidationError("File không có định dạng PDF hợp lệ.")
    if mime_type and mime_type not in {"application/pdf", "application/octet-stream"}:
        raise PDFValidationError("Chỉ hỗ trợ file PDF trong phiên bản MVP.")


def _clean_page_text(text: str) -> str:
    lines: list[str] = []
    previous: str | None = None
    for raw_line in text.replace("\x00", " ").splitlines():
        line = re.sub(r"[\t ]+", " ", raw_line).strip()
        if not line or line == previous:
            continue
        lines.append(line)
        previous = line
    return "\n".join(lines)


def _normalize_header_line(line: str) -> str:
    """Collapse runs of digits so page-varying headers share one template."""
    return re.sub(r"\d+", "{N}", line.strip())


def _detect_repeated_header(page_texts: list[str]) -> str | None:
    """Return the header template repeated across at least the threshold of pages."""
    first_lines: list[str] = []
    for page_text in page_texts:
        if not page_text:
            continue
        first_line = page_text.split("\n", 1)[0].strip()
        if first_line:
            first_lines.append(_normalize_header_line(first_line))
    if len(first_lines) < 2:
        return None
    template, count = Counter(first_lines).most_common(1)[0]
    if count < 2 or count / len(first_lines) < _HEADER_REPEAT_THRESHOLD:
        return None
    return template


def _is_boilerplate_page(body: str) -> bool:
    """True when a page carries only a closing/boilerplate marker."""
    stripped = body.strip()
    if not stripped:
        return True
    if len(stripped) < _BOILERPLATE_MAX_BODY:
        lowered = stripped.lower()
        if any(keyword in lowered for keyword in _BOILERPLATE_KEYWORDS):
            return True
    return False


def _filter_page_for_ai(page_text: str, header_template: str | None) -> str:
    """Drop per-page noise (header, page number, divider lines) before sending to AI."""
    lines = page_text.split("\n") if page_text else []
    start = 0
    if header_template and lines and _normalize_header_line(lines[0]) == header_template:
        start = 1
    kept: list[str] = []
    for line in lines[start:]:
        if _PAGE_NUMBER_RE.match(line):
            continue
        if _NOISE_LINE_RE.match(line):
            continue
        kept.append(line)
    return "\n".join(kept)


def extract_pdf_text(
    file_bytes: bytes,
    *,
    filename: str = "document.pdf",
    max_characters: int = DEFAULT_MAX_INPUT_CHARACTERS,
) -> PDFExtraction:
    """Extract page-labelled text from a PDF and cap the AI input size."""

    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError("Không thể mở PDF. File có thể bị hỏng hoặc được mã hóa.") from exc

    try:
        if document.needs_pass:
            raise PDFExtractionError("PDF đang được bảo vệ bằng mật khẩu.")
        if document.page_count < 1:
            raise PDFExtractionError("PDF không có trang nội dung.")

        page_texts: list[str] = []
        labelled_pages: list[str] = []
        total_characters = 0
        for page_index in range(document.page_count):
            try:
                page_text = _clean_page_text(document.load_page(page_index).get_text("text"))
            except Exception as exc:
                raise PDFExtractionError(f"Không thể đọc trang {page_index + 1} của PDF.") from exc
            page_texts.append(page_text)
            if page_text:
                total_characters += len(page_text)
                labelled_pages.append(f"--- Trang {page_index + 1} ---\n{page_text}")

        full_text = "\n\n".join(labelled_pages)
        if len(full_text.strip()) < MIN_EXTRACTED_CHARACTERS:
            raise PDFExtractionError(
                "Không trích xuất được đủ chữ. PDF có thể là slide dạng ảnh; bản MVP chưa hỗ trợ OCR."
            )

        header_template = _detect_repeated_header(page_texts)
        ai_pages: list[str] = []
        for index, page_text in enumerate(page_texts, start=1):
            if not page_text:
                continue
            filtered = _filter_page_for_ai(page_text, header_template)
            if _is_boilerplate_page(filtered):
                continue
            if filtered.strip():
                ai_pages.append(f"--- Trang {index} ---\n{filtered}")
        ai_text = "\n\n".join(ai_pages) or full_text

        processed_text = ai_text[:max_characters]
        return PDFExtraction(
            filename=filename,
            text=processed_text,
            page_count=document.page_count,
            character_count=total_characters,
            processed_characters=len(processed_text),
            page_texts=page_texts,
            was_truncated=len(ai_text) > max_characters,
        )
    finally:
        document.close()
