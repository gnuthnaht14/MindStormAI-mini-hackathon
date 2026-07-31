from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from studyflow.models import PageVisualAnalysis
from studyflow.services.pdf_service import extract_pdf_text
from studyflow.services.vision_service import enrich_pdf_visuals
from tests.unit.test_pdf_service import make_image_only_pdf


class FakeResponses:
    def __init__(self) -> None:
        self.call_count = 0
        self.kwargs = None

    def parse(self, **kwargs):
        self.call_count += 1
        self.kwargs = kwargs
        parsed = PageVisualAnalysis(
            visual_summary="Sơ đồ thể hiện dữ liệu đầu vào đi qua bộ xử lý để tạo kết quả học tập.",
            visible_text="Input, Processor, Output",
            important_facts=["Luồng đi từ Input đến Processor rồi tới Output."],
            confidence="high",
        )
        return type("FakeResponse", (), {"output_parsed": parsed})()


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class VisionServiceTests(unittest.TestCase):
    def test_enriches_visual_page_and_reuses_disk_cache(self) -> None:
        file_bytes = make_image_only_pdf()
        extraction = extract_pdf_text(file_bytes, filename="visual.pdf", enable_local_ocr=False)

        with tempfile.TemporaryDirectory() as directory:
            first_client = FakeClient()
            enriched = enrich_pdf_visuals(
                file_bytes,
                extraction,
                model="gpt-test-vision",
                cache_dir=Path(directory),
                max_pages=2,
                client=first_client,
            )
            self.assertEqual(first_client.responses.call_count, 1)
            self.assertEqual(enriched.vision_page_count, 1)
            self.assertIn("MÔ TẢ HÌNH ẢNH", enriched.text)
            self.assertIn("Sơ đồ thể hiện", enriched.text)
            image_input = first_client.responses.kwargs["input"][0]["content"][1]
            self.assertTrue(image_input["image_url"].startswith("data:image/png;base64,"))
            self.assertEqual(image_input["detail"], "low")

            second_client = FakeClient()
            cached = enrich_pdf_visuals(
                file_bytes,
                extraction,
                model="gpt-test-vision",
                cache_dir=Path(directory),
                max_pages=2,
                client=second_client,
            )
            self.assertEqual(second_client.responses.call_count, 0)
            self.assertEqual(cached.page_contents[0].visual_summary, enriched.page_contents[0].visual_summary)


if __name__ == "__main__":
    unittest.main()
