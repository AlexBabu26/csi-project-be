"""Pydantic schemas for Kalamela module."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SeniorityCategory(str, Enum):
    """Seniority category for events."""
    NA = "NA"
    JUNIOR = "Junior"
    SENIOR = "Senior"


class PaymentStatus(str, Enum):
    """Payment status enum."""
    PENDING = "Pending"
    PROOF_UPLOADED = "Proof Uploaded"
    PAID = "Paid"
    DECLINED = "Declined"


class AppealStatus(str, Enum):
    """Appeal status enum."""
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class EventType(str, Enum):
    """Event type enum for registration fees."""
    INDIVIDUAL = "individual"
    GROUP = "group"


# Registration Fee Schemas
class RegistrationFeeCreate(BaseModel):
    """Create schema for registration fee."""
    name: str = Field(..., min_length=1, max_length=255)
    event_type: EventType = Field(..., description="Type of event: 'individual' or 'group'")
    amount: int = Field(..., ge=0, description="Registration fee amount")


class RegistrationFeeUpdate(BaseModel):
    """Update schema for registration fee."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    event_type: Optional[EventType] = Field(None, description="Type of event: 'individual' or 'group'")
    amount: Optional[int] = Field(None, ge=0, description="Registration fee amount")


class RegistrationFeeResponse(BaseModel):
    """Response schema for registration fee."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    event_type: EventType
    amount: int
    created_by_id: Optional[int]
    updated_by_id: Optional[int]
    created_on: datetime
    updated_on: datetime


# Event Category Schemas
class EventCategoryCreate(BaseModel):
    """Create schema for event category."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class EventCategoryUpdate(BaseModel):
    """Update schema for event category."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class EventCategoryResponse(BaseModel):
    """Response schema for event category."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    created_on: datetime
    updated_on: datetime


# Event Schemas
class IndividualEventCreate(BaseModel):
    """Create schema for individual events."""
    name: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[int] = Field(None, gt=0, description="Foreign key to event_category table")
    registration_fee_id: Optional[int] = Field(None, gt=0, description="Foreign key to registration_fee table")
    description: Optional[str] = Field(None, max_length=1000)
    is_mandatory: bool = Field(default=False, description="Whether this event is mandatory")


class IndividualEventUpdate(BaseModel):
    """Update schema for individual events."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[int] = Field(None, gt=0, description="Foreign key to event_category table")
    registration_fee_id: Optional[int] = Field(None, gt=0, description="Foreign key to registration_fee table")
    description: Optional[str] = Field(None, max_length=1000)
    is_mandatory: Optional[bool] = Field(None, description="Whether this event is mandatory")


class IndividualEventResponse(BaseModel):
    """Response schema for individual events."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    category_id: Optional[int]
    category_name: Optional[str] = None
    registration_fee_id: Optional[int]
    registration_fee_amount: Optional[int] = None
    description: Optional[str]
    is_mandatory: bool
    created_on: datetime


class GroupEventCreate(BaseModel):
    """Create schema for group events."""
    name: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[int] = Field(None, gt=0, description="Foreign key to event_category table")
    description: Optional[str] = Field(None, max_length=1000)
    registration_fee_id: Optional[int] = Field(None, gt=0, description="Foreign key to registration_fee table")
    is_mandatory: bool = Field(default=False, description="Whether this event is mandatory")
    max_allowed_limit: int = Field(default=2, ge=1)
    min_allowed_limit: int = Field(default=1, ge=1)
    per_unit_allowed_limit: int = Field(default=1, ge=1)


class GroupEventUpdate(BaseModel):
    """Update schema for group events."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[int] = Field(None, gt=0, description="Foreign key to event_category table")
    description: Optional[str] = Field(None, max_length=1000)
    registration_fee_id: Optional[int] = Field(None, gt=0, description="Foreign key to registration_fee table")
    is_mandatory: Optional[bool] = Field(None, description="Whether this event is mandatory")
    max_allowed_limit: Optional[int] = Field(None, ge=1)
    min_allowed_limit: Optional[int] = Field(None, ge=1)
    per_unit_allowed_limit: Optional[int] = Field(None, ge=1)


class GroupEventResponse(BaseModel):
    """Response schema for group events."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    description: Optional[str]
    registration_fee_id: Optional[int]
    registration_fee_amount: Optional[int] = None
    is_mandatory: bool
    max_allowed_limit: int
    min_allowed_limit: int
    per_unit_allowed_limit: int
    created_on: datetime


