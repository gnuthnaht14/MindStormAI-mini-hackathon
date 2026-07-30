from __future__ import annotations

import re

from studyflow.models import Question


OPTION_PREFIX = re.compile(r"^\s*([A-F])[\).:\-]\s*", re.IGNORECASE)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _without_option_prefix(value: str) -> str:
    return OPTION_PREFIX.sub("", value).strip()


def is_correct_answer(question: Question, selected: str) -> bool:
    """Grade an objective question locally without another model call."""

    expected = question.answer.strip()
    if _normalize(selected) == _normalize(expected):
        return True

    expected_letter = expected.rstrip(".).:- ").upper()
    if len(expected_letter) == 1 and "A" <= expected_letter <= "F":
        option_index = ord(expected_letter) - ord("A")
        return option_index < len(question.options) and selected == question.options[option_index]

    return _normalize(_without_option_prefix(selected)) == _normalize(_without_option_prefix(expected))


def calculate_quiz_score(correct_answers: int, total_questions: int) -> float:
    """Return a deterministic score on a ten-point scale."""

    if total_questions < 1:
        raise ValueError("total_questions must be positive")
    if correct_answers < 0 or correct_answers > total_questions:
        raise ValueError("correct_answers must be between zero and total_questions")
    return round(correct_answers / total_questions * 10, 1)
