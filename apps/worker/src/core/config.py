from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    supabase_storage_bucket_videos: str = "videos"
    supabase_storage_bucket_clips: str = "clips"
    supabase_storage_bucket_reports: str = "reports"
    supabase_storage_bucket_reference_frames: str = "reference-frames"

    redis_url: str = "redis://localhost:6379/0"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "no-reply@sportslyze.com.br"

    yolo_model_path: str = "yolov8n.pt"
    enable_ocr: bool = True

    video_retention_days_default: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
