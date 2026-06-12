from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "Deepfake Detection System"
    app_env: str = "local"

    database_url: str

    redis_password: str
    redis_url: str

    minio_access_key: str
    minio_secret_key: str
    minio_endpoint: str
    minio_public_endpoint: str
    minio_bucket_raw: str
    minio_bucket_processed: str
    minio_bucket_reports: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_expiry_minutes: int = 15
    jwt_refresh_expiry_days: int = 7

    max_image_size_mb: int = 20
    max_video_size_mb: int = 500
    max_video_duration_seconds: int = 300
    file_retention_days: int = 30

    review_threshold: float = 0.61
    max_frames_per_video: int = 300
    frame_extraction_strategy: str = "adaptive"

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()