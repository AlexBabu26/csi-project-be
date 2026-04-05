import enum
from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    Integer, String, Text, Boolean, Date, DateTime, Numeric,
    ForeignKey, Enum as SAEnum, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base


class YuvalokhamUserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class YMPaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING_PAYMENT = "pending_payment"


class ComplaintCategory(str, enum.Enum):
    DELIVERY_ISSUE = "delivery_issue"
    PAYMENT_DISPUTE = "payment_dispute"
    CONTENT_ISSUE = "content_issue"
    SUBSCRIPTION_PROBLEM = "subscription_problem"
    OTHER = "other"


class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MagazineStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class YMUser(Base):
    __tablename__ = "ym_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[YuvalokhamUserRole] = mapped_column(
        SAEnum(YuvalokhamUserRole, values_callable=lambda e: [x.value for x in e]),
        default=YuvalokhamUserRole.USER,
        nullable=False,
    )
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    district_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("clergy_district.id"), nullable=True
    )
    unit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("unit_name.id"), nullable=True
    )
    parish_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_csi_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    district = relationship("ClergyDistrict", foreign_keys=[district_id], lazy="joined")
    unit = relationship("UnitName", foreign_keys=[unit_id], lazy="joined")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    subscriptions: Mapped[List["YMSubscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[List["YMPayment"]] = relationship(
        back_populates="user", foreign_keys="YMPayment.user_id", cascade="all, delete-orphan"
    )
    complaints: Mapped[List["YMComplaint"]] = relationship(
        back_populates="user", foreign_keys="YMComplaint.user_id", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["YMRefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class YMRefreshToken(Base):
    __tablename__ = "ym_refresh_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["YMUser"] = relationship(back_populates="refresh_tokens")


class YMSubscriptionPlan(Base):
    __tablename__ = "ym_subscription_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    subscriptions: Mapped[List["YMSubscription"]] = relationship(back_populates="plan")


class YMSubscription(Base):
    __tablename__ = "ym_subscription"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("ym_subscription_plan.id"), nullable=False)
    plan_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    plan_price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    plan_duration_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, values_callable=lambda e: [x.value for x in e]),
        default=SubscriptionStatus.PENDING_PAYMENT,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["YMUser"] = relationship(back_populates="subscriptions")
    plan: Mapped["YMSubscriptionPlan"] = relationship(back_populates="subscriptions")
    payments: Mapped[List["YMPayment"]] = relationship(back_populates="subscription")


class YMPayment(Base):
    __tablename__ = "ym_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=False, index=True)
    subscription_id: Mapped[int] = mapped_column(Integer, ForeignKey("ym_subscription.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    proof_file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[YMPaymentStatus] = mapped_column(
        SAEnum(YMPaymentStatus, values_callable=lambda e: [x.value for x in e]),
        default=YMPaymentStatus.PENDING,
        nullable=False,
    )
    admin_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["YMUser"] = relationship(back_populates="payments", foreign_keys=[user_id])
    subscription: Mapped["YMSubscription"] = relationship(back_populates="payments")
    reviewer: Mapped[Optional["YMUser"]] = relationship(foreign_keys=[reviewed_by])


class YMMagazine(Base):
    __tablename__ = "ym_magazine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    issue_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[MagazineStatus] = mapped_column(
        SAEnum(MagazineStatus, values_callable=lambda e: [x.value for x in e]),
        default=MagazineStatus.DRAFT,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class YMComplaint(Base):
    __tablename__ = "ym_complaint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=False, index=True)
    category: Mapped[ComplaintCategory] = mapped_column(
        SAEnum(ComplaintCategory, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, values_callable=lambda e: [x.value for x in e]),
        default=ComplaintStatus.OPEN,
        nullable=False,
    )
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responded_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["YMUser"] = relationship(back_populates="complaints", foreign_keys=[user_id])
    responder: Mapped[Optional["YMUser"]] = relationship(foreign_keys=[responded_by])


class YMQrSetting(Base):
    __tablename__ = "ym_qr_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    qr_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ym_user.id"), nullable=True)
