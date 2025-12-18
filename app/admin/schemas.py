"""Pydantic schemas for admin site settings module."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# Contact & Social nested schemas
class ContactInfo(BaseModel):
    """Contact information schema."""
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class SocialLinks(BaseModel):
    """Social media links schema."""
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None


# Site Settings Schemas
class SiteSettingsResponse(BaseModel):
    """Response schema for site settings."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_name: str
    app_subtitle: Optional[str]
    about_text: Optional[str]
    logo_primary_url: Optional[str]
    logo_secondary_url: Optional[str]
    logo_tertiary_url: Optional[str]
    registration_enabled: bool
    registration_closed_message: Optional[str]
    contact: ContactInfo
    social_links: SocialLinks
    updated_at: datetime

    @classmethod
    def from_orm_with_nested(cls, obj):
        """Convert flat DB model to nested response."""
        return cls(
            id=obj.id,
            app_name=obj.app_name or "CSI MKD YOUTH MOVEMENT",
            app_subtitle=obj.app_subtitle,
            about_text=obj.about_text,
            logo_primary_url=obj.logo_primary_url,
            logo_secondary_url=obj.logo_secondary_url,
            logo_tertiary_url=obj.logo_tertiary_url,
            registration_enabled=obj.registration_enabled,
            registration_closed_message=obj.registration_closed_message,
            contact=ContactInfo(
                address=obj.contact_address,
                email=obj.contact_email,
                phone=obj.contact_phone,
            ),
            social_links=SocialLinks(
                facebook=obj.social_facebook,
                instagram=obj.social_instagram,
                youtube=obj.social_youtube,
            ),
            updated_at=obj.updated_at,
        )


class SiteSettingsUpdate(BaseModel):
    """Update schema for site settings."""
    app_name: Optional[str] = Field(None, max_length=255)
    app_subtitle: Optional[str] = Field(None, max_length=255)
    about_text: Optional[str] = None
    registration_enabled: Optional[bool] = None
    registration_closed_message: Optional[str] = Field(None, max_length=255)
    contact: Optional[ContactInfo] = None
    social_links: Optional[SocialLinks] = None


class LogoUploadResponse(BaseModel):
    """Response schema for logo upload."""
    logo_type: str
    url: str
    filename: str


# Notice Schemas
class NoticeBase(BaseModel):
    """Base schema for notices."""
    text: str = Field(..., min_length=1)
    priority: str = Field(default="normal", pattern="^(high|normal|low)$")
    is_active: bool = True
    display_order: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class NoticeCreate(NoticeBase):
    """Create schema for notices."""
    pass


class NoticeUpdate(BaseModel):
    """Update schema for notices."""
    text: Optional[str] = Field(None, min_length=1)
    priority: Optional[str] = Field(None, pattern="^(high|normal|low)$")
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class NoticeResponse(NoticeBase):
    """Response schema for notices."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class NoticeReorderItem(BaseModel):
    """Single item for notice reorder."""
    id: int
    display_order: int


class NoticeReorderRequest(BaseModel):
    """Request schema for reordering notices."""
    order: List[NoticeReorderItem]


# Quick Link Schemas
class QuickLinkBase(BaseModel):
    """Base schema for quick links."""
    label: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=500)
    enabled: bool = True
    display_order: int = 0


class QuickLinkCreate(QuickLinkBase):
    """Create schema for quick links."""
    pass


class QuickLinkUpdate(BaseModel):
    """Update schema for quick links."""
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    enabled: Optional[bool] = None
    display_order: Optional[int] = None


class QuickLinkResponse(QuickLinkBase):
    """Response schema for quick links."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

