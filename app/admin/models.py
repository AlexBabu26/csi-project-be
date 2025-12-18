"""Admin module models for site settings, notices, and quick links."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.db import Base


class SiteSettings(Base):
    """Singleton table for site-wide settings."""
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_name: Mapped[str] = mapped_column(String(255), default="CSI MKD YOUTH MOVEMENT")
    app_subtitle: Mapped[Optional[str]] = mapped_column(String(255))
    about_text: Mapped[Optional[str]] = mapped_column(Text)
    logo_primary_url: Mapped[Optional[str]] = mapped_column(String(500))
    logo_secondary_url: Mapped[Optional[str]] = mapped_column(String(500))
    logo_tertiary_url: Mapped[Optional[str]] = mapped_column(String(500))
    registration_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    registration_closed_message: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Contact info
    contact_address: Mapped[Optional[str]] = mapped_column(Text)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Social links
    social_facebook: Mapped[Optional[str]] = mapped_column(String(500))
    social_instagram: Mapped[Optional[str]] = mapped_column(String(500))
    social_youtube: Mapped[Optional[str]] = mapped_column(String(500))
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Notice(Base):
    """Marquee notices for homepage."""
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class QuickLink(Base):
    """Quick navigation links for homepage."""
    __tablename__ = "quick_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

