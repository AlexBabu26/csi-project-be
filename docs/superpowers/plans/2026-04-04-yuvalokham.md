# Yuvalokham Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Yuvalokham magazine management module — independent auth, subscriptions, payments, magazines, complaints, and analytics — as a new domain package in the existing FastAPI monolith.

**Architecture:** Flat domain package at `app/yuvalokham/` with `models.py`, `schemas.py`, `service.py`, and `routers/{auth,user,admin}.py`. Independent JWT auth with `iss: "yuvalokham"` claim. All tables prefixed `ym_`. Async endpoints using `get_async_db`.

**Tech Stack:** FastAPI, SQLAlchemy 2.x (Mapped/mapped_column), Alembic, python-jose (JWT), bcrypt, Pydantic v2, Backblaze B2 (existing storage)

**Spec:** `docs/superpowers/specs/2026-04-04-yuvalokham-design.md`

---

## Chunk 1: Foundation — Models, Schemas, Auth

### Task 1: Package Scaffolding

**Files:**
- Create: `app/yuvalokham/__init__.py`
- Create: `app/yuvalokham/routers/__init__.py`

- [ ] **Step 1: Create package directories and init files**

```python
# app/yuvalokham/__init__.py
# (empty)
```

```python
# app/yuvalokham/routers/__init__.py
# (empty)
```

- [ ] **Step 2: Verify import works**

Run: `python -c "import app.yuvalokham; import app.yuvalokham.routers; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/yuvalokham/
git commit -m "chore: scaffold yuvalokham package structure"
```

---

### Task 2: Database Models

**Files:**
- Create: `app/yuvalokham/models.py`

All models use `Mapped[]` / `mapped_column()` pattern from SQLAlchemy 2.x, inheriting from `app.common.db.Base`. Follow the existing pattern in `app/auth/models.py` and `app/kalamela/models.py`.

- [ ] **Step 1: Create models.py with enums and all ORM models**

```python
# app/yuvalokham/models.py

import enum
from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    Integer, String, Text, Boolean, Date, DateTime, Numeric,
    ForeignKey, Enum as SAEnum, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base


# --- Enums ---

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


# --- Models ---

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
```

- [ ] **Step 2: Verify models import correctly**

Run: `python -c "from app.yuvalokham.models import YMUser, YMSubscription, YMMagazine; print('Models OK')"`
Expected: `Models OK`

- [ ] **Step 3: Commit**

```bash
git add app/yuvalokham/models.py
git commit -m "feat(yuvalokham): add all database models and enums"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `app/yuvalokham/schemas.py`

All schemas use Pydantic v2 with `model_config = ConfigDict(from_attributes=True)` for ORM-backed responses. Follow the existing `app/auth/schemas.py` pattern.

- [ ] **Step 1: Create schemas.py with all request/response models**

```python
# app/yuvalokham/schemas.py

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.yuvalokham.models import (
    YuvalokhamUserRole,
    YMPaymentStatus,
    SubscriptionStatus,
    ComplaintCategory,
    ComplaintStatus,
    MagazineStatus,
)


# --- Auth Schemas ---

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


# --- User Schemas ---

class YMUserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    role: YuvalokhamUserRole
    address: Optional[str] = None
    pincode: Optional[str] = None
    district_id: Optional[int] = None
    unit_id: Optional[int] = None
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


class YMAdminCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=8)


# --- Subscription Plan Schemas ---

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


# --- Subscription Schemas ---

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


# --- Payment Schemas ---

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


# --- Magazine Schemas ---

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


# --- Complaint Schemas ---

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


# --- QR Setting Schemas ---

class YMQrSettingResponse(BaseModel):
    id: int
    qr_image_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Analytics Schemas ---

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
```

- [ ] **Step 2: Verify schemas import correctly**

Run: `python -c "from app.yuvalokham.schemas import YMUserRegister, YMToken, YMSubscriptionResponse; print('Schemas OK')"`
Expected: `Schemas OK`

- [ ] **Step 3: Commit**

```bash
git add app/yuvalokham/schemas.py
git commit -m "feat(yuvalokham): add all Pydantic request/response schemas"
```

---

### Task 4: Service Layer — Auth + Dependencies

**Files:**
- Create: `app/yuvalokham/service.py`

The service is a single class `YuvalokhamService` with async static methods. Auth dependencies (`get_ym_current_user`, `get_ym_admin_user`) live at module level, following the pattern from `app/common/security.py` but using `ym_user` table and verifying `iss == "yuvalokham"`.

- [ ] **Step 1: Create service.py with auth dependencies and auth methods**

```python
# app/yuvalokham/service.py

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from dateutil.relativedelta import relativedelta
from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select, func, and_, or_, DateTime
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import get_settings
from app.common.db import get_async_db
from app.common.security import get_password_hash, verify_password
from app.common.storage import save_upload_file, delete_file, get_file_url
from app.yuvalokham.models import (
    YMUser, YMRefreshToken, YMSubscriptionPlan, YMSubscription,
    YMPayment, YMMagazine, YMComplaint, YMQrSetting,
    YuvalokhamUserRole, YMPaymentStatus, SubscriptionStatus,
    ComplaintStatus, MagazineStatus,
)
from app.yuvalokham import schemas as ym_schema

settings = get_settings()

ym_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/yuvalokham/auth/login")


# --- Token helpers (Yuvalokham-specific, adds iss claim) ---

