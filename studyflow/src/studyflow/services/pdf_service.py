from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

import pymupdf

from studyflow.models import PDFExtraction, PageContent


DEFAULT_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_INPUT_CHARACTERS = 60_000
MIN_EXTRACTED_CHARACTERS = 40
LOW_TEXT_CHARACTER_THRESHOLD = 80


class PDFValidationError(ValueError):
    """Raised when an upload is not a valid MVP input."""


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot provide usable text or visual content."""


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


def render_page_to_png(page: pymupdf.Page, *, scale: float = 2.0) -> bytes:
    """Render one PDF page to PNG for OCR or visual analysis."""

    matrix = pymupdf.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False, colorspace=pymupdf.csRGB)
    return pixmap.tobytes("png")


def render_pdf_page_preview(file_bytes: bytes, page_number: int, *, scale: float = 1.6) -> bytes:
    """Render a one-based source page for the citation preview dialog."""

    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError("Không thể mở PDF để hiển thị trang nguồn.") from exc
    try:
        if page_number < 1 or page_number > document.page_count:
            raise PDFExtractionError(f"Trang nguồn {page_number} không tồn tại trong PDF.")
        return render_page_to_png(document.load_page(page_number - 1), scale=scale)
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError(f"Không thể hiển thị trang nguồn {page_number}.") from exc
    finally:
        document.close()


def _image_metrics(page: pymupdf.Page) -> tuple[int, float]:
    """Return raster image count and approximate covered page area."""

    try:
        image_info = page.get_image_info()
    except Exception:
        return 0, 0.0

    page_area = max(float(page.rect.width * page.rect.height), 1.0)
    covered_area = 0.0
    for item in image_info:
        bbox = item.get("bbox")
        if not bbox:
            continue
        clipped = pymupdf.Rect(bbox) & page.rect
        if not clipped.is_empty:
            covered_area += float(clipped.width * clipped.height)
    return len(image_info), min(covered_area / page_area, 1.0)


def _drawing_count(page: pymupdf.Page) -> int:
    try:
        return len(page.get_drawings())
    except Exception:
        return 0


def classify_page(
    *,
    text: str,
    image_count: int,
    drawing_count: int,
    image_coverage: float,
) -> Literal["text", "scanned", "mixed_visual", "diagram_or_chart"]:
    """Classify a page using deterministic, low-cost PDF signals."""

    text_length = len(text.strip())
    if text_length < LOW_TEXT_CHARACTER_THRESHOLD and image_coverage >= 0.45:
        return "scanned"
    if drawing_count >= 8 and text_length < 1_500:
        return "diagram_or_chart"
    if image_coverage >= 0.18 or image_count >= 2:
        return "mixed_visual"
    return "text"


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def run_local_ocr(image_bytes: bytes, *, languages: str = "vie+eng", timeout_seconds: int = 30) -> str:
    """Run optional local Tesseract OCR without adding a Python dependency."""

    executable = shutil.which("tesseract")
    if not executable:
        return ""

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    def execute(selected_languages: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [executable, "stdin", "stdout", "-l", selected_languages],
            input=image_bytes,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
            creationflags=creation_flags,
        )

    try:
        result = execute(languages)
        if result.returncode != 0 and "+" in languages:
            result = execute("eng")
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return _clean_page_text(result.stdout.decode("utf-8", errors="replace"))


def is_visual_candidate(page: PageContent) -> bool:
    return page.visual_type != "text"


def compose_document_text(
    page_contents: list[PageContent],
    *,
    max_characters: int = DEFAULT_MAX_INPUT_CHARACTERS,
) -> tuple[str, bool]:
    """Build grounded, page-labelled AI context from all extraction methods."""

    labelled_pages: list[str] = []
    for page in page_contents:
        sections: list[str] = []
        if page.text_layer:
            sections.append(page.text_layer)
        if page.ocr_text and page.ocr_text.casefold() not in page.text_layer.casefold():
            sections.append(f"VĂN BẢN OCR:\n{page.ocr_text}")
        if page.visual_summary:
            visual = f"MÔ TẢ HÌNH ẢNH:\n{page.visual_summary}"
            if page.visual_facts:
                visual += "\nCHI TIẾT NHÌN THẤY:\n- " + "\n- ".join(page.visual_facts)
            sections.append(visual)
        if not sections and is_visual_candidate(page):
            sections.append("[Trang có nội dung hình ảnh nhưng chưa phân tích được chi tiết.]")
        if sections:
            labelled_pages.append(f"--- Trang {page.page_number} ---\n" + "\n\n".join(sections))

    full_text = "\n\n".join(labelled_pages)
    return full_text[:max_characters], len(full_text) > max_characters


def extract_pdf_text(
    file_bytes: bytes,
    *,
    filename: str = "document.pdf",
    max_characters: int = DEFAULT_MAX_INPUT_CHARACTERS,
    enable_local_ocr: bool = True,
    ocr_languages: str = "vie+eng",
) -> PDFExtraction:
    """Extract text and cheap page-level visual signals from a PDF."""

    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError("Không thể mở PDF. File có thể bị hỏng hoặc được mã hóa.") from exc

    try:
        if document.needs_pass:
            raise PDFExtractionError("PDF đang được bảo vệ bằng mật khẩu.")
        if document.page_count < 1:
            raise PDFExtractionError("PDF không có trang nội dung.")

        page_contents: list[PageContent] = []
        total_characters = 0
        ocr_page_count = 0
        for page_index in range(document.page_count):
            try:
                page = document.load_page(page_index)
                page_text = _clean_page_text(page.get_text("text"))
                image_count, image_coverage = _image_metrics(page)
                drawing_count = _drawing_count(page)
            except Exception as exc:
                raise PDFExtractionError(f"Không thể đọc trang {page_index + 1} của PDF.") from exc

            visual_type = classify_page(
                text=page_text,
                image_count=image_count,
                drawing_count=drawing_count,
                image_coverage=image_coverage,
            )
            ocr_text = ""
            if (
                enable_local_ocr
                and len(page_text) < LOW_TEXT_CHARACTER_THRESHOLD
                and visual_type != "text"
                and tesseract_available()
            ):
                ocr_text = run_local_ocr(render_page_to_png(page), languages=ocr_languages)
                if ocr_text:
                    ocr_page_count += 1

            total_characters += len(page_text) + len(ocr_text)
            page_contents.append(
                PageContent(
                    page_number=page_index + 1,
                    text_layer=page_text,
                    ocr_text=ocr_text,
                    visual_type=visual_type,
                    image_count=image_count,
                    drawing_count=drawing_count,
                    image_coverage=image_coverage,
                    analysis_method="ocr" if ocr_text else "text",
                    confidence=0.75 if ocr_text else 1.0,
                )
            )

        visual_candidates = [page.page_number for page in page_contents if is_visual_candidate(page)]
        if total_characters < MIN_EXTRACTED_CHARACTERS and not visual_candidates:
            raise PDFExtractionError(
                "Không trích xuất được chữ hoặc hình ảnh có thể xử lý từ PDF này."
            )

        processed_text, was_truncated = compose_document_text(
            page_contents,
            max_characters=max_characters,
        )
        return PDFExtraction(
            filename=filename,
            text=processed_text,
            page_count=document.page_count,
            character_count=total_characters,
            processed_characters=len(processed_text),
            page_texts=[page.text_layer or page.ocr_text for page in page_contents],
            page_contents=page_contents,
            visual_candidate_pages=visual_candidates,
            ocr_page_count=ocr_page_count,
            was_truncated=was_truncated,
        )
    finally:
        document.close()
