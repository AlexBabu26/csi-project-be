"""Conference module models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base


class Conference(Base):
    """Conference model for managing conferences."""
    
    __tablename__ = "conference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    added_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Active", nullable=False)


class ConferenceRegistrationData(Base):
    """Registration status tracking for conference district officials."""
    
    __tablename__ = "conference_registration_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    district_official_id: Mapped[int] = mapped_column(
        ForeignKey("custom_user.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(100), default="Registration Started", nullable=False)


class ConferenceDelegate(Base):
    """
    Conference delegates model linking officials and their member delegates.
    Each delegate entry represents either an official or a member delegated by an official.
    """
    
    __tablename__ = "conference_delegate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conference_id: Mapped[int] = mapped_column(
        ForeignKey("conference.id"), nullable=False, index=True
    )
    officials_id: Mapped[int] = mapped_column(
        ForeignKey("custom_user.id"), nullable=False, index=True
    )
    members_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("unit_members.id"), nullable=True, index=True
    )


class ConferencePayment(Base):
    """Payment tracking for conference registrations."""
    
    __tablename__ = "conference_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conference_id: Mapped[int] = mapped_column(
        ForeignKey("conference.id"), nullable=False, index=True
    )
    amount_to_pay: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("custom_user.id"), nullable=True, index=True
    )
    proof: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # File path
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # PAID, NOT PAID, PENDING


class FoodPreference(Base):
    """Food preference tracking for conference delegates by district."""
    
    __tablename__ = "food_preference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conference_id: Mapped[int] = mapped_column(
        ForeignKey("conference.id"), nullable=False, index=True
    )
    veg_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    non_veg_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("custom_user.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
