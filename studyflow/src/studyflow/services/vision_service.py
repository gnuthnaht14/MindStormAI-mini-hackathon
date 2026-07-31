from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path
from typing import Any

import pymupdf
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from studyflow.models import PDFExtraction, PageContent, PageVisualAnalysis
from studyflow.services.ai_service import MissingAPIKeyError, create_openai_client
from studyflow.services.pdf_service import compose_document_text, render_page_to_png


VISION_PROMPT_VERSION = "slide-page-v1"
VISION_INSTRUCTIONS = """Bạn đọc một trang slide bài giảng từ hình ảnh.
Chỉ mô tả thông tin thực sự nhìn thấy trên trang; không bổ sung kiến thức bên ngoài.
Ưu tiên giải thích quan hệ trong sơ đồ, xu hướng trong biểu đồ, cấu trúc bảng và ý nghĩa của ảnh minh họa.
Nếu chi tiết mờ hoặc không chắc chắn, nói rõ mức độ không chắc chắn thay vì đoán.
Trả lời bằng tiếng Việt và đúng schema được yêu cầu."""


class VisualAnalysisError(RuntimeError):
    """Raised when visual content cannot be prepared for downstream AI."""


def _page_priority(page: PageContent) -> float:
    type_score = {
        "scanned": 3.0,
        "diagram_or_chart": 2.5,
        "mixed_visual": 2.0,
        "text": 0.0,
    }[page.visual_type]
    low_text_bonus = max(0.0, 1.0 - len(page.text_layer) / 500)
    return type_score + page.image_coverage + low_text_bonus


def select_visual_pages(page_contents: list[PageContent], *, max_pages: int) -> list[PageContent]:
    """Choose the pages most likely to lose meaning with text extraction alone."""

    if max_pages <= 0:
        return []
    scanned = sorted(
        (page for page in page_contents if page.visual_type == "scanned"),
        key=lambda page: (-_page_priority(page), page.page_number),
    )
    diagrams = sorted(
        (page for page in page_contents if page.visual_type == "diagram_or_chart"),
        key=lambda page: (-_page_priority(page), page.page_number),
    )
    mixed = sorted(
        (page for page in page_contents if page.visual_type == "mixed_visual"),
        key=lambda page: (-_page_priority(page), page.page_number),
    )

    selected = scanned[:max_pages]
    remaining_slots = max_pages - len(selected)
    if remaining_slots and diagrams and mixed:
        reserved_each = max(1, (remaining_slots * 2) // 5)
        selected.extend(diagrams[:reserved_each])
        selected.extend(mixed[:reserved_each])

    selected_numbers = {page.page_number for page in selected}
    remainder = sorted(
        [
            page
            for page in [*scanned, *diagrams, *mixed]
            if page.page_number not in selected_numbers
        ],
        key=lambda page: (-_page_priority(page), page.page_number),
    )
    selected.extend(remainder[: max_pages - len(selected)])
    return sorted(selected[:max_pages], key=lambda page: page.page_number)


def _safe_model_slug(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", model).strip("-") or "model"


def _cache_path(
    cache_dir: Path,
    *,
    pdf_hash: str,
    page_number: int,
    model: str,
    detail: str,
    image_bytes: bytes,
) -> Path:
    fingerprint = hashlib.sha256(
        b"|".join(
            [
                VISION_PROMPT_VERSION.encode(),
                model.encode(),
                detail.encode(),
                hashlib.sha256(image_bytes).digest(),
            ]
        )
    ).hexdigest()[:16]
    return cache_dir / pdf_hash / f"page-{page_number:04d}-{_safe_model_slug(model)}-{fingerprint}.json"


def _read_cache(path: Path) -> PageVisualAnalysis | None:
    try:
        return PageVisualAnalysis.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cache(path: Path, result: PageVisualAnalysis) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    temporary_path.replace(path)


def analyze_page_image(
    image_bytes: bytes,
    *,
    page: PageContent,
    model: str,
    detail: str = "low",
    client: Any,
) -> PageVisualAnalysis:
    """Analyze one rendered page through the Responses API."""

    safe_detail = detail if detail in {"low", "high", "original", "auto"} else "low"
    known_text = page.text_layer[:2_000] or page.ocr_text[:2_000] or "(không có text layer)"
    prompt = f"""Phân tích trang {page.page_number} của slide.
Loại trang được rule-base nhận diện: {page.visual_type}.
Văn bản đã đọc được (có thể thiếu):
{known_text}

Hãy trả về:
- visual_summary: diễn giải ngắn nội dung hình ảnh và quan hệ quan trọng.
- visible_text: chữ quan trọng nhìn thấy nhưng chưa có trong phần văn bản trên.
- important_facts: các dữ kiện trực tiếp đọc được từ biểu đồ, bảng hoặc sơ đồ.
- confidence: low/medium/high."""
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    try:
        response = client.responses.parse(
            model=model,
            instructions=VISION_INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{encoded_image}",
                            "detail": safe_detail,
                        },
                    ],
                }
            ],
            text_format=PageVisualAnalysis,
            max_output_tokens=1_000,
            store=False,
            **(
                {"text": {"verbosity": "low"}, "reasoning": {"effort": "low"}}
                if model.startswith("gpt-5")
                else {}
            ),
        )
    except APITimeoutError as exc:
        raise VisualAnalysisError("Vision phản hồi quá chậm.") from exc
    except RateLimitError as exc:
        raise VisualAnalysisError("Vision đang quá tải hoặc chạm giới hạn sử dụng.") from exc
    except APIConnectionError as exc:
        raise VisualAnalysisError("Không thể kết nối đến dịch vụ Vision.") from exc
    except APIStatusError as exc:
        raise VisualAnalysisError(f"Vision từ chối yêu cầu (mã {exc.status_code}).") from exc
    except Exception as exc:
        raise VisualAnalysisError("Vision không trả về kết quả hợp lệ.") from exc

    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise VisualAnalysisError("Vision không trả về nội dung có cấu trúc.")
    return parsed


