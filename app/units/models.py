"""Units module models for managing unit members, transfers, and change requests."""

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base


class RequestStatus(str, enum.Enum):
    """Status enum for various request types."""
    
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ArchivedUnitMember(Base):
    """
    Stores information about former UnitMembers who exceed the age threshold.
    These members are archived and removed from the active UnitMembers table.
    """
    
    __tablename__ = "archived_unit_member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registered_user_id: Mapped[int] = mapped_column(
        ForeignKey("custom_user.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    qualification: Mapped[Optional[str]] = mapped_column(String(255))
    blood_group: Mapped[Optional[str]] = mapped_column(String(10))
    archived_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def age(self) -> int:
        """Calculate current age from date of birth."""
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))


class RemovedUnitMember(Base):
    """
    Stores information about deliberately removed UnitMembers.
    These members are stored here and removed from the active UnitMembers table.
    """
    
    __tablename__ = "removed_unit_member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registered_user_id: Mapped[int] = mapped_column(
        ForeignKey("custom_user.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    qualification: Mapped[Optional[str]] = mapped_column(String(255))
    blood_group: Mapped[Optional[str]] = mapped_column(String(10))
    archived_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def age(self) -> int:
        """Calculate current age from date of birth."""
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))


class UnitTransferRequest(Base):
    """
    Manages unit transfer requests for members moving between units.
    Tracks original and destination units along with approval status.
    """
    
    __tablename__ = "unit_transfer_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_member_id: Mapped[int] = mapped_column(
        ForeignKey("unit_members.id"), nullable=False, index=True
    )
    current_unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("unit_name.id"), nullable=True
    )
    original_registered_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("custom_user.id"), nullable=True
    )
    destination_unit_id: Mapped[int] = mapped_column(
        ForeignKey("unit_name.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proof: Mapped[str] = mapped_column(String(500), nullable=False)  # File path
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UnitMemberChangeRequest(Base):
    """
    Manages change requests for unit member information.
    Stores both new and original values for auditing and reversion.
    """
    
    __tablename__ = "unit_member_change_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_member_id: Mapped[int] = mapped_column(
        ForeignKey("unit_members.id"), nullable=False, index=True
    )
    
    # New values
    name: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    dob: Mapped[Optional[date]] = mapped_column(Date)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10))
    qualification: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Original values for reversion
    original_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_gender: Mapped[Optional[str]] = mapped_column(String(10))
    original_dob: Mapped[Optional[date]] = mapped_column(Date)
    original_blood_group: Mapped[Optional[str]] = mapped_column(String(10))
    original_qualification: Mapped[Optional[str]] = mapped_column(String(255))
    
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proof: Mapped[str] = mapped_column(String(500), nullable=False)  # File path
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UnitOfficialsChangeRequest(Base):
    """
    Manages change requests for unit officials information.
    Stores both new and original values for all official positions.
    """
    
    __tablename__ = "unit_officials_change_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_official_id: Mapped[int] = mapped_column(
        ForeignKey("unit_officials.id"), nullable=False, index=True
    )
    
    # President fields
    president_designation: Mapped[Optional[str]] = mapped_column(String(50))
    original_president_designation: Mapped[Optional[str]] = mapped_column(String(50))
    president_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_president_name: Mapped[Optional[str]] = mapped_column(String(255))
    president_phone: Mapped[Optional[str]] = mapped_column(String(30))
    original_president_phone: Mapped[Optional[str]] = mapped_column(String(30))
    
    # Vice President fields
    vice_president_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_vice_president_name: Mapped[Optional[str]] = mapped_column(String(255))
    vice_president_phone: Mapped[Optional[str]] = mapped_column(String(30))
    original_vice_president_phone: Mapped[Optional[str]] = mapped_column(String(30))
    
    # Secretary fields
    secretary_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_secretary_name: Mapped[Optional[str]] = mapped_column(String(255))
    secretary_phone: Mapped[Optional[str]] = mapped_column(String(30))
    original_secretary_phone: Mapped[Optional[str]] = mapped_column(String(30))
    
    # Joint Secretary fields
    joint_secretary_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_joint_secretary_name: Mapped[Optional[str]] = mapped_column(String(255))
    joint_secretary_phone: Mapped[Optional[str]] = mapped_column(String(30))
    original_joint_secretary_phone: Mapped[Optional[str]] = mapped_column(String(30))
    
    # Treasurer fields
    treasurer_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_treasurer_name: Mapped[Optional[str]] = mapped_column(String(255))
    treasurer_phone: Mapped[Optional[str]] = mapped_column(String(30))
    original_treasurer_phone: Mapped[Optional[str]] = mapped_column(String(30))
    
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proof: Mapped[str] = mapped_column(String(500), nullable=False)  # File path
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UnitCouncilorChangeRequest(Base):
    """
    Manages change requests for unit councilor assignments.
    Allows changing which member is assigned as a councilor.
    """
    
    __tablename__ = "unit_councilor_change_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_councilor_id: Mapped[int] = mapped_column(
        ForeignKey("unit_councilor.id"), nullable=False, index=True
    )
    
    # New unit member selection
    unit_member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unit_members.id"))
    original_unit_member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unit_members.id"))
    
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proof: Mapped[str] = mapped_column(String(500), nullable=False)  # File path
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UnitMemberAddRequest(Base):
    """
    Manages requests to add new members to a unit.
    Stores all member information until approved by admin.
    """
    
    __tablename__ = "unit_member_add_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registered_user_id: Mapped[int] = mapped_column(
        ForeignKey("custom_user.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    qualification: Mapped[Optional[str]] = mapped_column(String(255))
    blood_group: Mapped[Optional[str]] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proof: Mapped[Optional[str]] = mapped_column(String(500))  # File path
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

