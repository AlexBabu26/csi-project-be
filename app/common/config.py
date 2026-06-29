from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Load standard .env first, then repo "env" file (local override).
        env_file=(".env", "env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CSI Kalamela FastAPI"
    debug: bool = False
    
    # Database Configuration
    # For Neon serverless PostgreSQL, use the POOLED connection string for better
    # performance in serverless environments. The pooler reduces cold start latency.
    #
    # Direct connection (slower cold starts):
    #   postgresql+psycopg://user:pass@ep-xxx.region.aws.neon.tech/dbname
    #
    # Pooled connection (recommended for Vercel/serverless):
    #   postgresql+psycopg://user:pass@ep-xxx-pooler.region.aws.neon.tech/dbname?sslmode=require
    #
    # Note the "-pooler" suffix in the hostname for the pooled connection.
    # Set via DATABASE_URL in .env or env (never commit real credentials here).
    database_url: str = ""
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

    # Application timezone for date/time captures and display
    app_timezone: str = "Asia/Kolkata"

    # Email / notification settings
    mail_sender: Optional[str] = None
    resend_api_key: Optional[str] = None
    admin_notification_email: Optional[str] = None

    # OCR.space (optional PDF payment amount detection)
    ocr_space_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

