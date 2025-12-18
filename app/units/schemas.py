"""Pydantic schemas for units module."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequestStatus(str, Enum):
    """Status enum for various request types."""
    
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class FileExtension(str, Enum):
    """Allowed file extensions for proof documents."""
    
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"


# Archived Unit Member Schemas
class ArchivedUnitMemberBase(BaseModel):
    """Base schema for archived unit members."""
    
    name: str = Field(..., min_length=1, max_length=255)
    gender: Optional[str] = Field(None, max_length=10)
    dob: date
    number: str = Field(..., min_length=1, max_length=30)
    qualification: Optional[str] = Field(None, max_length=255)
    blood_group: Optional[str] = Field(None, max_length=10)


class ArchivedUnitMemberResponse(ArchivedUnitMemberBase):
    """Response schema for archived unit members."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int
    archived_at: datetime


# Removed Unit Member Schemas
class RemovedUnitMemberBase(BaseModel):
    """Base schema for removed unit members."""
    
    name: str = Field(..., min_length=1, max_length=255)
    gender: Optional[str] = Field(None, max_length=10)
    dob: date
    number: str = Field(..., min_length=1, max_length=30)
    qualification: Optional[str] = Field(None, max_length=255)
    blood_group: Optional[str] = Field(None, max_length=10)


class RemovedUnitMemberResponse(RemovedUnitMemberBase):
    """Response schema for removed unit members."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int
    archived_at: datetime


# Unit Transfer Request Schemas
class UnitTransferRequestBase(BaseModel):
    """Base schema for unit transfer requests."""
    
    unit_member_id: int = Field(..., gt=0)
    destination_unit_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=10, max_length=5000)


class UnitTransferRequestCreate(UnitTransferRequestBase):
    """Create schema for unit transfer requests."""
    
    proof: str = Field(..., description="File path to proof document")
    
    @field_validator("proof")
    @classmethod
    def validate_proof_extension(cls, v: str) -> str:
        """Validate that proof has allowed extension."""
        if not any(v.lower().endswith(f".{ext.value}") for ext in FileExtension):
            raise ValueError(f"File must have one of these extensions: {', '.join(e.value for e in FileExtension)}")
        return v


class UnitTransferRequestUpdate(BaseModel):
    """Update schema for unit transfer requests."""
    
    status: RequestStatus


class UnitTransferRequestResponse(UnitTransferRequestBase):
    """Response schema for unit transfer requests."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    current_unit_id: Optional[int]
    original_registered_user_id: Optional[int]
    proof: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime


# Unit Member Change Request Schemas
class UnitMemberChangeRequestBase(BaseModel):
    """Base schema for unit member change requests."""
    
    unit_member_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=10, max_length=5000)


class UnitMemberChangeRequestCreate(UnitMemberChangeRequestBase):
    """Create schema for unit member change requests."""
    
    name: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=10)
    dob: Optional[date] = None
    blood_group: Optional[str] = Field(None, max_length=10)
    qualification: Optional[str] = Field(None, max_length=255)
    proof: str = Field(..., description="File path to proof document")
    
    @field_validator("proof")
    @classmethod
    def validate_proof_extension(cls, v: str) -> str:
        """Validate that proof has allowed extension."""
        if not any(v.lower().endswith(f".{ext.value}") for ext in FileExtension):
            raise ValueError(f"File must have one of these extensions: {', '.join(e.value for e in FileExtension)}")
        return v


class UnitMemberChangeRequestResponse(UnitMemberChangeRequestBase):
    """Response schema for unit member change requests."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: Optional[str]
    gender: Optional[str]
    dob: Optional[date]
    blood_group: Optional[str]
    qualification: Optional[str]
    original_name: Optional[str]
    original_gender: Optional[str]
    original_dob: Optional[date]
    original_blood_group: Optional[str]
    original_qualification: Optional[str]
    proof: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime


# Unit Officials Change Request Schemas
class UnitOfficialsChangeRequestBase(BaseModel):
    """Base schema for unit officials change requests."""
    
    unit_official_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=10, max_length=5000)


class UnitOfficialsChangeRequestCreate(UnitOfficialsChangeRequestBase):
    """Create schema for unit officials change requests."""
    
    president_designation: Optional[str] = Field(None, max_length=50)
    president_name: Optional[str] = Field(None, max_length=255)
    president_phone: Optional[str] = Field(None, max_length=30)
    vice_president_name: Optional[str] = Field(None, max_length=255)
    vice_president_phone: Optional[str] = Field(None, max_length=30)
    secretary_name: Optional[str] = Field(None, max_length=255)
    secretary_phone: Optional[str] = Field(None, max_length=30)
    joint_secretary_name: Optional[str] = Field(None, max_length=255)
    joint_secretary_phone: Optional[str] = Field(None, max_length=30)
    treasurer_name: Optional[str] = Field(None, max_length=255)
    treasurer_phone: Optional[str] = Field(None, max_length=30)
    proof: str = Field(..., description="File path to proof document")
    
    @field_validator("proof")
    @classmethod
    def validate_proof_extension(cls, v: str) -> str:
        """Validate that proof has allowed extension."""
        if not any(v.lower().endswith(f".{ext.value}") for ext in FileExtension):
            raise ValueError(f"File must have one of these extensions: {', '.join(e.value for e in FileExtension)}")
        return v


class UnitOfficialsChangeRequestResponse(UnitOfficialsChangeRequestBase):
    """Response schema for unit officials change requests."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    president_designation: Optional[str]
    president_name: Optional[str]
    president_phone: Optional[str]
    original_president_designation: Optional[str]
    original_president_name: Optional[str]
    original_president_phone: Optional[str]
    vice_president_name: Optional[str]
    vice_president_phone: Optional[str]
    original_vice_president_name: Optional[str]
    original_vice_president_phone: Optional[str]
    secretary_name: Optional[str]
    secretary_phone: Optional[str]
    original_secretary_name: Optional[str]
    original_secretary_phone: Optional[str]
    joint_secretary_name: Optional[str]
    joint_secretary_phone: Optional[str]
    original_joint_secretary_name: Optional[str]
    original_joint_secretary_phone: Optional[str]
    treasurer_name: Optional[str]
    treasurer_phone: Optional[str]
    original_treasurer_name: Optional[str]
    original_treasurer_phone: Optional[str]
    proof: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime


