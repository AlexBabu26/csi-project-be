import enum
from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, Column, Date, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base


class UserType(str, enum.Enum):
    ADMIN = "1"
    UNIT = "2"
    DISTRICT_OFFICIAL = "3"


class ClergyDistrict(Base):
    __tablename__ = "clergy_district"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    units: Mapped[List["UnitName"]] = relationship("UnitName", back_populates="district", cascade="all, delete")
    users: Mapped[List["CustomUser"]] = relationship("CustomUser", back_populates="clergy_district")


class UnitName(Base):
    __tablename__ = "unit_name"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clergy_district_id: Mapped[int] = mapped_column(ForeignKey("clergy_district.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (UniqueConstraint("clergy_district_id", "name", name="uq_unit_name_per_district"),)

    district: Mapped["ClergyDistrict"] = relationship("ClergyDistrict", back_populates="units")
    users: Mapped[List["CustomUser"]] = relationship("CustomUser", back_populates="unit_name")


class CustomUser(Base):
    __tablename__ = "custom_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(150))
    last_name: Mapped[Optional[str]] = mapped_column(String(150))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    unit_name_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unit_name.id"))
    clergy_district_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clergy_district.id"))
    conference_member_count: Mapped[Optional[int]] = mapped_column(Integer)
    conference_official_count: Mapped[Optional[int]] = mapped_column(Integer)
    conference_id: Mapped[Optional[int]] = mapped_column(Integer)

    unit_name: Mapped[Optional["UnitName"]] = relationship("UnitName", back_populates="users")
    clergy_district: Mapped[Optional["ClergyDistrict"]] = relationship("ClergyDistrict", back_populates="users")
    unit_registration: Mapped[Optional["UnitRegistrationData"]] = relationship(
        "UnitRegistrationData", back_populates="registered_user", uselist=False
    )
    unit_details: Mapped[Optional["UnitDetails"]] = relationship(
        "UnitDetails", back_populates="registered_user", uselist=False
    )
    unit_members: Mapped[List["UnitMembers"]] = relationship("UnitMembers", back_populates="registered_user")
    unit_officials: Mapped[Optional["UnitOfficials"]] = relationship(
        "UnitOfficials", back_populates="registered_user", uselist=False
    )
    unit_councilors: Mapped[List["UnitCouncilor"]] = relationship("UnitCouncilor", back_populates="registered_user")


class UnitRegistrationData(Base):
    __tablename__ = "unit_registration_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registered_user_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="Registration Started")

    registered_user: Mapped["CustomUser"] = relationship("CustomUser", back_populates="unit_registration")


class UnitDetails(Base):
    __tablename__ = "unit_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registered_user_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), unique=True, nullable=False)
    registration_year: Mapped[int] = mapped_column(Integer, nullable=True)
    number_of_unit_members: Mapped[int] = mapped_column(Integer, nullable=True)

    registered_user: Mapped["CustomUser"] = relationship("CustomUser", back_populates="unit_details")


class UnitMembers(Base):
    __tablename__ = "unit_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registered_user_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    dob: Mapped[Optional[date]] = mapped_column(Date)
    number: Mapped[Optional[str]] = mapped_column(String(30))
    qualification: Mapped[Optional[str]] = mapped_column(String(255))
    blood_group: Mapped[Optional[str]] = mapped_column(String(10))

    registered_user: Mapped["CustomUser"] = relationship("CustomUser", back_populates="unit_members")


class UnitOfficials(Base):
    __tablename__ = "unit_officials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registered_user_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), unique=True, nullable=False)
    president: Mapped[Optional[str]] = mapped_column(String(255))
    vice_president: Mapped[Optional[str]] = mapped_column(String(255))
    secretary: Mapped[Optional[str]] = mapped_column(String(255))
    joint_secretary: Mapped[Optional[str]] = mapped_column(String(255))
    treasurer: Mapped[Optional[str]] = mapped_column(String(255))

    registered_user: Mapped["CustomUser"] = relationship("CustomUser", back_populates="unit_officials")


class UnitCouncilor(Base):
    __tablename__ = "unit_councilor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registered_user_id: Mapped[int] = mapped_column(ForeignKey("custom_user.id"), nullable=False)
    unit_member_id: Mapped[int] = mapped_column(ForeignKey("unit_members.id"), nullable=False)

    registered_user: Mapped["CustomUser"] = relationship("CustomUser", back_populates="unit_councilors")
    unit_member: Mapped["UnitMembers"] = relationship("UnitMembers")


class LoginAudit(Base):
    __tablename__ = "login_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(150))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("username <> ''", name="ck_login_audit_username_nonempty"),)

