# app/yuvalokham/routers/admin.py

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.common.storage import get_file_url
from app.common.schemas import Paginated
from app.yuvalokham.models import YMUser
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService, get_ym_admin_user, _build_user_response

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
    return Paginated(items=[_build_user_response(u) for u in items], total=total, page=skip // limit + 1, size=limit)


@router.get("/users/{user_id}", response_model=ym_schema.YMUserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db), _: YMUser = Depends(get_ym_admin_user)):
    user = await db.get(YMUser, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _build_user_response(user)


@router.put("/users/{user_id}", response_model=ym_schema.YMUserResponse)
async def update_user(
    user_id: int,
    data: ym_schema.YMAdminUserUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    user = await YuvalokhamService.admin_update_user(db, user_id, data)
    return _build_user_response(user)


@router.patch("/users/{user_id}/reset-password", response_model=ym_schema.YMUserResponse)
async def reset_user_password(
    user_id: int,
    data: ym_schema.YMAdminResetPassword,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    user = await YuvalokhamService.admin_reset_password(db, user_id, data.new_password)
    return _build_user_response(user)


@router.post("/admins", response_model=ym_schema.YMUserResponse, status_code=201)
async def create_admin(
    data: ym_schema.YMAdminCreate,
    db: AsyncSession = Depends(get_async_db),
    _: YMUser = Depends(get_ym_admin_user),
):
    admin = await YuvalokhamService.create_admin(db, data)
    return _build_user_response(admin)


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
    mag = await YuvalokhamService.upload_magazine_files(db, mag_id, cover, pdf)
    resp = ym_schema.YMMagazineResponse.model_validate(mag)
    if mag.cover_image_url:
        resp.cover_image_url = get_file_url(mag.cover_image_url)
    if mag.pdf_file_url:
        resp.pdf_file_url = get_file_url(mag.pdf_file_url)
    return resp


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
