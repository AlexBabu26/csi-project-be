from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.common.phone_utils import normalize_optional_phone, validate_and_normalize_phone

from app.yuvalokham.models import (
    YuvalokhamUserRole,
    YMPaymentStatus,
    SubscriptionStatus,
    ComplaintCategory,
    ComplaintStatus,
    MagazineStatus,
)


# --- Lookup ---

class YMDistrictItem(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class YMUnitItem(BaseModel):
    id: int
    name: str
    clergy_district_id: int
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---

class YMUserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=8)
    address: Optional[str] = None
    pincode: Optional[str] = Field(None, max_length=10)
    district_id: Optional[int] = None
    unit_id: Optional[int] = None
    parish_name: Optional[str] = Field(None, max_length=255)
    is_csi_member: bool = False

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return validate_and_normalize_phone(v)


class YMUserLogin(BaseModel):
    email: str
    password: str


class YMToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class YMRefreshTokenRequest(BaseModel):
    refresh_token: str


class YMTokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    role: Optional[str] = None
    iss: Optional[str] = None


# --- User ---

class YMUserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    role: YuvalokhamUserRole
    address: Optional[str] = None
    pincode: Optional[str] = None
    district_id: Optional[int] = None
    district_name: Optional[str] = None
    unit_id: Optional[int] = None
    unit_name: Optional[str] = None
    parish_name: Optional[str] = None
    is_csi_member: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class YMUserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=5, max_length=20)
    address: Optional[str] = None
    pincode: Optional[str] = Field(None, max_length=10)
    district_id: Optional[int] = None
    unit_id: Optional[int] = None
    parish_name: Optional[str] = Field(None, max_length=255)
    is_csi_member: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_phone(v)


class YMAdminUserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=5, max_length=20)
    address: Optional[str] = None
    pincode: Optional[str] = Field(None, max_length=10)
    district_id: Optional[int] = None
    unit_id: Optional[int] = None
    parish_name: Optional[str] = Field(None, max_length=255)
    is_csi_member: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_phone(v)


class YMAdminResetPassword(BaseModel):
    new_password: str = Field(min_length=8)


class YMAdminCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=8)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return validate_and_normalize_phone(v)


# --- Subscription Plan ---

class YMPlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    duration_months: int = Field(gt=0)
    price: Decimal = Field(gt=0, decimal_places=2)
    description: Optional[str] = None


class YMPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    duration_months: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None


class YMPlanResponse(BaseModel):
    id: int
    name: str
    duration_months: int
    price: Decimal
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Subscription ---

class YMSubscribeRequest(BaseModel):
    plan_id: int


class YMSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    plan_name_snapshot: str
    plan_price_snapshot: Decimal
    plan_duration_snapshot: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: SubscriptionStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Payment ---

class YMPaymentResponse(BaseModel):
    id: int
    user_id: int
    subscription_id: int
    amount: Decimal
    proof_file_url: str
    status: YMPaymentStatus
    admin_remarks: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class YMPaymentReject(BaseModel):
    remarks: str = Field(min_length=1)


# --- Magazine ---

class YMMagazineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    issue_number: Optional[str] = Field(None, max_length=50)
    volume: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class YMMagazineUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    issue_number: Optional[str] = Field(None, max_length=50)
    volume: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class YMMagazineResponse(BaseModel):
    id: int
    title: str
    issue_number: Optional[str] = None
    volume: Optional[str] = None
    cover_image_url: Optional[str] = None
    pdf_file_url: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[date] = None
    status: MagazineStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Complaint ---

class YMComplaintCreate(BaseModel):
    category: ComplaintCategory
    subject: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)


class YMComplaintResponse(BaseModel):
    id: int
    user_id: int
    category: ComplaintCategory
    subject: str
    description: str
    status: ComplaintStatus
    admin_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class YMComplaintRespond(BaseModel):
    response: str = Field(min_length=1)


# --- QR Setting ---

class YMQrSettingResponse(BaseModel):
    id: int
    qr_image_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Analytics ---

class YMAnalyticsSummary(BaseModel):
    total_users: int
    active_subscriptions: int
    total_revenue: Decimal
    pending_payments: int
    open_complaints: int


class YMTrendPoint(BaseModel):
    month: str
    new_users: int
    new_subscriptions: int
    revenue: Decimal
    complaints: int


class YMAnalyticsBreakdowns(BaseModel):
    by_district: list
    plan_popularity: list
    complaint_categories: list
    renewal_rate: float


class YMExpiringSubscription(BaseModel):
    subscription_id: int
    user_id: int
    user_name: str
    user_email: str
    plan_name: str
    end_date: date
    days_remaining: int
