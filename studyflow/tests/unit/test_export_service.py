from __future__ import annotations

import unittest

from studyflow.models import QuizMaterial, SummaryMaterial
from studyflow.services.export_service import build_quiz_markdown, build_summary_markdown


class ExportServiceTests(unittest.TestCase):
    def test_summary_export_does_not_contain_quiz(self) -> None:
        summary = SummaryMaterial(
            title="Demo title",
            overview={
                "text": "Bản tổng quan đủ dài để vượt qua validation của schema SummaryMaterial.",
                "source_pages": [1],
            },
            learning_objectives=[
                {"text": "Hiểu được mục tiêu quan trọng đầu tiên.", "source_pages": [1]},
                {"text": "Áp dụng được mục tiêu quan trọng thứ hai.", "source_pages": [2]},
            ],
            key_concepts=[
                {
                    "name": f"Khái niệm {index}",
                    "simple_explanation": "Giải thích đơn giản và đủ dài cho khái niệm đang được kiểm tra.",
                    "example": None,
                    "source_pages": [index],
                }
                for index in range(1, 4)
            ],
            process_steps=[],
            common_misconceptions=[],
            takeaways=[
                {"text": f"Điều quan trọng cần nhớ số {index}.", "source_pages": [index]}
                for index in range(1, 4)
            ],
        )
        markdown = build_summary_markdown(summary)
        self.assertIn("## Tổng quan 30 giây", markdown)
        self.assertNotIn("## Câu hỏi ôn tập", markdown)

    def test_quiz_export_does_not_contain_summary(self) -> None:
        quiz = QuizMaterial(
            questions=[
                {
                    "type": "multiple_choice",
                    "question": f"Câu hỏi ôn tập hợp lệ số {index}?",
                    "options": [f"Đáp án {index}", "Nhiễu"],
                    "answer": f"Đáp án {index}",
                    "explanation": "Giải thích ngắn nhưng đầy đủ.",
                    "source_pages": [1],
                }
                for index in range(1, 6)
            ]
        )
        markdown = build_quiz_markdown(quiz)
        self.assertIn("## Câu hỏi ôn tập", markdown)
        self.assertIn("**Đáp án:** Đáp án 1", markdown)
        self.assertNotIn("## Tổng quan 30 giây", markdown)


if __name__ == "__main__":
    unittest.main()
