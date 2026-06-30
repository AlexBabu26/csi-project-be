"""Read-only endpoints for country, state, and city master data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import City, Country, State
from app.common.db import get_async_db
from app.common.cache import clear_cache, get_cache, set_cache, TTL_MASTER_DATA
from app.master.schemas import CityResponse, CountryResponse, StateResponse, StateSummaryResponse

router = APIRouter()

# Bumped after CityResponse started including country_id; drops stale v1 entries.
_CITIES_CACHE_PREFIX = "master:cities:v2"
clear_cache("master:cities:")


@router.get("/countries", response_model=list[CountryResponse])
async def list_countries(
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    cache_key = f"master:countries:{search or ''}:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    stmt = select(Country).order_by(Country.name)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(Country.name.ilike(pattern))
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    data = [{"id": r.id, "name": r.name} for r in result.scalars().all()]
    set_cache(cache_key, data, TTL_MASTER_DATA)
    return data


@router.get("/states", response_model=list[StateResponse])
async def list_states(
    country_id: int = Query(..., ge=1),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    cache_key = f"master:states:{country_id}:{search or ''}:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

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
    data = [{"id": r.id, "country_id": r.country_id, "name": r.name} for r in result.scalars().all()]
    set_cache(cache_key, data, TTL_MASTER_DATA)
    return data


@router.get("/states/{state_id}/summary", response_model=StateSummaryResponse)
async def get_state_summary(
    state_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    cache_key = f"master:state_summary:{state_id}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    state = await db.get(State, state_id)
    if not state:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")

    city_count = await db.scalar(
        select(func.count()).select_from(City).where(City.state_id == state_id)
    ) or 0

    data = {
        "id": state.id,
        "country_id": state.country_id,
        "name": state.name,
        "city_count": city_count,
        "city_required": city_count > 0,
    }
    set_cache(cache_key, data, TTL_MASTER_DATA)
    return data


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    state_id: int = Query(..., ge=1),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    cache_key = f"{_CITIES_CACHE_PREFIX}:{state_id}:{search or ''}:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

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
    data = [
        {"id": r.id, "country_id": r.country_id, "state_id": r.state_id, "name": r.name}
        for r in result.scalars().all()
    ]
    set_cache(cache_key, data, TTL_MASTER_DATA)
    return data
