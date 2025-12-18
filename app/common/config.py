from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "CSI Kalamela FastAPI"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/csi_kalamela"
    secret_key: str = "change-this-secret"
    access_token_expire_minutes: int = 15  # Short-lived access tokens
    refresh_token_expire_days: int = 7  # Long-lived refresh tokens
    algorithm: str = "HS256"
    cors_origins: List[str] = ["*"]
    upload_dir: str = "storage/uploads"
    export_dir: str = "storage/exports"
    max_upload_size_mb: int = 5
    allowed_upload_extensions: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]

    # Backblaze B2 Storage
    b2_endpoint: str = "https://s3.eu-central-003.backblazeb2.com"
    b2_bucket_name: str = "csi-youthmovement"
    b2_key_id: str = "4c6b021b5a16"
    b2_application_key: str = "00375a2d3225788e08472bed0aec292c1e166269e1"
    b2_region: str = "eu-central-003"
    b2_key_prefix: str = "csi_youth_"  # Required prefix for B2 application key

    # Pagination defaults
    default_page_size: int = 50

    # Email settings placeholder (for password reset tokens)
    mail_sender: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

