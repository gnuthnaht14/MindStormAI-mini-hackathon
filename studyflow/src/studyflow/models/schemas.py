from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionType = Literal["multiple_choice", "true_false", "short_answer"]


class PDFExtraction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    filename: str
    text: str
    page_count: int = Field(ge=1)
    character_count: int = Field(ge=1)
    processed_characters: int = Field(ge=1)
    page_texts: list[str] = Field(default_factory=list)
    was_truncated: bool = False


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: QuestionType
    question: str = Field(min_length=5)
    options: list[str] = Field(default_factory=list, max_length=6)
    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=5)

    @field_validator("options")
    @classmethod
    def clean_options(cls, options: list[str]) -> list[str]:
        return [option.strip() for option in options if option.strip()]

    @model_validator(mode="after")
    def validate_options_for_type(self) -> "Question":
        if self.type == "multiple_choice" and len(self.options) < 2:
            raise ValueError("Multiple-choice questions need at least two options")
        if self.type == "true_false" and not self.options:
            self.options = ["Đúng", "Sai"]
        return self


class StudyMaterial(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=160)
    summary: str = Field(min_length=40)
    key_points: list[str] = Field(min_length=3, max_length=12)
    questions: list[Question] = Field(min_length=5, max_length=10)

    @field_validator("key_points")
    @classmethod
    def remove_empty_key_points(cls, items: list[str]) -> list[str]:
        return [item.strip() for item in items if item.strip()]
