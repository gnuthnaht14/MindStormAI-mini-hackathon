from __future__ import annotations

import unittest

import pymupdf

from studyflow.services.pdf_service import (
    PDFExtractionError,
    PDFValidationError,
    extract_pdf_text,
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


if __name__ == "__main__":
    unittest.main()
