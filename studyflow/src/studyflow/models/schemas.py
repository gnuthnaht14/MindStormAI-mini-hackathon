from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionType = Literal["multiple_choice", "true_false", "short_answer"]
PageVisualType = Literal["text", "scanned", "mixed_visual", "diagram_or_chart"]
PageAnalysisMethod = Literal["text", "ocr", "vision", "text+vision", "ocr+vision"]


def _normalize_source_pages(pages: list[int]) -> list[int]:
    """Keep citations deterministic without accepting invalid page numbers."""

    return sorted(set(pages))


class PageContent(BaseModel):
    """Content and extraction metadata kept at page granularity."""

    model_config = ConfigDict(str_strip_whitespace=True)

    page_number: int = Field(ge=1)
    text_layer: str = ""
    ocr_text: str = ""
    visual_summary: str = ""
    visual_facts: list[str] = Field(default_factory=list)
    visual_type: PageVisualType = "text"
    image_count: int = Field(default=0, ge=0)
    drawing_count: int = Field(default=0, ge=0)
    image_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis_method: PageAnalysisMethod = "text"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PageVisualAnalysis(BaseModel):
    """Structured result returned by the vision model for one rendered page."""

    model_config = ConfigDict(str_strip_whitespace=True)

    visual_summary: str = Field(min_length=8, max_length=1_500)
    visible_text: str = Field(default="", max_length=3_000)
    important_facts: list[str] = Field(default_factory=list, max_length=12)
    confidence: Literal["low", "medium", "high"] = "medium"


class PDFExtraction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    filename: str
    text: str
    page_count: int = Field(ge=1)
    character_count: int = Field(ge=0)
    processed_characters: int = Field(ge=0)
    page_texts: list[str] = Field(default_factory=list)
    page_contents: list[PageContent] = Field(default_factory=list)
    visual_candidate_pages: list[int] = Field(default_factory=list)
    ocr_page_count: int = Field(default=0, ge=0)
    vision_page_count: int = Field(default=0, ge=0)
    visual_warnings: list[str] = Field(default_factory=list)
    was_truncated: bool = False


class CitedPoint(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=8)
    source_pages: list[int] = Field(min_length=1, max_length=8)

    @field_validator("source_pages")
    @classmethod
    def normalize_source_pages(cls, pages: list[int]) -> list[int]:
        if any(page < 1 for page in pages):
            raise ValueError("Source page numbers must be positive")
        return _normalize_source_pages(pages)


class KeyConcept(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    simple_explanation: str = Field(min_length=20)
    example: str | None
    source_pages: list[int] = Field(min_length=1, max_length=8)

    @field_validator("source_pages")
    @classmethod
    def normalize_source_pages(cls, pages: list[int]) -> list[int]:
        if any(page < 1 for page in pages):
            raise ValueError("Source page numbers must be positive")
        return _normalize_source_pages(pages)


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: QuestionType
    question: str = Field(min_length=5)
    options: list[str] = Field(default_factory=list, max_length=6)
    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=5)
    source_pages: list[int] = Field(min_length=1, max_length=8)

    @field_validator("options")
    @classmethod
    def clean_options(cls, options: list[str]) -> list[str]:
        return [option.strip() for option in options if option.strip()]

    @field_validator("source_pages")
    @classmethod
    def normalize_source_pages(cls, pages: list[int]) -> list[int]:
        if any(page < 1 for page in pages):
            raise ValueError("Source page numbers must be positive")
        return _normalize_source_pages(pages)

    @model_validator(mode="after")
    def validate_options_for_type(self) -> "Question":
        if self.type == "multiple_choice" and len(self.options) < 2:
            raise ValueError("Multiple-choice questions need at least two options")
        if self.type == "true_false" and not self.options:
            self.options = ["Đúng", "Sai"]
        return self


class SummaryMaterial(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=160)
    overview: CitedPoint
    learning_objectives: list[CitedPoint] = Field(min_length=2, max_length=6)
    key_concepts: list[KeyConcept] = Field(min_length=3, max_length=10)
    process_steps: list[CitedPoint] = Field(max_length=10)
    common_misconceptions: list[CitedPoint] = Field(max_length=6)
    takeaways: list[CitedPoint] = Field(min_length=3, max_length=8)


class QuizMaterial(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    questions: list[Question] = Field(min_length=5, max_length=10)


class StudyMaterial(SummaryMaterial):
    """Legacy combined schema used only to load old demo/export payloads."""

    questions: list[Question] = Field(min_length=5, max_length=10)
