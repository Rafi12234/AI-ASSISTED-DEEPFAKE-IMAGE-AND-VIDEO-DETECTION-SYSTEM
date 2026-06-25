from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


class AISettings(BaseSettings):
    service_name: str = "Deepfake Detection AI Service"
    service_version: str = "0.31.0"

    app_env: str = "local"

    default_device: Literal["cpu", "cuda"] = "cpu"
    enable_gpu: bool = False

    max_image_size_mb: int = 20
    max_video_size_mb: int = 500
    max_video_duration_seconds: int = 300

    model_root: Path = Field(default=ROOT_DIR / "models")
    artifact_root: Path = Field(default=ROOT_DIR / "artifacts")
    dataset_root: Path = Field(default=PROJECT_ROOT / "datasets")

    active_image_model: str = "heuristic_image_foundation_v1"
    active_video_model: str = "heuristic_video_foundation_v1"
    active_audio_model: str = "not_enabled"
    active_av_sync_model: str = "not_enabled"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_ai_settings() -> AISettings:
    settings = AISettings()

    settings.model_root.mkdir(parents=True, exist_ok=True)
    settings.artifact_root.mkdir(parents=True, exist_ok=True)
    settings.dataset_root.mkdir(parents=True, exist_ok=True)

    return settings


ai_settings = get_ai_settings()