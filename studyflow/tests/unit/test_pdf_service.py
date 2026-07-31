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


def make_multi_page_pdf(pages: list[str]) -> bytes:
    document = pymupdf.open()
    for body in pages:
        page = document.new_page()
        if body:
            page.insert_text((72, 72), body)
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

    def test_extract_strips_repeated_header_and_page_numbers(self) -> None:
        pages = [
            "STUDYFLOW SLIDE 1\nOverview of the onboarding program and its happy path.\n1",
            "STUDYFLOW SLIDE 2\nOnboarding steps include login and joining the server.\n2",
            "STUDYFLOW SLIDE 3\nWorking principles split issues with clear owners.\n3",
        ]
        result = extract_pdf_text(make_multi_page_pdf(pages), filename="slides.pdf")
        self.assertNotIn("STUDYFLOW", result.text)
        self.assertNotIn("\n1\n", result.text)
        self.assertIn("Overview of the onboarding", result.text)
        self.assertIn("Onboarding steps include", result.text)

    def test_extract_preserves_page_texts_for_ui_while_filtering_ai_text(self) -> None:
        pages = [
            "STUDYFLOW SLIDE 1\nImportant academic content that must be retained here.\n1",
            "STUDYFLOW SLIDE 2\nThinking is indirect and abstract reflection of reality.\n2",
        ]
        result = extract_pdf_text(make_multi_page_pdf(pages), filename="slides.pdf")
        self.assertTrue(any("STUDYFLOW" in pt for pt in result.page_texts))
        self.assertTrue(any("SLIDE 2" in pt for pt in result.page_texts))
        self.assertNotIn("STUDYFLOW", result.text)

    def test_extract_drops_boilerplate_closing_pages_from_ai_text(self) -> None:
        pages = [
            "STUDYFLOW SLIDE 1\nCore knowledge about neural networks and basics here.\n1",
            "Thank you\n2",
        ]
        result = extract_pdf_text(make_multi_page_pdf(pages), filename="slides.pdf")
        self.assertNotIn("Thank you", result.text)
        self.assertIn("Core knowledge about", result.text)

    def test_extract_keeps_single_page_without_false_header_removal(self) -> None:
        body = "StudyFlow demo lesson with enough extractable text for validation."
        result = extract_pdf_text(make_pdf(body), filename="one.pdf")
        self.assertIn(body, result.text)


if __name__ == "__main__":
    unittest.main()