# Participation Schemas
class IndividualParticipationCreate(BaseModel):
    """Create schema for individual participation."""
    individual_event_id: int = Field(..., gt=0)
    participant_id: int = Field(..., gt=0)
    seniority_category: SeniorityCategory = Field(default=SeniorityCategory.NA)


class IndividualParticipationResponse(BaseModel):
    """Response schema for individual participation."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    individual_event_id: int
    participant_id: int
    added_by_id: int
    chest_number: Optional[str]
    seniority_category: Optional[SeniorityCategory]
    created_on: datetime


class GroupParticipationCreate(BaseModel):
    """Create schema for group participation."""
    group_event_id: int = Field(..., gt=0)
    participant_ids: List[int] = Field(..., min_items=1, description="List of participant IDs for the team")


class GroupParticipationResponse(BaseModel):
    """Response schema for group participation."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    group_event_id: int
    participant_id: int
    chest_number: Optional[str]
    added_by_id: int


# Score Card Schemas
class IndividualScoreCreate(BaseModel):
    """Create schema for individual score."""
    event_participation_id: int = Field(..., gt=0)
    awarded_mark: int = Field(..., ge=0)
    grade: Optional[str] = Field(None, max_length=10)
    total_points: int = Field(..., ge=0)


class IndividualScoreBulkCreate(BaseModel):
    """Bulk create schema for individual scores."""
    participants: List[IndividualScoreCreate]


class IndividualScoreUpdate(BaseModel):
    """Update schema for individual score."""
    event_participation_id: int = Field(..., gt=0)
    awarded_mark: int = Field(..., ge=0)
    grade: Optional[str] = Field(None, max_length=10)
    total_points: int = Field(..., ge=0)


class IndividualScoreBulkUpdate(BaseModel):
    """Bulk update schema for individual scores."""
    participants: List[IndividualScoreUpdate]


class IndividualScoreResponse(BaseModel):
    """Response schema for individual score."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    event_participation_id: int
    participant_id: int
    awarded_mark: int
    grade: Optional[str]
    total_points: int
    added_on: datetime


class GroupScoreCreate(BaseModel):
    """Create schema for group score."""
    event_name: str = Field(..., min_length=1, max_length=255)
    chest_number: str = Field(..., min_length=1, max_length=50)
    awarded_mark: int = Field(..., ge=0)
    grade: Optional[str] = Field(None, max_length=10)
    total_points: int = Field(..., ge=0)


class GroupScoreBulkCreate(BaseModel):
    """Bulk create schema for group scores."""
    participants: List[GroupScoreCreate]


class GroupScoreUpdate(BaseModel):
    """Update schema for group score."""
    chest_number: str = Field(..., min_length=1, max_length=50)
    awarded_mark: int = Field(..., ge=0)
    grade: Optional[str] = Field(None, max_length=10)
    total_points: int = Field(..., ge=0)


class GroupScoreBulkUpdate(BaseModel):
    """Bulk update schema for group scores."""
    participants: List[GroupScoreUpdate]


class GroupScoreResponse(BaseModel):
    """Response schema for group score."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    event_name: str
    chest_number: str
    awarded_mark: int
    grade: Optional[str]
    total_points: int
    added_on: datetime


# Payment Schemas
class KalamelaPaymentCreate(BaseModel):
    """Create schema for Kalamela payment."""
    individual_events_count: int = Field(default=0, ge=0)
    group_events_count: int = Field(default=0, ge=0)


