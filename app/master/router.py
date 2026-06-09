"""Read-only endpoints for country, state, and city master data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import City, Country, State
from app.common.db import get_async_db
from app.master.schemas import CityResponse, CountryResponse, StateResponse, StateSummaryResponse

router = APIRouter()


@router.get("/countries", response_model=list[CountryResponse])
async def list_countries(
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = select(Country).order_by(Country.name)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(Country.name.ilike(pattern))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/states", response_model=list[StateResponse])
async def list_states(
    country_id: int = Query(..., ge=1),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = (
        select(State)
        .where(State.country_id == country_id)
        .order_by(State.name)
    )
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(State.name.ilike(pattern))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/states/{state_id}/summary", response_model=StateSummaryResponse)
async def get_state_summary(
    state_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    state = await db.get(State, state_id)
    if not state:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")

    city_count = await db.scalar(
        select(func.count()).select_from(City).where(City.state_id == state_id)
    ) or 0

    return {
        "id": state.id,
        "country_id": state.country_id,
        "name": state.name,
        "city_count": city_count,
        "city_required": city_count > 0,
    }


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    state_id: int = Query(..., ge=1),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = (
        select(City)
        .where(City.state_id == state_id)
        .order_by(City.name)
    )
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(City.name.ilike(pattern))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
