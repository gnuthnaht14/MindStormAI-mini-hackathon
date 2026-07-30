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


class FakeCompletions:
    def __init__(self, material: StudyMaterial) -> None:
        self.material = material
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        message = type("FakeMessage", (), {"parsed": self.material})()
        return type("FakeResponse", (), {"choices": [type("FakeChoice", (), {"message": message})()]})()


class FakeChat:
    def __init__(self, material: StudyMaterial) -> None:
        self.completions = FakeCompletions(material)


class FakeClient:
    def __init__(self, material: StudyMaterial) -> None:
        self.chat = FakeChat(material)


class AIServiceTests(unittest.TestCase):
    def test_generate_uses_one_structured_chat_call(self) -> None:
        client = FakeClient(material_fixture())
        result = generate_study_material(
            "Nội dung bài học đủ dài để tạo câu hỏi.",
            question_count=5,
            question_types=("short_answer",),
            model="openai/gpt-4o-mini",
            client=client,
        )
        self.assertEqual(result.title, "Bài học thử nghiệm")
        self.assertIs(client.chat.completions.kwargs["response_format"], StudyMaterial)
        user_msgs = [m for m in client.chat.completions.kwargs["messages"] if m["role"] == "user"]
        self.assertTrue(any("đúng 5 câu hỏi" in m["content"] for m in user_msgs))

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
