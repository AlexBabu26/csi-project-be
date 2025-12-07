from datetime import datetime
from typing import List, Optional
import enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base
from app.auth.models import CustomUser
from app.kalamela.models import PaymentStatus


class ConferenceRegistrationStatus(str, enum.Enum):
    STARTED = "Registration Started"
    SUBMITTED = "Submitted"
    APPROVED = "Approved"


class Conference(Base):
    __tablename__ = "conference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(String(1000))
    added_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(64), default="active")

    delegates: Mapped[List["ConferenceDelegate"]] = relationship("ConferenceDelegate", back_populates="conference")
    payments: Mapped[List["ConferencePayment"]] = relationship("ConferencePayment", back_populates="conference")


class ConferenceRegistrationData(Base):
    __tablename__ = "conference_registration_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_official_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default=ConferenceRegistrationStatus.STARTED.value)

    district_official: Mapped[CustomUser] = relationship("CustomUser")


class ConferenceDelegate(Base):
    __tablename__ = "conference_delegate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conference.id"), nullable=False)
    officials_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False)
    members_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unit_members.id"))

    __table_args__ = (UniqueConstraint("conference_id", "officials_id", name="uq_delegate_per_conf_official"),)

    conference: Mapped[Conference] = relationship("Conference", back_populates="delegates")
    official: Mapped[CustomUser] = relationship("CustomUser")


class ConferencePayment(Base):
    __tablename__ = "conference_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conference.id"), nullable=False)
    amount_to_pay: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False)
    proof_path: Mapped[Optional[str]] = mapped_column(String(500))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(128))

    conference: Mapped[Conference] = relationship("Conference", back_populates="payments")
    uploaded_by: Mapped[CustomUser] = relationship("CustomUser")

