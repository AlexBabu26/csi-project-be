from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.auth.models import UserType
from app.common.schemas import Timestamped


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    role: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginResponse(Token):
    """Login response with user routing information."""
    user_type: str
    redirect_url: str


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    user_type: UserType = UserType.UNIT
    unit_name_id: Optional[int] = None
    clergy_district_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UnitName(BaseModel):
    id: int
    clergy_district_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UnitRegistrationRequest(BaseModel):
    email: EmailStr
    phone_number: str
    first_name: str
    last_name: Optional[str] = None
    unit_name_id: int
    clergy_district_id: int
    password: str = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class LoginAuditRead(BaseModel):
    username: str
    success: bool
    timestamp: datetime

