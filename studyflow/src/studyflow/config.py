from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Small dependency-free settings object for the first backend phase."""

    environment: str = "development"
    data_dir: Path = Path("var")
    # Model id theo định dạng OpenRouter: "<provider>/<model>"
    # Danh sách model & giá: https://openrouter.ai/models
    openrouter_model: str = "openai/gpt-4o-mini"
    max_upload_mb: int = 20
    max_input_characters: int = 60_000

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            data_dir=Path(os.getenv("DATA_DIR", "var")),
            # Ưu tiên OPENROUTER_MODEL; fallback OPENAI_MODEL để không phá vỡ
            # .env cũ nếu ai đó chưa kịp đổi tên biến.
            openrouter_model=os.getenv(
                "OPENROUTER_MODEL", os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
            ),
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "20")),
            max_input_characters=int(os.getenv("MAX_INPUT_CHARACTERS", "60000")),
        )