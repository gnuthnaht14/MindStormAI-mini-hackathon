from __future__ import annotations

import unittest

from studyflow.models import Question, StudyMaterial
from studyflow.services.export_service import build_markdown


class ExportServiceTests(unittest.TestCase):
    def test_markdown_contains_summary_questions_and_answers(self) -> None:
        material = StudyMaterial(
            title="Demo title",
            overview={
                "text": "Bản tổng quan đủ dài để vượt qua validation của schema StudyMaterial.",
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
            questions=[
                Question(
                    type="short_answer",
                    question=f"Câu hỏi ôn tập hợp lệ số {index}?",
                    answer=f"Đáp án {index}",
                    explanation="Giải thích ngắn nhưng đầy đủ.",
                    source_pages=[1],
                )
                for index in range(1, 6)
            ],
        )
        markdown = build_markdown(material)
        self.assertIn("# Demo title", markdown)
        self.assertIn("## Tổng quan 30 giây", markdown)
        self.assertIn("## Khái niệm trọng tâm", markdown)
        self.assertIn("Nguồn: trang 1", markdown)
        self.assertIn("**Đáp án:** Đáp án 1", markdown)


if __name__ == "__main__":
    unittest.main()