def _merge_analysis(page: PageContent, analysis: PageVisualAnalysis) -> PageContent:
    confidence = {"low": 0.5, "medium": 0.75, "high": 0.9}[analysis.confidence]
    ocr_text = page.ocr_text
    if not ocr_text and len(page.text_layer) < 80:
        ocr_text = analysis.visible_text
    if page.ocr_text:
        method = "ocr+vision"
    elif page.text_layer:
        method = "text+vision"
    else:
        method = "vision"
    return page.model_copy(
        update={
            "ocr_text": ocr_text,
            "visual_summary": analysis.visual_summary,
            "visual_facts": analysis.important_facts,
            "analysis_method": method,
            "confidence": confidence,
        }
    )


def enrich_pdf_visuals(
    file_bytes: bytes,
    extraction: PDFExtraction,
    *,
    api_key: str | None = None,
    model: str,
    cache_dir: Path,
    max_pages: int = 8,
    detail: str = "low",
    max_characters: int = 60_000,
    client: Any | None = None,
) -> PDFExtraction:
    """Enrich only high-value visual pages and reuse a disk cache across flows."""

    if not extraction.page_contents or max_pages <= 0:
        return extraction

    selected_pages = select_visual_pages(extraction.page_contents, max_pages=max_pages)
    if not selected_pages:
        return extraction

    pdf_hash = hashlib.sha256(file_bytes).hexdigest()
    pages_by_number = {page.page_number: page for page in extraction.page_contents}
    warnings = list(extraction.visual_warnings)
    resolved_client = client

    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise VisualAnalysisError("Không thể render PDF để đọc hình ảnh.") from exc

    try:
        for selected in selected_pages:
            try:
                image_bytes = render_page_to_png(document.load_page(selected.page_number - 1))
            except Exception:
                warnings.append(f"Trang {selected.page_number}: không thể render ảnh để phân tích.")
                continue
            cache_path = _cache_path(
                cache_dir,
                pdf_hash=pdf_hash,
                page_number=selected.page_number,
                model=model,
                detail=detail,
                image_bytes=image_bytes,
            )
            analysis = _read_cache(cache_path)
            if analysis is None:
                if resolved_client is None:
                    resolved_client = create_openai_client(api_key)
                try:
                    analysis = analyze_page_image(
                        image_bytes,
                        page=selected,
                        model=model,
                        detail=detail,
                        client=resolved_client,
                    )
                    try:
                        _write_cache(cache_path, analysis)
                    except OSError:
                        warnings.append(
                            f"Trang {selected.page_number}: đã đọc được ảnh nhưng không ghi được cache."
                        )
                except VisualAnalysisError as exc:
                    warnings.append(f"Trang {selected.page_number}: {exc}")
                    continue
            pages_by_number[selected.page_number] = _merge_analysis(selected, analysis)
    finally:
        document.close()

    enriched_pages = [pages_by_number[number] for number in sorted(pages_by_number)]
    processed_text, was_truncated = compose_document_text(
        enriched_pages,
        max_characters=max_characters,
    )
    vision_page_count = sum("vision" in page.analysis_method for page in enriched_pages)
    if len(extraction.visual_candidate_pages) > len(selected_pages):
        skipped = len(extraction.visual_candidate_pages) - len(selected_pages)

    usable_characters = sum(
        len(page.text_layer) + len(page.ocr_text) + len(page.visual_summary)
        for page in enriched_pages
    )
    if usable_characters < 40:
        if resolved_client is None and not api_key:
            raise MissingAPIKeyError("Hệ thống cần OPENAI_API_KEY để đọc PDF dạng hình ảnh.")
        raise VisualAnalysisError("Không đọc được đủ nội dung chữ hoặc hình ảnh để tạo tài liệu học tập.")

    return extraction.model_copy(
        update={
            "text": processed_text,
            "processed_characters": len(processed_text),
            "page_texts": [page.text_layer or page.ocr_text for page in enriched_pages],
            "page_contents": enriched_pages,
            "vision_page_count": vision_page_count,
            "visual_warnings": warnings,
            "was_truncated": was_truncated,
        }
    )
