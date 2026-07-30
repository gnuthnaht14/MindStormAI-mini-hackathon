from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, TypeVar

from .models import ChatMessage, SlideDocument, SourceChunk, StudyArtifact, StudySession


StructuredOutput = TypeVar("StructuredOutput")


@dataclass(frozen=True, slots=True)
class UploadedFile:
    filename: str
    mime_type: str
    local_path: Path
    size_bytes: int


@dataclass(frozen=True, slots=True)
class LLMResult:
    text: str | None = None
    structured: Mapping[str, Any] | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        context: Sequence[SourceChunk] = (),
        response_schema: type[StructuredOutput] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> LLMResult: ...


class DocumentParser(Protocol):
    def supports(self, mime_type: str, filename: str) -> bool: ...

    async def parse(self, document_id: str, source: UploadedFile) -> SlideDocument: ...


class RetrievalIndex(Protocol):
    async def replace_document(self, document_id: str, chunks: Sequence[SourceChunk]) -> None: ...

    async def search(self, document_id: str, query: str, *, limit: int = 8) -> Sequence[SourceChunk]: ...

    async def delete_document(self, document_id: str) -> None: ...


class FileStorage(Protocol):
    async def save(self, session_id: str, filename: str, content: bytes) -> Path: ...

    async def delete(self, path: Path) -> None: ...


class DocumentRepository(Protocol):
    async def save(self, document: SlideDocument) -> None: ...

    async def get(self, document_id: str) -> SlideDocument | None: ...


class SessionRepository(Protocol):
    async def save(self, session: StudySession) -> None: ...

    async def get(self, session_id: str) -> StudySession | None: ...


class ArtifactRepository(Protocol):
    async def save(self, artifact: StudyArtifact) -> None: ...

    async def get(self, artifact_id: str) -> StudyArtifact | None: ...

    async def list_for_document(self, document_id: str) -> Sequence[StudyArtifact]: ...