# Unit Councilor Change Request Schemas
class UnitCouncilorChangeRequestBase(BaseModel):
    """Base schema for unit councilor change requests."""
    
    unit_councilor_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=10, max_length=5000)


class UnitCouncilorChangeRequestCreate(UnitCouncilorChangeRequestBase):
    """Create schema for unit councilor change requests."""
    
    unit_member_id: Optional[int] = Field(None, gt=0)
    proof: str = Field(..., description="File path to proof document")
    
    @field_validator("proof")
    @classmethod
    def validate_proof_extension(cls, v: str) -> str:
        """Validate that proof has allowed extension."""
        if not any(v.lower().endswith(f".{ext.value}") for ext in FileExtension):
            raise ValueError(f"File must have one of these extensions: {', '.join(e.value for e in FileExtension)}")
        return v


class UnitCouncilorChangeRequestResponse(UnitCouncilorChangeRequestBase):
    """Response schema for unit councilor change requests."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    unit_member_id: Optional[int]
    original_unit_member_id: Optional[int]
    proof: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime


# Unit Member Add Request Schemas
class UnitMemberAddRequestBase(BaseModel):
    """Base schema for unit member add requests."""
    
    name: str = Field(..., min_length=1, max_length=255)
    gender: str = Field(..., max_length=10)
    dob: date
    number: str = Field(..., min_length=1, max_length=30)
    qualification: Optional[str] = Field(None, max_length=255)
    blood_group: Optional[str] = Field(None, max_length=10)
    reason: str = Field(..., min_length=10, max_length=5000)


class UnitMemberAddRequestCreate(UnitMemberAddRequestBase):
    """Create schema for unit member add requests."""
    
    proof: Optional[str] = Field(None, description="File path to proof document")
    
    @field_validator("proof")
    @classmethod
    def validate_proof_extension(cls, v: Optional[str]) -> Optional[str]:
        """Validate that proof has allowed extension if provided."""
        if v and not any(v.lower().endswith(f".{ext.value}") for ext in FileExtension):
            raise ValueError(f"File must have one of these extensions: {', '.join(e.value for e in FileExtension)}")
        return v


class UnitMemberAddRequestResponse(UnitMemberAddRequestBase):
    """Response schema for unit member add requests."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int
    proof: Optional[str]
    status: RequestStatus
    created_at: datetime
    updated_at: datetime


# Unit Details Schemas
class UnitDetailsCreate(BaseModel):
    """Create schema for unit details."""
    
    president_designation: str = Field(..., min_length=1, max_length=50)
    president_name: str = Field(..., min_length=1, max_length=255)
    president_phone: str = Field(..., min_length=1, max_length=30)


class UnitDetailsResponse(BaseModel):
    """Response schema for unit details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int
    registration_year: Optional[int]
    number_of_unit_members: Optional[int]


# Unit Members Schemas (for regular operations)
class UnitMemberBase(BaseModel):
    """Base schema for unit members."""
    
    name: str = Field(..., min_length=1, max_length=255)
    gender: Optional[str] = Field(None, max_length=10)
    dob: Optional[date] = None
    number: Optional[str] = Field(None, max_length=30)
    qualification: Optional[str] = Field(None, max_length=255)
    blood_group: Optional[str] = Field(None, max_length=10)


class UnitMemberCreate(UnitMemberBase):
    """Create schema for unit members."""
    pass


class UnitMemberUpdate(BaseModel):
    """Update schema for unit members."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    gender: Optional[str] = Field(None, max_length=10)
    dob: Optional[date] = None
    number: Optional[str] = Field(None, max_length=30)
    qualification: Optional[str] = Field(None, max_length=255)
    blood_group: Optional[str] = Field(None, max_length=10)


class UnitMemberResponse(UnitMemberBase):
    """Response schema for unit members."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int


# Unit Officials Schemas (for regular operations)
class UnitOfficialsUpdate(BaseModel):
    """Update schema for unit officials."""
    
    position: str = Field(..., description="Position: President, Vice President, Secretary, Joint Secretary, or Treasurer")
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=1, max_length=30)
    designation: Optional[str] = Field(None, max_length=50, description="Only for President position")


class UnitOfficialsResponse(BaseModel):
    """Response schema for unit officials."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int
    president_designation: Optional[str]
    president_name: Optional[str]
    president_phone: Optional[str]
    vice_president_name: Optional[str]
    vice_president_phone: Optional[str]
    secretary_name: Optional[str]
    secretary_phone: Optional[str]
    joint_secretary_name: Optional[str]
    joint_secretary_phone: Optional[str]
    treasurer_name: Optional[str]
    treasurer_phone: Optional[str]


# Unit Councilor Schemas
class UnitCouncilorCreate(BaseModel):
    """Create schema for unit councilors."""
    
    unit_member_id: int = Field(..., gt=0)


class UnitCouncilorResponse(BaseModel):
    """Response schema for unit councilors."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    registered_user_id: int
    unit_member_id: int


# Status Update Schema
class StatusUpdate(BaseModel):
    """Schema for updating registration status."""
    
    status: str = Field(..., min_length=1, max_length=100)

