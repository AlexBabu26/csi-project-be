from datetime import date, datetime
from typing import List, Optional
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base
from app.auth.models import CustomUser, UnitMembers


class SeniorityCategory(str, enum.Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"


class GenderRestriction(str, enum.Enum):
    """Gender restrictions for events."""
    MALE = "Male"
    FEMALE = "Female"
    # NULL means no gender restriction (open to all)


class RuleCategory(str, enum.Enum):
    """Categories for Kalamela rules."""
    AGE_RESTRICTION = "age_restriction"
    PARTICIPATION_LIMIT = "participation_limit"
    FEE = "fee"


class PaymentStatus(str, enum.Enum):
    PENDING = "Pending"
    PAID = "Paid"
    DECLINED = "Declined"


class AppealStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class EventType(str, enum.Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"


class PaymentQrCode(Base):
    """Reusable payment QR codes stored in cloud storage (B2)."""

    __tablename__ = "payment_qr_code"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_on: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Reverse relationship to fees that use this QR code
    registration_fees: Mapped[List["RegistrationFee"]] = relationship(
        "RegistrationFee",
        back_populates="qr_code",
    )


class EventCategory(Base):
    """Master table for Kalamela event categories."""
    __tablename__ = "event_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to events
    individual_events: Mapped[List["IndividualEvent"]] = relationship(
        "IndividualEvent", back_populates="event_category"
    )


class RegistrationFee(Base):
    """Master table for registration fees."""
    __tablename__ = "registration_fee"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("custom_user.id"), nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("custom_user.id"), nullable=True)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional reference to a shared payment QR code
    qr_code_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("payment_qr_code.id"),
        nullable=True,
    )

    # Relationships
    created_by: Mapped[Optional["CustomUser"]] = relationship(
        "CustomUser", foreign_keys=[created_by_id]
    )
    updated_by: Mapped[Optional["CustomUser"]] = relationship(
        "CustomUser", foreign_keys=[updated_by_id]
    )
    individual_events: Mapped[List["IndividualEvent"]] = relationship(
        "IndividualEvent", back_populates="registration_fee"
    )
    group_events: Mapped[List["GroupEvent"]] = relationship(
        "GroupEvent", back_populates="registration_fee"
    )
    qr_code: Mapped[Optional["PaymentQrCode"]] = relationship(
        "PaymentQrCode",
        back_populates="registration_fees",
    )


class IndividualEvent(Base):
    __tablename__ = "individual_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("event_category.id"), nullable=True)
    registration_fee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("registration_fee.id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gender_restriction: Mapped[Optional[GenderRestriction]] = mapped_column(
        SAEnum(GenderRestriction, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    seniority_restriction: Mapped[Optional[SeniorityCategory]] = mapped_column(
        SAEnum(SeniorityCategory, values_callable=lambda x: [e.value for e in x], name='seniority_restriction_enum'),
        nullable=True
    )
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    event_category: Mapped[Optional["EventCategory"]] = relationship(
        "EventCategory", back_populates="individual_events"
    )
    registration_fee: Mapped[Optional["RegistrationFee"]] = relationship(
        "RegistrationFee", back_populates="individual_events"
    )
    participations: Mapped[List["IndividualEventParticipation"]] = relationship(
        "IndividualEventParticipation", back_populates="individual_event"
    )


class GroupEvent(Base):
    __tablename__ = "group_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("event_category.id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    registration_fee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("registration_fee.id"), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gender_restriction: Mapped[Optional[GenderRestriction]] = mapped_column(
        SAEnum(GenderRestriction, values_callable=lambda x: [e.value for e in x], name='group_gender_restriction_enum'),
        nullable=True
    )
    seniority_restriction: Mapped[Optional[SeniorityCategory]] = mapped_column(
        SAEnum(SeniorityCategory, values_callable=lambda x: [e.value for e in x], name='group_seniority_restriction_enum'),
        nullable=True
    )
    max_allowed_limit: Mapped[int] = mapped_column(Integer, default=2)
    min_allowed_limit: Mapped[int] = mapped_column(Integer, default=1)
    per_unit_allowed_limit: Mapped[int] = mapped_column(Integer, default=1)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    event_category: Mapped[Optional["EventCategory"]] = relationship("EventCategory")
    registration_fee: Mapped[Optional["RegistrationFee"]] = relationship(
        "RegistrationFee", back_populates="group_events"
    )
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
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("group_event_id", "participant_id", name="uq_group_event_per_participant"),
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
    
    # Input: marks out of 100 (supports decimal values)
    awarded_mark: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    
    # Auto-calculated fields
    grade: Mapped[Optional[str]] = mapped_column(String(1))  # A, B, C, or null
    grade_points: Mapped[int] = mapped_column(Integer, default=0)  # 5, 3, 1, 0
    rank: Mapped[Optional[int]] = mapped_column(Integer)  # 1, 2, 3, or null
    rank_points: Mapped[int] = mapped_column(Integer, default=0)  # 5, 3, 1, 0
    total_points: Mapped[int] = mapped_column(Integer, default=0)  # grade_points + rank_points
    
    added_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    participation: Mapped[IndividualEventParticipation] = relationship("IndividualEventParticipation")
    participant: Mapped[UnitMembers] = relationship("UnitMembers")


class GroupEventScoreCard(Base):
    __tablename__ = "group_event_score_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chest_number: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Input: marks out of 100 (supports decimal values)
    awarded_mark: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    
    # Auto-calculated fields (Group events: rank points only, no grade points for championship)
    grade: Mapped[Optional[str]] = mapped_column(String(1))  # A, B, C, or null (for display)
    grade_points: Mapped[int] = mapped_column(Integer, default=0)  # 5, 3, 1, 0 (for display)
    rank: Mapped[Optional[int]] = mapped_column(Integer)  # 1, 2, 3, or null
    rank_points: Mapped[int] = mapped_column(Integer, default=0)  # 5, 3, 1, 0
    total_points: Mapped[int] = mapped_column(Integer, default=0)  # For groups: rank_points only
    
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


class KalamelaRules(Base):
    """
    Kalamela participation rules - managed by admin.
    
    Stores configurable rules for:
    - Age restrictions (Junior/Senior DOB ranges)
    - Participation limits (max events per person, max participants per unit)
    - Fee configurations
    """
    __tablename__ = "kalamela_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    rule_category: Mapped[RuleCategory] = mapped_column(
        SAEnum(RuleCategory, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    rule_value: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("custom_user.id"))

    # Relationship
    updated_by: Mapped[Optional["CustomUser"]] = relationship("CustomUser")


class ScheduleStatus(str, enum.Enum):
    """Status enum for event schedules."""
    SCHEDULED = "Scheduled"
    ONGOING = "Ongoing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    POSTPONED = "Postponed"


class EventSchedule(Base):
    """Model for event schedules/stages."""
    __tablename__ = "event_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    stage_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(
        SAEnum(ScheduleStatus, values_callable=lambda x: [e.value for e in x]),
        default=ScheduleStatus.SCHEDULED,
        nullable=False
    )
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_on: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("custom_user.id"),
        nullable=True
    )

    # Relationships
    created_by: Mapped[Optional["CustomUser"]] = relationship("CustomUser")