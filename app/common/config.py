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
    access_token_expire_minutes: int = 60 * 6
    algorithm: str = "HS256"
    cors_origins: List[str] = ["*"]
    upload_dir: str = "storage/uploads"
    export_dir: str = "storage/exports"
    max_upload_size_mb: int = 5
    allowed_upload_extensions: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]

    # Pagination defaults
    default_page_size: int = 50

    # Email settings placeholder (for password reset tokens)
    mail_sender: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

