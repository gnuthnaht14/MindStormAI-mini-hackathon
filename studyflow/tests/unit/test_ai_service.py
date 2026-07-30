from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from studyflow.models import StudyMaterial
from studyflow.services.ai_service import AIGenerationError, MissingAPIKeyError, generate_study_material


def material_fixture() -> StudyMaterial:
    questions = [
        {
            "type": "multiple_choice",
            "question": f"Câu hỏi kiểm tra số {index} là gì?",
            "options": [f"Đáp án {index}", "Phương án gây nhiễu"],
            "answer": f"Đáp án {index}",
            "explanation": "Giải thích dựa trên nội dung tài liệu.",
            "source_pages": [1],
        }
        for index in range(1, 6)
    ]
    return StudyMaterial(
        title="Bài học thử nghiệm",
        overview={
            "text": "Đây là tổng quan đủ dài để kiểm tra structured output trong unit test.",
            "source_pages": [1],
        },
        learning_objectives=[
            {"text": "Hiểu mục tiêu chính của bài học thử nghiệm.", "source_pages": [1]},
            {"text": "Áp dụng được nội dung chính vào câu hỏi.", "source_pages": [1]},
        ],
        key_concepts=[
            {
                "name": f"Khái niệm {index}",
                "simple_explanation": "Giải thích đơn giản và đủ dài cho khái niệm thử nghiệm.",
                "example": None,
                "source_pages": [1],
            }
            for index in range(1, 4)
        ],
        process_steps=[],
        common_misconceptions=[],
        takeaways=[
            {"text": f"Điều quan trọng cần nhớ số {index}.", "source_pages": [1]}
            for index in range(1, 4)
        ],
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
            "--- Trang 1 ---\nNội dung bài học đủ dài để tạo câu hỏi.",
            question_count=5,
            question_types=("multiple_choice",),
            model="gpt-5.6-sol",
            client=client,
        )
        self.assertEqual(result.title, "Bài học thử nghiệm")
        self.assertIs(client.responses.kwargs["text_format"], StudyMaterial)
        self.assertIn("đúng 5 câu hỏi", client.responses.kwargs["input"])
        self.assertIn("source_pages", client.responses.kwargs["input"])

    def test_generate_rejects_nonexistent_page_citation(self) -> None:
        material = material_fixture().model_copy(deep=True)
        material.overview.source_pages = [2]
        client = FakeClient(material)

        with self.assertRaisesRegex(AIGenerationError, "trang không tồn tại"):
            generate_study_material(
                "--- Trang 1 ---\nNội dung duy nhất của tài liệu.",
                question_count=5,
                question_types=("multiple_choice",),
                model="gpt-5.6-sol",
                client=client,
            )

    def test_generate_builds_openai_client(self) -> None:
        provider_client = Mock()
        provider_client.responses.parse.return_value = type(
            "FakeResponse", (), {"output_parsed": material_fixture()}
        )()
        with patch("studyflow.services.ai_service.OpenAI", return_value=provider_client) as factory:
            generate_study_material(
                "--- Trang 1 ---\nNội dung bài học dùng để kiểm tra OpenAI.",
                question_count=5,
                question_types=("multiple_choice",),
                api_key="sk-test",
                model="gpt-5.6-sol",
            )

        client_options = factory.call_args.kwargs
        self.assertEqual(client_options["api_key"], "sk-test")
        self.assertNotIn("base_url", client_options)

    def test_generate_requires_api_key_without_injected_client(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with self.assertRaises(MissingAPIKeyError):
                generate_study_material(
                    "Nội dung bài học.",
                    question_count=5,
                    question_types=("multiple_choice",),
                    api_key="",
                    model="gpt-5.6-sol",
                )

    def test_generate_rejects_question_type_outside_request(self) -> None:
        client = FakeClient(material_fixture())
        with self.assertRaisesRegex(AIGenerationError, "dạng câu hỏi không được yêu cầu"):
            generate_study_material(
                "--- Trang 1 ---\nNội dung bài học đủ dài.",
                question_count=5,
                question_types=("true_false",),
                model="gpt-5.6-sol",
                client=client,
            )


if __name__ == "__main__":
    unittest.main()
