from datetime import datetime
from typing import List, Optional
import enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base
from app.auth.models import CustomUser, UnitMembers


class SeniorityCategory(str, enum.Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"


class PaymentStatus(str, enum.Enum):
    PENDING = "Pending"
    PROOF_UPLOADED = "Proof Uploaded"
    PAID = "Paid"
    DECLINED = "Declined"


class AppealStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class IndividualEvent(Base):
    __tablename__ = "individual_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    participations: Mapped[List["IndividualEventParticipation"]] = relationship(
        "IndividualEventParticipation", back_populates="individual_event"
    )


class GroupEvent(Base):
    __tablename__ = "group_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    max_allowed_limit: Mapped[int] = mapped_column(Integer, default=2)
    min_allowed_limit: Mapped[int] = mapped_column(Integer, default=1)
    per_unit_allowed_limit: Mapped[int] = mapped_column(Integer, default=2)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    participations: Mapped[List["GroupEventParticipation"]] = relationship(
        "GroupEventParticipation", back_populates="group_event"
    )


class IndividualEventParticipation(Base):
    __tablename__ = "individual_event_participation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    individual_event_id: Mapped[int] = mapped_column(ForeignKey("individual_event.id"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("unit_members.id"), nullable=False)
    added_by_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False)
    chest_number: Mapped[Optional[str]] = mapped_column(String(50))
    seniority_category: Mapped[Optional[SeniorityCategory]] = mapped_column(SAEnum(SeniorityCategory))
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("individual_event_id", "participant_id", name="uq_ind_event_per_participant"),
        UniqueConstraint("individual_event_id", "chest_number", name="uq_ind_event_chest_number"),
    )

    individual_event: Mapped[IndividualEvent] = relationship("IndividualEvent", back_populates="participations")
    participant: Mapped[UnitMembers] = relationship("UnitMembers")
    added_by: Mapped[CustomUser] = relationship("CustomUser")


class GroupEventParticipation(Base):
    __tablename__ = "group_event_participation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_event_id: Mapped[int] = mapped_column(ForeignKey("group_event.id"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("unit_members.id"), nullable=False)
    chest_number: Mapped[Optional[str]] = mapped_column(String(50))
    added_by_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("group_event_id", "participant_id", name="uq_group_event_per_participant"),
        UniqueConstraint("group_event_id", "chest_number", name="uq_group_event_chest_number"),
    )

    group_event: Mapped[GroupEvent] = relationship("GroupEvent", back_populates="participations")
    participant: Mapped[UnitMembers] = relationship("UnitMembers")
    added_by: Mapped[CustomUser] = relationship("CustomUser")


class KalamelaExcludeMembers(Base):
    __tablename__ = "kalamela_exclude_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    members_id: Mapped[int] = mapped_column(ForeignKey("unit_members.id"), unique=True, nullable=False)

    member: Mapped[UnitMembers] = relationship("UnitMembers")


class KalamelaPayments(Base):
    __tablename__ = "kalamela_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paid_by_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False)
    individual_events_count: Mapped[int] = mapped_column(Integer, default=0)
    group_events_count: Mapped[int] = mapped_column(Integer, default=0)
    total_amount_to_pay: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_proof_path: Mapped[Optional[str]] = mapped_column(String(500))
    payment_status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    paid_by: Mapped[CustomUser] = relationship("CustomUser")


class IndividualEventScoreCard(Base):
    __tablename__ = "individual_event_score_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_participation_id: Mapped[int] = mapped_column(ForeignKey("individual_event_participation.id"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("unit_members.id"), nullable=False)
    awarded_mark: Mapped[int] = mapped_column(Integer, default=0)
    grade: Mapped[Optional[str]] = mapped_column(String(10))
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    added_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    participation: Mapped[IndividualEventParticipation] = relationship("IndividualEventParticipation")
    participant: Mapped[UnitMembers] = relationship("UnitMembers")


class GroupEventScoreCard(Base):
    __tablename__ = "group_event_score_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    awarded_mark: Mapped[int] = mapped_column(Integer, default=0)
    chest_number: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[Optional[str]] = mapped_column(String(10))
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    added_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Appeal(Base):
    __tablename__ = "appeal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    added_by_id: Mapped[int] = mapped_column(ForeignKey("unit_members.id"), nullable=False)
    chest_number: Mapped[str] = mapped_column(String(50), nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    statement: Mapped[str] = mapped_column(String(1000), nullable=False)
    reply: Mapped[Optional[str]] = mapped_column(String(1000))
    status: Mapped[AppealStatus] = mapped_column(SAEnum(AppealStatus), default=AppealStatus.PENDING)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    added_by: Mapped[UnitMembers] = relationship("UnitMembers")


class AppealPayments(Base):
    __tablename__ = "appeal_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeal.id"), nullable=False, unique=True)
    total_amount_to_pay: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(64), default="Appeal Fee")
    payment_status: Mapped[str] = mapped_column(String(64), default="Pending")
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appeal: Mapped[Appeal] = relationship("Appeal")

