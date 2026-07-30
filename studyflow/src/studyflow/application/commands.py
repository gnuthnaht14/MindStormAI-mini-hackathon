from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from studyflow.domain.models import ArtifactType


@dataclass(frozen=True, slots=True)
class IngestDocumentCommand:
    session_id: str
    filename: str
    mime_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class GenerateArtifactCommand:
    session_id: str
    document_id: str
    artifact_type: ArtifactType
    slide_indexes: tuple[int, ...] = ()
    options: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AskTutorCommand:
    session_id: str
    document_id: str
    question: str
    selected_slide_indexes: tuple[int, ...] = ()
