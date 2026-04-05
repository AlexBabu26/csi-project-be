# app/yuvalokham/routers/auth.py

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.auth.models import ClergyDistrict, UnitName
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService, _build_user_response

router = APIRouter()


@router.get("/districts", response_model=List[ym_schema.YMDistrictItem])
async def list_districts(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(ClergyDistrict).order_by(ClergyDistrict.name))
    return result.scalars().all()


@router.get("/units", response_model=List[ym_schema.YMUnitItem])
async def list_units(
    district_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = select(UnitName)
    if district_id is not None:
        stmt = stmt.where(UnitName.clergy_district_id == district_id)
    stmt = stmt.order_by(UnitName.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/register", response_model=ym_schema.YMUserResponse, status_code=201)
async def register(data: ym_schema.YMUserRegister, db: AsyncSession = Depends(get_async_db)):
    user = await YuvalokhamService.register_user(db, data)
    return _build_user_response(user)


@router.post("/login", response_model=ym_schema.YMToken)
async def login(data: ym_schema.YMUserLogin, db: AsyncSession = Depends(get_async_db)):
    return await YuvalokhamService.login(db, data)


@router.post("/refresh", response_model=ym_schema.YMToken)
async def refresh(data: ym_schema.YMRefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    return await YuvalokhamService.refresh_token(db, data.refresh_token)
