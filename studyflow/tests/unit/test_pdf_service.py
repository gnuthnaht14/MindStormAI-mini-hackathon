from __future__ import annotations

import unittest

import pymupdf

from studyflow.services.pdf_service import (
    PDFExtractionError,
    PDFValidationError,
    extract_pdf_text,
    render_pdf_page_preview,
    validate_pdf,
)


def make_pdf(text: str = "StudyFlow demo lesson with enough extractable text for validation.") -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def make_image_only_pdf() -> bytes:
    source = pymupdf.open()
    source_page = source.new_page(width=600, height=400)
    source_page.insert_text((80, 180), "A visual-only lecture slide rendered as an image", fontsize=20)
    image_bytes = source_page.get_pixmap(alpha=False).tobytes("png")
    source.close()

    document = pymupdf.open()
    page = document.new_page(width=600, height=400)
    page.insert_image(page.rect, stream=image_bytes)
    content = document.tobytes()
    document.close()
    return content


class PDFServiceTests(unittest.TestCase):
    def test_validate_accepts_a_real_pdf(self) -> None:
        validate_pdf(filename="lesson.pdf", file_bytes=make_pdf(), mime_type="application/pdf")

    def test_validate_rejects_wrong_extension(self) -> None:
        with self.assertRaises(PDFValidationError):
            validate_pdf(filename="lesson.txt", file_bytes=make_pdf())

    def test_validate_rejects_oversized_file(self) -> None:
        with self.assertRaises(PDFValidationError):
            validate_pdf(filename="lesson.pdf", file_bytes=b"%PDF-12345", max_size_bytes=5)

    def test_extract_returns_page_labels_and_metrics(self) -> None:
        result = extract_pdf_text(make_pdf(), filename="lesson.pdf")
        self.assertEqual(result.page_count, 1)
        self.assertIn("--- Trang 1 ---", result.text)
        self.assertGreater(result.character_count, 40)

    def test_extract_rejects_image_only_or_empty_pdf(self) -> None:
        with self.assertRaises(PDFExtractionError):
            extract_pdf_text(make_pdf(""), filename="empty.pdf")

    def test_extract_accepts_image_only_pdf_as_visual_candidate(self) -> None:
        result = extract_pdf_text(make_image_only_pdf(), filename="visual.pdf", enable_local_ocr=False)
        self.assertEqual(result.character_count, 0)
        self.assertEqual(result.visual_candidate_pages, [1])
        self.assertEqual(result.page_contents[0].visual_type, "scanned")
        self.assertIn("--- Trang 1 ---", result.text)

    def test_renders_one_based_source_page_preview(self) -> None:
        image_bytes = render_pdf_page_preview(make_pdf(), 1)
        self.assertTrue(image_bytes.startswith(b"\x89PNG"))

    def test_rejects_missing_source_page_preview(self) -> None:
        with self.assertRaises(PDFExtractionError):
            render_pdf_page_preview(make_pdf(), 2)


if __name__ == "__main__":
    unittest.main()
