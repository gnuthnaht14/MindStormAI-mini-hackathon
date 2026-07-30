from __future__ import annotations

import unittest

from studyflow.models import Question
from studyflow.services.quiz_service import calculate_quiz_score, is_correct_answer


def make_question(answer: str) -> Question:
    return Question(
        type="multiple_choice",
        question="Đâu là đáp án đúng?",
        options=["A. Lựa chọn một", "B. Lựa chọn hai", "C. Lựa chọn ba"],
        answer=answer,
        explanation="Giải thích đủ dài cho câu hỏi kiểm thử.",
        source_pages=[1],
    )


class QuizServiceTests(unittest.TestCase):
    def test_accepts_exact_answer(self) -> None:
        self.assertTrue(is_correct_answer(make_question("B. Lựa chọn hai"), "B. Lựa chọn hai"))

    def test_accepts_answer_letter(self) -> None:
        self.assertTrue(is_correct_answer(make_question("B"), "B. Lựa chọn hai"))

    def test_accepts_answer_without_option_prefix(self) -> None:
        self.assertTrue(is_correct_answer(make_question("Lựa chọn hai"), "B. Lựa chọn hai"))

    def test_rejects_wrong_answer(self) -> None:
        self.assertFalse(is_correct_answer(make_question("B"), "A. Lựa chọn một"))

    def test_calculates_score_on_ten_point_scale(self) -> None:
        self.assertEqual(calculate_quiz_score(6, 8), 7.5)

    def test_rejects_invalid_score_input(self) -> None:
        with self.assertRaises(ValueError):
            calculate_quiz_score(9, 8)


if __name__ == "__main__":
    unittest.main()
