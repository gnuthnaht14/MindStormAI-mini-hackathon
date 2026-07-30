from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Small dependency-free settings object for the first backend phase."""

    environment: str = "development"
    data_dir: Path = Path("var")
    default_llm_provider: str = "openrouter"
    default_chat_model: str | None = None
    max_upload_mb: int = 50
    max_chat_history_turns: int = 10

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            data_dir=Path(os.getenv("DATA_DIR", "var")),
            default_llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openrouter"),
            default_chat_model=os.getenv("DEFAULT_CHAT_MODEL") or None,
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "50")),
            max_chat_history_turns=int(os.getenv("MAX_CHAT_HISTORY_TURNS", "10")),
        )