class KalamelaPaymentResponse(BaseModel):
    """Response schema for Kalamela payment."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    paid_by_id: int
    individual_events_count: int
    group_events_count: int
    total_amount_to_pay: int
    payment_proof_path: Optional[str]
    payment_status: PaymentStatus
    created_on: datetime


# Appeal Schemas
class AppealCreate(BaseModel):
    """Create schema for appeal."""
    participant_id: int = Field(..., gt=0)
    chest_number: str = Field(..., min_length=1, max_length=50)
    event_name: str = Field(..., min_length=1, max_length=255)
    statement: str = Field(..., min_length=10, max_length=1000)
    payment_type: str = Field(default="Appeal Fee", max_length=100)


class AppealReply(BaseModel):
    """Schema for appeal reply."""
    reply: str = Field(..., min_length=1, max_length=1000)


class AppealResponse(BaseModel):
    """Response schema for appeal."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    added_by_id: int
    chest_number: str
    event_name: str
    statement: str
    reply: Optional[str]
    status: AppealStatus
    created_on: datetime


class AppealPaymentResponse(BaseModel):
    """Response schema for appeal payment."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    appeal_id: int
    total_amount_to_pay: int
    payment_type: str
    payment_status: str
    created_on: datetime


# Exclude Members Schema
class ExcludeMemberCreate(BaseModel):
    """Schema for excluding a member."""
    members_id: int = Field(..., gt=0)


# Filter Schemas
class EventFilterSchema(BaseModel):
    """Schema for filtering events."""
    district_id: Optional[int] = None
    individual_event_id: Optional[int] = None
    group_event_id: Optional[int] = None


class SelectEventSchema(BaseModel):
    """Schema for selecting an event."""
    event_id: int = Field(..., gt=0)
    unit_id: Optional[int] = Field(None, gt=0)


class ChestNumberUpdate(BaseModel):
    """Schema for updating chest number."""
    chest_number: str = Field(..., min_length=1, max_length=50)


# Aggregated Response Schemas
class ParticipantDetail(BaseModel):
    """Participant detail for responses."""
    individual_event_participation_id: Optional[int] = None
    group_event_participation_id: Optional[int] = None
    individual_event_id: Optional[int] = None
    group_event_id: Optional[int] = None
    participant_id: int
    participant_name: str
    participant_unit: str
    participant_district: str
    participant_phone: Optional[str]
    participant_chest_number: Optional[str]
    participant_gender: Optional[str] = None


class TeamParticipants(BaseModel):
    """Team participants grouped together."""
    team_code: str
    participants: List[ParticipantDetail]
    total_count: int
    max_allowed_limit: Optional[int] = None


class EventParticipants(BaseModel):
    """Event with its participants."""
    event_name: str
    participants: List[ParticipantDetail]


class EventTeams(BaseModel):
    """Event with teams."""
    event_name: str
    teams: List[TeamParticipants]


class DistrictStatistics(BaseModel):
    """District statistics for events."""
    individual_events_count: int
    group_events_count: int
    individual_event_amount: int
    group_event_amount: int
    total_amount_to_pay: int
    payment_status: Optional[str]


class KalaprathibhaResult(BaseModel):
    """Kalaprathibha result schema."""
    participant_name: str
    participant_unit: str
    participant_district: str
    combined_score: int
    event_count: int


class UnitMemberWithAge(BaseModel):
    """Unit member with calculated age."""
    id: int
    name: str
    gender: Optional[str]
    dob: Optional[date]
    number: Optional[str]
    qualification: Optional[str]
    blood_group: Optional[str]
    age: Optional[int]
    unit_name: str
    is_excluded: bool = False


# Kalamela Rules Schemas
class RuleCategory(str, Enum):
    """Categories for Kalamela rules."""
    AGE_RESTRICTION = "age_restriction"
    PARTICIPATION_LIMIT = "participation_limit"
    FEE = "fee"


class KalamelaRuleCreate(BaseModel):
    """Create schema for Kalamela rule."""
    rule_key: str = Field(..., min_length=1, max_length=100)
    rule_category: RuleCategory
    rule_value: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class KalamelaRuleUpdate(BaseModel):
    """Update schema for Kalamela rule."""
    rule_value: Optional[str] = Field(None, min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class KalamelaRuleResponse(BaseModel):
    """Response schema for Kalamela rule."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    rule_key: str
    rule_category: RuleCategory
    rule_value: str
    display_name: str
    description: Optional[str]
    is_active: bool
    created_on: datetime
    updated_on: datetime
    updated_by_id: Optional[int]


class KalamelaRulesGrouped(BaseModel):
    """Grouped rules by category for easier frontend consumption."""
    age_restrictions: dict
    participation_limits: dict
    fees: dict
