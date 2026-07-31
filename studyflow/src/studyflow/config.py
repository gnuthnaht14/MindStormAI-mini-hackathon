from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Small dependency-free settings object for the first backend phase."""

    environment: str = "development"
    data_dir: Path = Path("var")
    openai_model: str = "gpt-5.6-sol"
    openai_vision_model: str = "gpt-5.6-sol"
    max_upload_mb: int = 20
    max_input_characters: int = 60_000
    enable_local_ocr: bool = True
    ocr_languages: str = "vie+eng"
    enable_vision: bool = True
    max_vision_pages: int = 20
    vision_image_detail: str = "low"

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            data_dir=Path(os.getenv("DATA_DIR", "var")),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
            openai_vision_model=os.getenv(
                "OPENAI_VISION_MODEL",
                os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
            ),
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "20")),
            max_input_characters=int(os.getenv("MAX_INPUT_CHARACTERS", "60000")),
            enable_local_ocr=_env_bool("ENABLE_LOCAL_OCR", True),
            ocr_languages=os.getenv("OCR_LANGUAGES", "vie+eng"),
            enable_vision=_env_bool("ENABLE_VISION", True),
            max_vision_pages=max(0, int(os.getenv("MAX_VISION_PAGES", "8"))),
            vision_image_detail=os.getenv("VISION_IMAGE_DETAIL", "low"),
        )
