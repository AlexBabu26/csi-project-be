# app/yuvalokham/service.py

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from app.common.datetime_utils import now_ist, today_ist

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

def _build_user_response(user: YMUser) -> ym_schema.YMUserResponse:
    data = ym_schema.YMUserResponse.model_validate(user)
    data.district_name = user.district.name if user.district else None
    data.unit_name = user.unit.name if user.unit else None
    return data


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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The username or password you entered is incorrect. Please try again.",
            )

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
                YMSubscription.end_date >= today_ist(),
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
        payment.reviewed_at = now_ist()

        # Activate subscription
        sub = await db.get(YMSubscription, payment.subscription_id)
        active_sub = await YuvalokhamService.get_active_subscription(db, sub.user_id)
        if active_sub and active_sub.id != sub.id:
            sub.start_date = active_sub.end_date
        else:
            sub.start_date = today_ist()
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
        payment.reviewed_at = now_ist()
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
            key, _ = save_upload_file(cover, "yuvalokham/magazines/covers", max_size_mb=10)
            mag.cover_image_url = key
        if pdf:
            if mag.pdf_file_url:
                delete_file(mag.pdf_file_url)
            key, _ = save_upload_file(pdf, "yuvalokham/magazines/pdfs", max_size_mb=50)
            mag.pdf_file_url = key
        await db.flush()
        return mag

    @staticmethod
    async def publish_magazine(db: AsyncSession, mag_id: int) -> YMMagazine:
        mag = await db.get(YMMagazine, mag_id)
        if not mag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found")
        mag.status = MagazineStatus.PUBLISHED
        mag.published_date = today_ist()
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
        complaint.responded_at = now_ist()
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
        complaint.responded_at = now_ist()
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
    async def admin_reset_password(db: AsyncSession, user_id: int, new_password: str) -> YMUser:
        user = await db.get(YMUser, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.password_hash = get_password_hash(new_password)
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
                YMSubscription.end_date >= today_ist(),
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
        cutoff = today_ist() - relativedelta(months=months)
        trends = []

        for i in range(months):
            m_start = today_ist() - relativedelta(months=months - 1 - i)
            m_start = m_start.replace(day=1)
            if i < months - 1:
                m_end = (m_start + relativedelta(months=1)) - timedelta(days=1)
            else:
                m_end = today_ist()

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
            .where(expired_sub.end_date < today_ist(), expired_sub.end_date.is_not(None))
        )).scalar() or 0

        renewed_count = 0
        if expired_count > 0:
            renewed_result = await db.execute(
                select(func.count(func.distinct(expired_sub.user_id)))
                .select_from(expired_sub)
                .where(
                    expired_sub.end_date < today_ist(),
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
        cutoff = today_ist() + timedelta(days=days)
        result = await db.execute(
            select(YMSubscription, YMUser)
            .join(YMUser, YMSubscription.user_id == YMUser.id)
            .where(
                YMSubscription.status == SubscriptionStatus.ACTIVE,
                YMSubscription.end_date >= today_ist(),
                YMSubscription.end_date <= cutoff,
            )
            .order_by(YMSubscription.end_date)
        )
        rows = result.all()
        return [
            ym_schema.YMExpiringSubscription(
                subscription_id=sub.id, user_id=u.id, user_name=u.name,
                user_email=u.email, plan_name=sub.plan_name_snapshot,
                end_date=sub.end_date, days_remaining=(sub.end_date - today_ist()).days,
            )
            for sub, u in rows
        ]
