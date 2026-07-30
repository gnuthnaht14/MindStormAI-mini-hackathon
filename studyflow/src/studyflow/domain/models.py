from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping


def utc_now() -> datetime:
    return datetime.now(UTC)


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ArtifactType(StrEnum):
    NOTES = "notes"
    SUMMARY = "summary"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"


class ArtifactStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class SlidePage:
    index: int
    text: str
    title: str | None = None
    speaker_notes: str | None = None
    image_uri: str | None = None

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("SlidePage.index is one-based and must be positive")


@dataclass(frozen=True, slots=True)
class SlideDocument:
    id: str
    filename: str
    mime_type: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    pages: tuple[SlidePage, ...] = ()
    checksum: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class SourceChunk:
    id: str
    document_id: str
    text: str
    slide_indexes: tuple[int, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.slide_indexes:
            raise ValueError("SourceChunk must point to at least one slide")


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: str
    slide_indexes: tuple[int, ...]
    quote: str | None = None


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str
    citations: tuple[Citation, ...] = ()
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class StudyArtifact:
    id: str
    session_id: str
    document_id: str
    artifact_type: ArtifactType
    status: ArtifactStatus = ArtifactStatus.PENDING
    payload: Mapping[str, Any] = field(default_factory=dict)
    citations: tuple[Citation, ...] = ()
    model: str | None = None
    prompt_version: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class StudySession:
    id: str
    title: str
    document_ids: tuple[str, ...] = ()
    messages: tuple[ChatMessage, ...] = ()
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
