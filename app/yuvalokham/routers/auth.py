# app/yuvalokham/routers/auth.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_db
from app.yuvalokham import schemas as ym_schema
from app.yuvalokham.service import YuvalokhamService, _build_user_response

router = APIRouter()


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
