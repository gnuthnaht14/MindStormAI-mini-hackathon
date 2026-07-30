from __future__ import annotations

import unittest
from unittest.mock import patch

from studyflow.models import StudyMaterial
from studyflow.services.ai_service import MissingAPIKeyError, generate_study_material


def material_fixture() -> StudyMaterial:
    questions = [
        {
            "type": "short_answer",
            "question": f"Câu hỏi kiểm tra số {index} là gì?",
            "options": [],
            "answer": f"Đáp án {index}",
            "explanation": "Giải thích dựa trên nội dung tài liệu.",
        }
        for index in range(1, 6)
    ]
    return StudyMaterial(
        title="Bài học thử nghiệm",
        summary="Đây là bản tóm tắt đủ dài để kiểm tra structured output trong unit test.",
        key_points=["Ý chính một", "Ý chính hai", "Ý chính ba"],
        questions=questions,
    )


class FakeResponses:
    def __init__(self, material: StudyMaterial) -> None:
        self.material = material
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return type("FakeResponse", (), {"output_parsed": self.material})()


class FakeClient:
    def __init__(self, material: StudyMaterial) -> None:
        self.responses = FakeResponses(material)


class AIServiceTests(unittest.TestCase):
    def test_generate_uses_one_structured_responses_call(self) -> None:
        client = FakeClient(material_fixture())
        result = generate_study_material(
            "Nội dung bài học đủ dài để tạo câu hỏi.",
            question_count=5,
            question_types=("short_answer",),
            model="gpt-5.6-sol",
            client=client,
        )
        self.assertEqual(result.title, "Bài học thử nghiệm")
        self.assertIs(client.responses.kwargs["text_format"], StudyMaterial)
        self.assertIn("đúng 5 câu hỏi", client.responses.kwargs["input"])

    def test_generate_requires_api_key_without_injected_client(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with self.assertRaises(MissingAPIKeyError):
                generate_study_material(
                    "Nội dung bài học.",
                    question_count=5,
                    question_types=("short_answer",),
                    api_key="",
                    model="gpt-5.6-sol",
                )


if __name__ == "__main__":
    unittest.main()