def _create_ym_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": "yuvalokham",
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _create_ym_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "iss": "yuvalokham",
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _decode_ym_token(token: str, expected_type: str = "access") -> ym_schema.YMTokenPayload:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("iss") != "yuvalokham":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return ym_schema.YMTokenPayload(
            sub=payload.get("sub"), exp=payload.get("exp"),
            role=payload.get("role"), iss=payload.get("iss"),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- Auth dependencies ---

async def get_ym_current_user(
    token: str = Depends(ym_oauth2_scheme),
    db: AsyncSession = Depends(get_async_db),
) -> YMUser:
    payload = _decode_ym_token(token, "access")
    user = await db.get(YMUser, int(payload.sub))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def get_ym_admin_user(
    current_user: YMUser = Depends(get_ym_current_user),
) -> YMUser:
    if current_user.role != YuvalokhamUserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# --- Service class ---

class YuvalokhamService:

    # ========================
    # Auth
    # ========================

    @staticmethod
    async def register_user(db: AsyncSession, data: ym_schema.YMUserRegister) -> YMUser:
        existing = await db.execute(select(YMUser).where(YMUser.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        await YuvalokhamService._validate_district_unit(db, data.district_id, data.unit_id)

        user = YMUser(
            name=data.name, email=data.email, phone=data.phone,
            password_hash=get_password_hash(data.password),
            role=YuvalokhamUserRole.USER,
            address=data.address, pincode=data.pincode,
            district_id=data.district_id, unit_id=data.unit_id,
            parish_name=data.parish_name, is_csi_member=data.is_csi_member,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def login(db: AsyncSession, data: ym_schema.YMUserLogin) -> ym_schema.YMToken:
        result = await db.execute(select(YMUser).where(YMUser.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Revoke old refresh tokens
        old_tokens = await db.execute(
            select(YMRefreshToken).where(
                YMRefreshToken.user_id == user.id, YMRefreshToken.revoked == False  # noqa: E712
            )
        )
        for t in old_tokens.scalars().all():
            t.revoked = True

        access_token = _create_ym_access_token(user.id, user.role.value)
        refresh_token_str = _create_ym_refresh_token(user.id)

        db.add(YMRefreshToken(
            user_id=user.id, token=refresh_token_str,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        ))
        return ym_schema.YMToken(
            access_token=access_token, refresh_token=refresh_token_str, role=user.role.value,
        )

    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token_str: str) -> ym_schema.YMToken:
        payload = _decode_ym_token(refresh_token_str, "refresh")

        result = await db.execute(
            select(YMRefreshToken).where(
                YMRefreshToken.token == refresh_token_str,
                YMRefreshToken.revoked == False,  # noqa: E712
                YMRefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        db_token = result.scalar_one_or_none()
        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        user = await db.get(YMUser, db_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        db_token.revoked = True
        new_access = _create_ym_access_token(user.id, user.role.value)
        new_refresh = _create_ym_refresh_token(user.id)
        db.add(YMRefreshToken(
            user_id=user.id, token=new_refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        ))
        return ym_schema.YMToken(access_token=new_access, refresh_token=new_refresh, role=user.role.value)

    # ========================
    # User Profile
    # ========================

    @staticmethod
    async def _validate_district_unit(db: AsyncSession, district_id: Optional[int], unit_id: Optional[int]) -> None:
        if district_id and unit_id:
            from app.auth.models import UnitName
            unit = await db.get(UnitName, unit_id)
            if unit and unit.clergy_district_id != district_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unit does not belong to selected district",
                )

    @staticmethod
    async def update_profile(db: AsyncSession, user: YMUser, data: ym_schema.YMUserUpdate) -> YMUser:
        updates = data.model_dump(exclude_unset=True)
        district_id = updates.get("district_id", user.district_id)
        unit_id = updates.get("unit_id", user.unit_id)
        await YuvalokhamService._validate_district_unit(db, district_id, unit_id)
        for field, value in updates.items():
            setattr(user, field, value)
        await db.flush()
        return user

    # ========================
    # Subscription Plans
    # ========================

    @staticmethod
    async def get_active_plans(db: AsyncSession) -> List[YMSubscriptionPlan]:
        result = await db.execute(
            select(YMSubscriptionPlan).where(YMSubscriptionPlan.is_active == True).order_by(YMSubscriptionPlan.price)  # noqa: E712
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_plans(db: AsyncSession) -> List[YMSubscriptionPlan]:
        result = await db.execute(select(YMSubscriptionPlan).order_by(YMSubscriptionPlan.id))
        return list(result.scalars().all())

    @staticmethod
    async def create_plan(db: AsyncSession, data: ym_schema.YMPlanCreate) -> YMSubscriptionPlan:
        plan = YMSubscriptionPlan(**data.model_dump())
        db.add(plan)
        await db.flush()
        return plan

    @staticmethod
    async def update_plan(db: AsyncSession, plan_id: int, data: ym_schema.YMPlanUpdate) -> YMSubscriptionPlan:
        plan = await db.get(YMSubscriptionPlan, plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(plan, field, value)
        await db.flush()
        return plan

    @staticmethod
    async def toggle_plan(db: AsyncSession, plan_id: int) -> YMSubscriptionPlan:
        plan = await db.get(YMSubscriptionPlan, plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        plan.is_active = not plan.is_active
        await db.flush()
        return plan

    # ========================
    # Subscriptions
    # ========================

    @staticmethod
    async def subscribe(db: AsyncSession, user: YMUser, data: ym_schema.YMSubscribeRequest) -> YMSubscription:
        # Check for existing pending subscription
        existing = await db.execute(
            select(YMSubscription).where(
                YMSubscription.user_id == user.id,
                YMSubscription.status == SubscriptionStatus.PENDING_PAYMENT,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a pending subscription")

        plan = await db.get(YMSubscriptionPlan, data.plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or inactive")

        sub = YMSubscription(
            user_id=user.id, plan_id=plan.id,
            plan_name_snapshot=plan.name,
            plan_price_snapshot=plan.price,
            plan_duration_snapshot=plan.duration_months,
            status=SubscriptionStatus.PENDING_PAYMENT,
        )
        db.add(sub)
        await db.flush()
        return sub

    @staticmethod
    async def get_user_subscriptions(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20):
        stmt = select(YMSubscription).where(YMSubscription.user_id == user_id)
        count_result = await db.execute(select(func.count(YMSubscription.id)).select_from(stmt.subquery()))
        total = count_result.scalar()
        result = await db.execute(stmt.order_by(YMSubscription.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def get_active_subscription(db: AsyncSession, user_id: int) -> Optional[YMSubscription]:
        result = await db.execute(
            select(YMSubscription).where(
                YMSubscription.user_id == user_id,
                YMSubscription.status == SubscriptionStatus.ACTIVE,
                YMSubscription.end_date >= date.today(),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_subscriptions(
        db: AsyncSession, status_filter: Optional[str] = None,
        plan_id: Optional[int] = None, user_id: Optional[int] = None,
        skip: int = 0, limit: int = 20,
    ):
        stmt = select(YMSubscription)
        if status_filter:
            stmt = stmt.where(YMSubscription.status == status_filter)
        if plan_id:
            stmt = stmt.where(YMSubscription.plan_id == plan_id)
        if user_id:
            stmt = stmt.where(YMSubscription.user_id == user_id)

        count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar()

        result = await db.execute(stmt.order_by(YMSubscription.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    # ========================
    # Payments
    # ========================

    @staticmethod
    async def submit_payment(
        db: AsyncSession, user: YMUser, subscription_id: int, proof_file: UploadFile,
    ) -> YMPayment:
        sub = await db.get(YMSubscription, subscription_id)
        if not sub or sub.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        if sub.status != SubscriptionStatus.PENDING_PAYMENT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription is not pending payment")

        object_key, _ = save_upload_file(proof_file, "yuvalokham/payments")
        payment = YMPayment(
            user_id=user.id, subscription_id=sub.id,
            amount=sub.plan_price_snapshot,
            proof_file_url=object_key,
            status=YMPaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()
        return payment

    @staticmethod
    async def get_user_payments(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20):
        stmt = select(YMPayment).where(YMPayment.user_id == user_id)
        count_result = await db.execute(select(func.count(YMPayment.id)).select_from(stmt.subquery()))
        total = count_result.scalar()
        result = await db.execute(stmt.order_by(YMPayment.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def get_all_payments(
        db: AsyncSession, status_filter: Optional[str] = None, skip: int = 0, limit: int = 20,
    ):
        stmt = select(YMPayment)
        if status_filter:
            stmt = stmt.where(YMPayment.status == status_filter)
        count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar()
        result = await db.execute(stmt.order_by(YMPayment.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def approve_payment(db: AsyncSession, payment_id: int, admin: YMUser) -> YMPayment:
        payment = await db.get(YMPayment, payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.status != YMPaymentStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment is not pending")

        payment.status = YMPaymentStatus.APPROVED
        payment.reviewed_by = admin.id
        payment.reviewed_at = datetime.now(timezone.utc)

        # Activate subscription
        sub = await db.get(YMSubscription, payment.subscription_id)
        active_sub = await YuvalokhamService.get_active_subscription(db, sub.user_id)
        if active_sub and active_sub.id != sub.id:
            sub.start_date = active_sub.end_date
        else:
            sub.start_date = date.today()
        sub.end_date = sub.start_date + relativedelta(months=sub.plan_duration_snapshot)
        sub.status = SubscriptionStatus.ACTIVE

        await db.flush()
        return payment

    @staticmethod
    async def reject_payment(db: AsyncSession, payment_id: int, admin: YMUser, remarks: str) -> YMPayment:
        payment = await db.get(YMPayment, payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.status != YMPaymentStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment is not pending")

        payment.status = YMPaymentStatus.REJECTED
        payment.admin_remarks = remarks
        payment.reviewed_by = admin.id
        payment.reviewed_at = datetime.now(timezone.utc)
        # Subscription intentionally stays PENDING_PAYMENT so user can resubmit proof
        await db.flush()
        return payment

    # ========================
    # Magazines
    # ========================

    @staticmethod
    async def create_magazine(db: AsyncSession, data: ym_schema.YMMagazineCreate) -> YMMagazine:
        magazine = YMMagazine(**data.model_dump(), status=MagazineStatus.DRAFT)
        db.add(magazine)
        await db.flush()
        return magazine

    @staticmethod
    async def update_magazine(db: AsyncSession, mag_id: int, data: ym_schema.YMMagazineUpdate) -> YMMagazine:
        mag = await db.get(YMMagazine, mag_id)
        if not mag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(mag, field, value)
        await db.flush()
        return mag

    @staticmethod
    async def upload_magazine_files(
        db: AsyncSession, mag_id: int,
        cover: Optional[UploadFile] = None, pdf: Optional[UploadFile] = None,
    ) -> YMMagazine:
        mag = await db.get(YMMagazine, mag_id)
        if not mag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found")
        if cover:
            if mag.cover_image_url:
                delete_file(mag.cover_image_url)
            key, _ = save_upload_file(cover, "yuvalokham/magazines/covers")
            mag.cover_image_url = key
        if pdf:
            if mag.pdf_file_url:
                delete_file(mag.pdf_file_url)
            key, _ = save_upload_file(pdf, "yuvalokham/magazines/pdfs")
            mag.pdf_file_url = key
        await db.flush()
        return mag

    @staticmethod
    async def publish_magazine(db: AsyncSession, mag_id: int) -> YMMagazine:
        mag = await db.get(YMMagazine, mag_id)
        if not mag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found")
        mag.status = MagazineStatus.PUBLISHED
        mag.published_date = date.today()
        await db.flush()
        return mag

    @staticmethod
    async def delete_magazine(db: AsyncSession, mag_id: int) -> None:
        mag = await db.get(YMMagazine, mag_id)
        if not mag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found")
        if mag.status != MagazineStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft magazines can be deleted")
        if mag.cover_image_url:
            delete_file(mag.cover_image_url)
        if mag.pdf_file_url:
            delete_file(mag.pdf_file_url)
        await db.delete(mag)
        await db.flush()

    @staticmethod
    async def get_published_magazines(db: AsyncSession) -> List[YMMagazine]:
        result = await db.execute(
            select(YMMagazine).where(YMMagazine.status == MagazineStatus.PUBLISHED)
            .order_by(YMMagazine.published_date.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_magazines(db: AsyncSession, status_filter: Optional[str] = None):
        stmt = select(YMMagazine)
        if status_filter:
            stmt = stmt.where(YMMagazine.status == status_filter)
        result = await db.execute(stmt.order_by(YMMagazine.created_at.desc()))
        return list(result.scalars().all())

    # ========================
    # Complaints
    # ========================

    @staticmethod
    async def create_complaint(db: AsyncSession, user: YMUser, data: ym_schema.YMComplaintCreate) -> YMComplaint:
        complaint = YMComplaint(user_id=user.id, **data.model_dump())
        db.add(complaint)
        await db.flush()
        return complaint

    @staticmethod
    async def get_user_complaints(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20):
        stmt = select(YMComplaint).where(YMComplaint.user_id == user_id)
        count_result = await db.execute(select(func.count(YMComplaint.id)).select_from(stmt.subquery()))
        total = count_result.scalar()
        result = await db.execute(stmt.order_by(YMComplaint.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def get_all_complaints(
        db: AsyncSession, status_filter: Optional[str] = None,
        category: Optional[str] = None, skip: int = 0, limit: int = 20,
    ):
        stmt = select(YMComplaint)
        if status_filter:
            stmt = stmt.where(YMComplaint.status == status_filter)
        if category:
            stmt = stmt.where(YMComplaint.category == category)
        count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar()
        result = await db.execute(stmt.order_by(YMComplaint.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def respond_complaint(db: AsyncSession, complaint_id: int, admin: YMUser, response: str) -> YMComplaint:
        complaint = await db.get(YMComplaint, complaint_id)
        if not complaint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        if complaint.status != ComplaintStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complaint is not open")
        complaint.admin_response = response
        complaint.responded_by = admin.id
        complaint.responded_at = datetime.now(timezone.utc)
        complaint.status = ComplaintStatus.RESOLVED
        await db.flush()
        return complaint

    @staticmethod
    async def close_complaint(db: AsyncSession, complaint_id: int, admin: YMUser) -> YMComplaint:
        complaint = await db.get(YMComplaint, complaint_id)
        if not complaint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        if complaint.status != ComplaintStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complaint is not open")
        complaint.responded_by = admin.id
        complaint.responded_at = datetime.now(timezone.utc)
        complaint.status = ComplaintStatus.CLOSED
        await db.flush()
        return complaint

    # ========================
    # QR Settings
    # ========================

    @staticmethod
    async def get_qr_setting(db: AsyncSession) -> Optional[YMQrSetting]:
        return await db.get(YMQrSetting, 1)

    @staticmethod
    async def update_qr_setting(
        db: AsyncSession, admin: YMUser,
        qr_file: Optional[UploadFile] = None, description: Optional[str] = None,
    ) -> YMQrSetting:
        qr = await db.get(YMQrSetting, 1)
        if not qr:
            qr = YMQrSetting(id=1, updated_by=admin.id)
            db.add(qr)

        if qr_file:
            if qr.qr_image_url:
                delete_file(qr.qr_image_url)
            key, _ = save_upload_file(qr_file, "yuvalokham/qr")
            qr.qr_image_url = key

        if description is not None:
            qr.description = description

        qr.updated_by = admin.id
        await db.flush()
        return qr

    # ========================
    # Admin — User Management
    # ========================

    @staticmethod
    async def get_all_users(
        db: AsyncSession, search: Optional[str] = None,
        is_active: Optional[bool] = None, district_id: Optional[int] = None,
        skip: int = 0, limit: int = 20,
    ):
        stmt = select(YMUser).where(YMUser.role == YuvalokhamUserRole.USER)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(or_(YMUser.name.ilike(pattern), YMUser.email.ilike(pattern)))
        if is_active is not None:
            stmt = stmt.where(YMUser.is_active == is_active)
        if district_id:
            stmt = stmt.where(YMUser.district_id == district_id)

        count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar()
        result = await db.execute(stmt.order_by(YMUser.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def admin_update_user(db: AsyncSession, user_id: int, data: ym_schema.YMAdminUserUpdate) -> YMUser:
        user = await db.get(YMUser, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        updates = data.model_dump(exclude_unset=True)
        district_id = updates.get("district_id", user.district_id)
        unit_id = updates.get("unit_id", user.unit_id)
        await YuvalokhamService._validate_district_unit(db, district_id, unit_id)
        for field, value in updates.items():
            setattr(user, field, value)
        await db.flush()
        return user

    @staticmethod
    async def create_admin(db: AsyncSession, data: ym_schema.YMAdminCreate) -> YMUser:
        existing = await db.execute(select(YMUser).where(YMUser.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        admin = YMUser(
            name=data.name, email=data.email, phone=data.phone,
            password_hash=get_password_hash(data.password),
            role=YuvalokhamUserRole.ADMIN,
        )
        db.add(admin)
        await db.flush()
        return admin

    # ========================
    # Analytics
    # ========================

    @staticmethod
    async def get_analytics_summary(db: AsyncSession) -> ym_schema.YMAnalyticsSummary:
        total_users = (await db.execute(
            select(func.count(YMUser.id)).select_from(YMUser).where(YMUser.role == YuvalokhamUserRole.USER)
        )).scalar() or 0

        active_subs = (await db.execute(
            select(func.count(YMSubscription.id)).select_from(YMSubscription).where(
                YMSubscription.status == SubscriptionStatus.ACTIVE,
                YMSubscription.end_date >= date.today(),
            )
        )).scalar() or 0

        total_revenue = (await db.execute(
            select(func.coalesce(func.sum(YMPayment.amount), 0)).select_from(YMPayment).where(
                YMPayment.status == YMPaymentStatus.APPROVED,
            )
        )).scalar() or Decimal("0")

        pending_payments = (await db.execute(
            select(func.count(YMPayment.id)).select_from(YMPayment).where(YMPayment.status == YMPaymentStatus.PENDING)
        )).scalar() or 0

        open_complaints = (await db.execute(
            select(func.count(YMComplaint.id)).select_from(YMComplaint).where(YMComplaint.status == ComplaintStatus.OPEN)
        )).scalar() or 0

        return ym_schema.YMAnalyticsSummary(
            total_users=total_users, active_subscriptions=active_subs,
            total_revenue=total_revenue, pending_payments=pending_payments,
            open_complaints=open_complaints,
        )

    @staticmethod
    async def get_analytics_trends(db: AsyncSession, months: int = 12) -> List[ym_schema.YMTrendPoint]:
        cutoff = date.today() - relativedelta(months=months)
        trends = []

        for i in range(months):
            m_start = date.today() - relativedelta(months=months - 1 - i)
            m_start = m_start.replace(day=1)
            if i < months - 1:
                m_end = (m_start + relativedelta(months=1)) - timedelta(days=1)
            else:
                m_end = date.today()

            new_users = (await db.execute(
                select(func.count()).where(
                    YMUser.role == YuvalokhamUserRole.USER,
                    func.date(YMUser.created_at) >= m_start,
                    func.date(YMUser.created_at) <= m_end,
                )
            )).scalar() or 0

            new_subs = (await db.execute(
                select(func.count()).where(
                    YMSubscription.created_at >= datetime.combine(m_start, datetime.min.time()),
                    YMSubscription.created_at <= datetime.combine(m_end, datetime.max.time()),
                )
            )).scalar() or 0

            revenue = (await db.execute(
                select(func.coalesce(func.sum(YMPayment.amount), 0)).where(
                    YMPayment.status == YMPaymentStatus.APPROVED,
                    YMPayment.reviewed_at >= datetime.combine(m_start, datetime.min.time()),
                    YMPayment.reviewed_at <= datetime.combine(m_end, datetime.max.time()),
                )
            )).scalar() or Decimal("0")

            complaints = (await db.execute(
                select(func.count()).where(
                    func.date(YMComplaint.created_at) >= m_start,
                    func.date(YMComplaint.created_at) <= m_end,
                )
            )).scalar() or 0

            trends.append(ym_schema.YMTrendPoint(
                month=m_start.strftime("%Y-%m"), new_users=new_users,
                new_subscriptions=new_subs, revenue=revenue, complaints=complaints,
            ))

        return trends

    @staticmethod
    async def get_analytics_breakdowns(db: AsyncSession) -> ym_schema.YMAnalyticsBreakdowns:
        # Subscriptions by district (join subscription to user for district)
        district_result = await db.execute(
            select(YMUser.district_id, func.count(YMSubscription.id))
            .select_from(YMSubscription)
            .join(YMUser, YMSubscription.user_id == YMUser.id)
            .where(YMUser.district_id.is_not(None))
            .group_by(YMUser.district_id)
        )
        by_district = [{"district_id": r[0], "count": r[1]} for r in district_result.all()]

        # Plan popularity
        plan_result = await db.execute(
            select(YMSubscription.plan_name_snapshot, func.count(YMSubscription.id))
            .select_from(YMSubscription)
            .group_by(YMSubscription.plan_name_snapshot)
        )
        plan_pop = [{"plan": r[0], "count": r[1]} for r in plan_result.all()]

        # Complaint categories
        cat_result = await db.execute(
            select(YMComplaint.category, func.count(YMComplaint.id))
            .select_from(YMComplaint)
            .group_by(YMComplaint.category)
        )
        complaint_cats = [{"category": r[0], "count": r[1]} for r in cat_result.all()]

        # Renewal rate: users who had an expired sub AND created a new sub within 30 days of expiry
        from sqlalchemy.orm import aliased
        expired_sub = aliased(YMSubscription)
        renewed_sub = aliased(YMSubscription)

        expired_count = (await db.execute(
            select(func.count(func.distinct(expired_sub.user_id)))
            .select_from(expired_sub)
            .where(expired_sub.end_date < date.today(), expired_sub.end_date.is_not(None))
        )).scalar() or 0

        renewed_count = 0
        if expired_count > 0:
            renewed_result = await db.execute(
                select(func.count(func.distinct(expired_sub.user_id)))
                .select_from(expired_sub)
                .where(
                    expired_sub.end_date < date.today(),
                    expired_sub.end_date.is_not(None),
                    expired_sub.user_id.in_(
                        select(renewed_sub.user_id)
                        .where(
                            renewed_sub.user_id == expired_sub.user_id,
                            renewed_sub.created_at >= func.cast(expired_sub.end_date, DateTime),
                            renewed_sub.created_at <= func.cast(expired_sub.end_date, DateTime) + timedelta(days=30),
                            renewed_sub.id != expired_sub.id,
                        )
                    ),
                )
            )
            renewed_count = renewed_result.scalar() or 0

        rate = (renewed_count / expired_count * 100) if expired_count > 0 else 0.0

        return ym_schema.YMAnalyticsBreakdowns(
            by_district=by_district, plan_popularity=plan_pop,
            complaint_categories=complaint_cats, renewal_rate=round(rate, 2),
        )

    @staticmethod
    async def get_expiring_subscriptions(db: AsyncSession, days: int = 30) -> List[ym_schema.YMExpiringSubscription]:
        cutoff = date.today() + timedelta(days=days)
        result = await db.execute(
            select(YMSubscription, YMUser)
            .join(YMUser, YMSubscription.user_id == YMUser.id)
            .where(
                YMSubscription.status == SubscriptionStatus.ACTIVE,
                YMSubscription.end_date >= date.today(),
                YMSubscription.end_date <= cutoff,
            )
            .order_by(YMSubscription.end_date)
        )
        rows = result.all()
        return [
            ym_schema.YMExpiringSubscription(
                subscription_id=sub.id, user_id=u.id, user_name=u.name,
                user_email=u.email, plan_name=sub.plan_name_snapshot,
                end_date=sub.end_date, days_remaining=(sub.end_date - date.today()).days,
            )
            for sub, u in rows
        ]
```

- [ ] **Step 2: Add `python-dateutil` dependency (for `relativedelta`)**

Check if already in requirements.txt. If not:

Run: `pip show python-dateutil` — if not found, run `pip install python-dateutil`.

Add `python-dateutil` to `requirements.txt` if missing.

- [ ] **Step 3: Verify service imports**

Run: `python -c "from app.yuvalokham.service import YuvalokhamService, get_ym_current_user, get_ym_admin_user; print('Service OK')"`
Expected: `Service OK`

- [ ] **Step 4: Commit**

```bash
git add app/yuvalokham/service.py requirements.txt
git commit -m "feat(yuvalokham): add service layer with auth, business logic, and analytics"
```

---

## Chunk 2: Routers and Integration

### Task 5: Auth Router

**Files:**
- Create: `app/yuvalokham/routers/auth.py`

- [ ] **Step 1: Create auth router**

```python
# app/yuvalokham/routers/auth.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService

router = APIRouter()


@router.post("/register", response_model=ym_schema.YMUserResponse, status_code=201)
async def register(data: ym_schema.YMUserRegister, db: AsyncSession = Depends(get_async_db)):
    user = await YuvalokhamService.register_user(db, data)
    return user


@router.post("/login", response_model=ym_schema.YMToken)
async def login(data: ym_schema.YMUserLogin, db: AsyncSession = Depends(get_async_db)):
    return await YuvalokhamService.login(db, data)


@router.post("/refresh", response_model=ym_schema.YMToken)
async def refresh(data: ym_schema.YMRefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    return await YuvalokhamService.refresh_token(db, data.refresh_token)
```

- [ ] **Step 2: Commit**

```bash
git add app/yuvalokham/routers/auth.py
git commit -m "feat(yuvalokham): add auth router (register, login, refresh)"
```

---

### Task 6: User Router

**Files:**
- Create: `app/yuvalokham/routers/user.py`

- [ ] **Step 1: Create user router**

```python
# app/yuvalokham/routers/user.py

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.common.storage import get_file_url
from app.common.schemas import Paginated
from app.yuvalokham.models import YMUser
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService, get_ym_current_user

router = APIRouter()


@router.get("/profile", response_model=ym_schema.YMUserResponse)
async def get_profile(current_user: YMUser = Depends(get_ym_current_user)):
    return current_user


@router.put("/profile", response_model=ym_schema.YMUserResponse)
async def update_profile(
    data: ym_schema.YMUserUpdate,
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.update_profile(db, current_user, data)


@router.get("/plans", response_model=List[ym_schema.YMPlanResponse])
async def list_plans(db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_current_user)):
    return await YuvalokhamService.get_active_plans(db)


@router.post("/subscribe", response_model=ym_schema.YMSubscriptionResponse, status_code=201)
async def subscribe(
    data: ym_schema.YMSubscribeRequest,
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.subscribe(db, current_user, data)


@router.get("/subscriptions", response_model=Paginated[ym_schema.YMSubscriptionResponse])
async def list_subscriptions(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    items, total = await YuvalokhamService.get_user_subscriptions(db, current_user.id, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)


@router.get("/subscriptions/active", response_model=Optional[ym_schema.YMSubscriptionResponse])
async def active_subscription(
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.get_active_subscription(db, current_user.id)


@router.get("/qr-code", response_model=Optional[ym_schema.YMQrSettingResponse])
async def get_qr_code(
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_current_user),
):
    qr = await YuvalokhamService.get_qr_setting(db)
    if qr and qr.qr_image_url:
        qr.qr_image_url = get_file_url(qr.qr_image_url)
    return qr


@router.post("/payments", response_model=ym_schema.YMPaymentResponse, status_code=201)
async def submit_payment(
    subscription_id: int = Form(...),
    proof: UploadFile = File(...),
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.submit_payment(db, current_user, subscription_id, proof)


@router.get("/payments", response_model=Paginated[ym_schema.YMPaymentResponse])
async def list_payments(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    items, total = await YuvalokhamService.get_user_payments(db, current_user.id, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)


@router.get("/magazines", response_model=List[ym_schema.YMMagazineResponse])
async def list_magazines(
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    magazines = await YuvalokhamService.get_published_magazines(db)
    active_sub = await YuvalokhamService.get_active_subscription(db, current_user.id)
    result = []
    for m in magazines:
        resp = ym_schema.YMMagazineResponse.model_validate(m)
        if active_sub and m.pdf_file_url:
            resp.pdf_file_url = get_file_url(m.pdf_file_url)
        else:
            resp.pdf_file_url = None
        if m.cover_image_url:
            resp.cover_image_url = get_file_url(m.cover_image_url)
        result.append(resp)
    return result


@router.get("/magazines/{mag_id}", response_model=ym_schema.YMMagazineResponse)
async def get_magazine(
    mag_id: int,
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    from app.yuvalokham.models import YMMagazine, MagazineStatus
    from fastapi import HTTPException, status
    mag = await db.get(YMMagazine, mag_id)
    if not mag or mag.status != MagazineStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found")
    resp = ym_schema.YMMagazineResponse.model_validate(mag)
    active_sub = await YuvalokhamService.get_active_subscription(db, current_user.id)
    if active_sub and mag.pdf_file_url:
        resp.pdf_file_url = get_file_url(mag.pdf_file_url)
    else:
        resp.pdf_file_url = None
    if mag.cover_image_url:
        resp.cover_image_url = get_file_url(mag.cover_image_url)
    return resp


@router.post("/complaints", response_model=ym_schema.YMComplaintResponse, status_code=201)
async def create_complaint(
    data: ym_schema.YMComplaintCreate,
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.create_complaint(db, current_user, data)


@router.get("/complaints", response_model=Paginated[ym_schema.YMComplaintResponse])
async def list_complaints(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    items, total = await YuvalokhamService.get_user_complaints(db, current_user.id, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)
```

- [ ] **Step 2: Commit**

```bash
git add app/yuvalokham/routers/user.py
git commit -m "feat(yuvalokham): add user router (profile, subscriptions, payments, magazines, complaints)"
```

---

### Task 7: Admin Router

**Files:**
- Create: `app/yuvalokham/routers/admin.py`

- [ ] **Step 1: Create admin router**

```python
# app/yuvalokham/routers/admin.py

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.common.storage import get_file_url
from app.common.schemas import Paginated
from app.yuvalokham.models import YMUser
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService, get_ym_admin_user

router = APIRouter()


# --- Users ---

@router.get("/users", response_model=Paginated[ym_schema.YMUserResponse])
async def list_users(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    district_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    items, total = await YuvalokhamService.get_all_users(db, search, is_active, district_id, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)


@router.get("/users/{user_id}", response_model=ym_schema.YMUserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user)):
    user = await db.get(YMUser, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=ym_schema.YMUserResponse)
async def update_user(
    user_id: int,
    data: ym_schema.YMAdminUserUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.admin_update_user(db, user_id, data)


@router.post("/admins", response_model=ym_schema.YMUserResponse, status_code=201)
async def create_admin(
    data: ym_schema.YMAdminCreate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.create_admin(db, data)


# --- Subscriptions ---

@router.get("/subscriptions", response_model=Paginated[ym_schema.YMSubscriptionResponse])
async def list_subscriptions(
    status_filter: Optional[str] = Query(None, alias="status"),
    plan_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    items, total = await YuvalokhamService.get_all_subscriptions(db, status_filter, plan_id, user_id, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)


# --- Plans ---

@router.get("/plans", response_model=List[ym_schema.YMPlanResponse])
async def list_plans(db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user)):
    return await YuvalokhamService.get_all_plans(db)


@router.post("/plans", response_model=ym_schema.YMPlanResponse, status_code=201)
async def create_plan(
    data: ym_schema.YMPlanCreate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.create_plan(db, data)


@router.put("/plans/{plan_id}", response_model=ym_schema.YMPlanResponse)
async def update_plan(
    plan_id: int, data: ym_schema.YMPlanUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.update_plan(db, plan_id, data)


@router.patch("/plans/{plan_id}/toggle", response_model=ym_schema.YMPlanResponse)
async def toggle_plan(
    plan_id: int, db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.toggle_plan(db, plan_id)


# --- Payments ---

@router.get("/payments", response_model=Paginated[ym_schema.YMPaymentResponse])
async def list_payments(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    items, total = await YuvalokhamService.get_all_payments(db, status_filter, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)


@router.patch("/payments/{payment_id}/approve", response_model=ym_schema.YMPaymentResponse)
async def approve_payment(
    payment_id: int,
    admin: YMUser = Depends(get_ym_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.approve_payment(db, payment_id, admin)


@router.patch("/payments/{payment_id}/reject", response_model=ym_schema.YMPaymentResponse)
async def reject_payment(
    payment_id: int,
    data: ym_schema.YMPaymentReject,
    admin: YMUser = Depends(get_ym_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.reject_payment(db, payment_id, admin, data.remarks)


# --- Magazines ---

@router.get("/magazines", response_model=List[ym_schema.YMMagazineResponse])
async def list_magazines(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    mags = await YuvalokhamService.get_all_magazines(db, status_filter)
    result = []
    for m in mags:
        resp = ym_schema.YMMagazineResponse.model_validate(m)
        if m.cover_image_url:
            resp.cover_image_url = get_file_url(m.cover_image_url)
        if m.pdf_file_url:
            resp.pdf_file_url = get_file_url(m.pdf_file_url)
        result.append(resp)
    return result


@router.post("/magazines", response_model=ym_schema.YMMagazineResponse, status_code=201)
async def create_magazine(
    data: ym_schema.YMMagazineCreate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.create_magazine(db, data)


@router.put("/magazines/{mag_id}", response_model=ym_schema.YMMagazineResponse)
async def update_magazine(
    mag_id: int, data: ym_schema.YMMagazineUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.update_magazine(db, mag_id, data)


@router.post("/magazines/{mag_id}/files", response_model=ym_schema.YMMagazineResponse)
async def upload_magazine_files(
    mag_id: int,
    cover: Optional[UploadFile] = File(None),
    pdf: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.upload_magazine_files(db, mag_id, cover, pdf)


@router.patch("/magazines/{mag_id}/publish", response_model=ym_schema.YMMagazineResponse)
async def publish_magazine(
    mag_id: int, db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.publish_magazine(db, mag_id)


@router.delete("/magazines/{mag_id}", status_code=204)
async def delete_magazine(
    mag_id: int, db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user),
):
    await YuvalokhamService.delete_magazine(db, mag_id)


# --- Complaints ---

@router.get("/complaints", response_model=Paginated[ym_schema.YMComplaintResponse])
async def list_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    items, total = await YuvalokhamService.get_all_complaints(db, status_filter, category, skip, limit)
    return Paginated(items=items, total=total, page=skip // limit + 1, size=limit)


@router.patch("/complaints/{complaint_id}/respond", response_model=ym_schema.YMComplaintResponse)
async def respond_complaint(
    complaint_id: int, data: ym_schema.YMComplaintRespond,
    admin: YMUser = Depends(get_ym_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.respond_complaint(db, complaint_id, admin, data.response)


@router.patch("/complaints/{complaint_id}/close", response_model=ym_schema.YMComplaintResponse)
async def close_complaint(
    complaint_id: int,
    admin: YMUser = Depends(get_ym_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.close_complaint(db, complaint_id, admin)


# --- QR Settings ---

@router.get("/qr-settings", response_model=Optional[ym_schema.YMQrSettingResponse])
async def get_qr_settings(db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user)):
    qr = await YuvalokhamService.get_qr_setting(db)
    if qr and qr.qr_image_url:
        qr.qr_image_url = get_file_url(qr.qr_image_url)
    return qr


@router.put("/qr-settings", response_model=ym_schema.YMQrSettingResponse)
async def update_qr_settings(
    qr_image: Optional[UploadFile] = File(None),
    description: Optional[str] = Form(None),
    admin: YMUser = Depends(get_ym_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await YuvalokhamService.update_qr_setting(db, admin, qr_image, description)


# --- Analytics ---

@router.get("/analytics/summary", response_model=ym_schema.YMAnalyticsSummary)
async def analytics_summary(db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user)):
    return await YuvalokhamService.get_analytics_summary(db)


@router.get("/analytics/trends", response_model=List[ym_schema.YMTrendPoint])
async def analytics_trends(
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.get_analytics_trends(db, months)


@router.get("/analytics/breakdowns", response_model=ym_schema.YMAnalyticsBreakdowns)
async def analytics_breakdowns(db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user)):
    return await YuvalokhamService.get_analytics_breakdowns(db)


@router.get("/analytics/expiring", response_model=List[ym_schema.YMExpiringSubscription])
async def analytics_expiring(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    return await YuvalokhamService.get_expiring_subscriptions(db, days)
```

- [ ] **Step 2: Commit**

```bash
git add app/yuvalokham/routers/admin.py
git commit -m "feat(yuvalokham): add admin router (users, plans, payments, magazines, complaints, QR, analytics)"
```

---

### Task 8: Main App & Alembic Integration

**Files:**
- Modify: `main.py` (add 3 router includes)
- Modify: `alembic/env.py` (add model import)

- [ ] **Step 1: Register Yuvalokham routers in main.py**

Add after the existing kalamela router includes (line 47):

```python
from app.yuvalokham.routers import auth as ym_auth, user as ym_user, admin as ym_admin
```

And in the router section:

```python
app.include_router(ym_auth.router, prefix="/api/yuvalokham/auth", tags=["yuvalokham-auth"])
app.include_router(ym_user.router, prefix="/api/yuvalokham/user", tags=["yuvalokham-user"])
app.include_router(ym_admin.router, prefix="/api/yuvalokham/admin", tags=["yuvalokham-admin"])
```

- [ ] **Step 2: Add model import to alembic/env.py**

Add after `import app.admin.models  # noqa` (line 13):

```python
import app.yuvalokham.models  # noqa
```

- [ ] **Step 3: Verify server starts**

Run: `python -c "from main import app; print(f'Routes: {len(app.routes)}')"` 
Expected: no import errors, route count increases

- [ ] **Step 4: Commit**

```bash
git add main.py alembic/env.py
git commit -m "feat(yuvalokham): register routers in main.py and models in alembic"
```

---

### Task 9: Database Migration

**Files:**
- Create: `alembic/versions/<auto>_create_yuvalokham_tables.py` (autogenerated)

- [ ] **Step 1: Generate migration**

Run: `alembic revision --autogenerate -m "create yuvalokham tables"`

Verify the generated migration contains `create_table` for: `ym_user`, `ym_refresh_token`, `ym_subscription_plan`, `ym_subscription`, `ym_payment`, `ym_magazine`, `ym_complaint`, `ym_qr_setting`.

- [ ] **Step 2: Review migration file**

Open the generated file in `alembic/versions/`. Verify:
- All 8 tables present with correct columns.
- Foreign keys reference correct tables.
- Enum types are created.
- `downgrade()` drops tables in correct order (reverse of creation).

- [ ] **Step 3: Apply migration**

Run: `alembic upgrade head`
Expected: Migration applies without errors.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/
git commit -m "feat(yuvalokham): add database migration for all ym_ tables"
```

---

### Task 10: Seed Initial Admin

**Files:**
- Create: `scripts/seed_ym_admin.py`

- [ ] **Step 1: Create seed script**

```python
# scripts/seed_ym_admin.py

"""Seed the first Yuvalokham admin user."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.db import session_scope
from app.common.security import get_password_hash
from app.yuvalokham.models import YMUser, YuvalokhamUserRole


def seed():
    with session_scope() as db:
        existing = db.query(YMUser).filter(
            YMUser.role == YuvalokhamUserRole.ADMIN
        ).first()
        if existing:
            print(f"Admin already exists: {existing.email}")
            return

        admin = YMUser(
            name="Yuvalokham Admin",
            email="yuvalokham.admin@csi.org",
            phone="0000000000",
            password_hash=get_password_hash("admin@123"),
            role=YuvalokhamUserRole.ADMIN,
        )
        db.add(admin)
        print(f"Created admin: {admin.email} (password: admin@123)")
        print("⚠ Change the password immediately after first login!")


if __name__ == "__main__":
    seed()
```

- [ ] **Step 2: Run seed**

Run: `python scripts/seed_ym_admin.py`
Expected: `Created admin: yuvalokham.admin@csi.org`

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_ym_admin.py
git commit -m "feat(yuvalokham): add admin seed script"
```

---

### Task 11: Smoke Test — Start Server & Hit Health + Auth

- [ ] **Step 1: Start server**

Run: `python main.py` (or `uvicorn main:app --reload`)
Expected: Server starts on port 8000 without import errors.

- [ ] **Step 2: Test registration**

Run:
```bash
curl -X POST http://localhost:8000/api/yuvalokham/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","phone":"1234567890","password":"testpass123"}'
```
Expected: 201 with user JSON.

- [ ] **Step 3: Test login**

Run:
```bash
curl -X POST http://localhost:8000/api/yuvalokham/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```
Expected: 200 with `access_token`, `refresh_token`, `role: "user"`.

- [ ] **Step 4: Test admin login**

Run:
```bash
curl -X POST http://localhost:8000/api/yuvalokham/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"yuvalokham.admin@csi.org","password":"admin@123"}'
```
Expected: 200 with `role: "admin"`.

- [ ] **Step 5: Check Swagger docs**

Open `http://localhost:8000/docs` in browser. Verify Yuvalokham tags (`yuvalokham-auth`, `yuvalokham-user`, `yuvalokham-admin`) appear with all endpoints.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat(yuvalokham): complete magazine management module — auth, subscriptions, payments, magazines, complaints, analytics"
```
