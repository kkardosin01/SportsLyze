from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    supabase_storage_bucket_videos: str = "videos"
    supabase_storage_bucket_clips: str = "clips"
    supabase_storage_bucket_reports: str = "reports"

    # Fila
    redis_url: str = "redis://localhost:6379/0"

    # Upload
    max_upload_size_bytes: int = 8 * 1024 * 1024 * 1024  # 8 GB
    allowed_video_codecs: list[str] = ["h264", "hevc"]
    allowed_video_extensions: list[str] = [".mp4"]

    # Retenção de vídeo original
    video_retention_days_default: int = 15

    # E-mail
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "no-reply@sportslyze.com.br"

    # App
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
