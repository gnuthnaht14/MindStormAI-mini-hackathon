from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from studyflow.models import QuizMaterial, SummaryMaterial
from studyflow.services.ai_service import (
    AIGenerationError,
    MissingAPIKeyError,
    generate_quiz,
    generate_summary,
)


def summary_fixture() -> SummaryMaterial:
    return SummaryMaterial(
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
    )


def quiz_fixture() -> QuizMaterial:
    return QuizMaterial(
        questions=[
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
    )


class FakeResponses:
    def __init__(self, parsed) -> None:
        self.parsed = parsed
        self.kwargs = None
        self.call_count = 0

    def parse(self, **kwargs):
        self.kwargs = kwargs
        self.call_count += 1
        return type("FakeResponse", (), {"output_parsed": self.parsed})()


class FakeClient:
    def __init__(self, parsed) -> None:
        self.responses = FakeResponses(parsed)


class AIServiceTests(unittest.TestCase):
    def test_summary_call_uses_only_summary_schema(self) -> None:
        client = FakeClient(summary_fixture())
        result = generate_summary(
            "--- Trang 1 ---\nNội dung bài học.", model="gpt-5.6-sol", client=client
        )
        self.assertEqual(result.title, "Bài học thử nghiệm")
        self.assertEqual(client.responses.call_count, 1)
        self.assertIs(client.responses.kwargs["text_format"], SummaryMaterial)
        self.assertIn("Không tạo câu hỏi hoặc quiz", client.responses.kwargs["input"])

    def test_quiz_call_uses_only_quiz_schema(self) -> None:
        client = FakeClient(quiz_fixture())
        result = generate_quiz(
            "--- Trang 1 ---\nNội dung bài học.",
            question_count=5,
            question_types=("multiple_choice",),
            model="gpt-5.6-sol",
            client=client,
        )
        self.assertEqual(len(result.questions), 5)
        self.assertEqual(client.responses.call_count, 1)
        self.assertIs(client.responses.kwargs["text_format"], QuizMaterial)
        self.assertIn("Không tạo summary", client.responses.kwargs["input"])

    def test_summary_rejects_nonexistent_page_citation(self) -> None:
        summary = summary_fixture().model_copy(deep=True)
        summary.overview.source_pages = [2]
        with self.assertRaisesRegex(AIGenerationError, "trang không tồn tại"):
            generate_summary("--- Trang 1 ---\nNội dung.", client=FakeClient(summary))

    def test_quiz_rejects_question_type_outside_request(self) -> None:
        with self.assertRaisesRegex(AIGenerationError, "dạng câu hỏi không được yêu cầu"):
            generate_quiz(
                "--- Trang 1 ---\nNội dung.",
                question_count=5,
                question_types=("true_false",),
                client=FakeClient(quiz_fixture()),
            )

    def test_generate_requires_api_key_without_injected_client(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with self.assertRaises(MissingAPIKeyError):
                generate_summary("Nội dung bài học.", api_key="", model="gpt-5.6-sol")

    def test_generate_builds_openai_client(self) -> None:
        provider_client = Mock()
        provider_client.responses.parse.return_value = type(
            "FakeResponse", (), {"output_parsed": summary_fixture()}
        )()
        with patch("studyflow.services.ai_service.OpenAI", return_value=provider_client) as factory:
            generate_summary(
                "--- Trang 1 ---\nNội dung bài học.", api_key="sk-test", model="gpt-5.6-sol"
            )
        self.assertEqual(factory.call_args.kwargs["api_key"], "sk-test")
        self.assertNotIn("base_url", factory.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
