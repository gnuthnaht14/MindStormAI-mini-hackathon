from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Small dependency-free settings object for the first backend phase."""

    environment: str = "development"
    data_dir: Path = Path("var")
    openai_model: str = "gpt-5.6-sol"
    max_upload_mb: int = 20
    max_input_characters: int = 60_000

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            data_dir=Path(os.getenv("DATA_DIR", "var")),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "20")),
            max_input_characters=int(os.getenv("MAX_INPUT_CHARACTERS", "60000")),
        )
