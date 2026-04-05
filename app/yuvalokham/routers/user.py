# app/yuvalokham/routers/user.py

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.common.storage import get_file_url
from app.common.schemas import Paginated
from app.yuvalokham.models import YMUser
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService, get_ym_current_user, _build_user_response

router = APIRouter()


def _payment_response(p) -> ym_schema.YMPaymentResponse:
    resp = ym_schema.YMPaymentResponse.model_validate(p)
    if p.proof_file_url:
        resp.proof_file_url = get_file_url(p.proof_file_url)
    return resp


@router.get("/profile", response_model=ym_schema.YMUserResponse)
async def get_profile(current_user: YMUser = Depends(get_ym_current_user)):
    return _build_user_response(current_user)


@router.put("/profile", response_model=ym_schema.YMUserResponse)
async def update_profile(
    data: ym_schema.YMUserUpdate,
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    user = await YuvalokhamService.update_profile(db, current_user, data)
    return _build_user_response(user)


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
    if not qr:
        return None
    resp = ym_schema.YMQrSettingResponse.model_validate(qr)
    if qr.qr_image_url:
        resp.qr_image_url = get_file_url(qr.qr_image_url)
    return resp


@router.post("/payments", response_model=ym_schema.YMPaymentResponse, status_code=201)
async def submit_payment(
    subscription_id: int = Form(...),
    proof: UploadFile = File(...),
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    payment = await YuvalokhamService.submit_payment(db, current_user, subscription_id, proof)
    return _payment_response(payment)


@router.get("/payments", response_model=Paginated[ym_schema.YMPaymentResponse])
async def list_payments(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    current_user: YMUser = Depends(get_ym_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    items, total = await YuvalokhamService.get_user_payments(db, current_user.id, skip, limit)
    return Paginated(items=[_payment_response(p) for p in items], total=total, page=skip // limit + 1, size=limit)


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
