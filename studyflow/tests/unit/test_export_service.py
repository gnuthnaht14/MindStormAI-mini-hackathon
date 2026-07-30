from __future__ import annotations

import unittest

from studyflow.models import Question, StudyMaterial
from studyflow.services.export_service import build_markdown


class ExportServiceTests(unittest.TestCase):
    def test_markdown_contains_summary_questions_and_answers(self) -> None:
        material = StudyMaterial(
            title="Demo title",
            summary="Bản tóm tắt đủ dài để vượt qua validation của schema StudyMaterial.",
            key_points=["Ý một", "Ý hai", "Ý ba"],
            questions=[
                Question(
                    type="short_answer",
                    question=f"Câu hỏi ôn tập hợp lệ số {index}?",
                    answer=f"Đáp án {index}",
                    explanation="Giải thích ngắn nhưng đầy đủ.",
                )
                for index in range(1, 6)
            ],
        )
        markdown = build_markdown(material)
        self.assertIn("# Demo title", markdown)
        self.assertIn("## Tóm tắt", markdown)
        self.assertIn("**Đáp án:** Đáp án 1", markdown)


if __name__ == "__main__":
    unittest.main()
