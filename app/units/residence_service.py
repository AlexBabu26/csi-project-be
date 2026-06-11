"""Helpers for member residence location using country/state/city master data."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import City, Country, ResidenceLocation, State

KERALA_STATE_NAME = "Kerala"
INDIA_ISO_CODE = "IN"


async def get_city_with_relations(db: AsyncSession, city_id: int) -> City:
    stmt = (
        select(City)
        .options(
            selectinload(City.country),
            selectinload(City.state).selectinload(State.country),
        )
        .where(City.id == city_id)
    )
    result = await db.execute(stmt)
    city = result.scalar_one_or_none()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid city selected",
        )
    return city


async def get_state_with_country(db: AsyncSession, state_id: int) -> State:
    stmt = (
        select(State)
        .options(selectinload(State.country))
        .where(State.id == state_id)
    )
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state selected",
        )
    return state


async def get_kerala_state(db: AsyncSession) -> State:
    stmt = (
        select(State)
        .join(Country, Country.id == State.country_id)
        .options(selectinload(State.country))
        .where(
            State.name == KERALA_STATE_NAME,
            Country.iso_code == INDIA_ISO_CODE,
        )
    )
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kerala state is not configured in master data",
        )
    return state


def _is_kerala_state(state: State) -> bool:
    return (
        state.name == KERALA_STATE_NAME
        and (state.country.iso_code or "").upper() == INDIA_ISO_CODE
    )


def residence_location_for_state(state: State) -> ResidenceLocation:
    iso_code = (state.country.iso_code or "").upper()
    if iso_code == INDIA_ISO_CODE:
        return ResidenceLocation.OUTSIDE_KERALA
    return ResidenceLocation.OUTSIDE_INDIA


def residence_location_for_city(city: City) -> ResidenceLocation:
    if city.state and _is_kerala_state(city.state):
        return ResidenceLocation.WITHIN_KERALA
    iso_code = (city.country.iso_code or "").upper()
    if iso_code == INDIA_ISO_CODE:
        return ResidenceLocation.OUTSIDE_KERALA
    return ResidenceLocation.OUTSIDE_INDIA


async def apply_residence_fields(
    db: AsyncSession,
    *,
    residence_location: ResidenceLocation | None,
    residence_state_id: int | None,
    residence_city_id: int | None,
) -> tuple[ResidenceLocation, int | None, int | None]:
    if residence_location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Living location is required",
        )

    if residence_location == ResidenceLocation.WITHIN_KERALA:
        kerala_state = await get_kerala_state(db)
        if residence_city_id:
            city = await get_city_with_relations(db, residence_city_id)
            if city.state_id != kerala_state.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected city must be in Kerala",
                )
            return ResidenceLocation.WITHIN_KERALA, kerala_state.id, residence_city_id
        return ResidenceLocation.WITHIN_KERALA, kerala_state.id, None

    if residence_city_id:
        city = await get_city_with_relations(db, residence_city_id)
        resolved_location = residence_location_for_city(city)
        if resolved_location == ResidenceLocation.WITHIN_KERALA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Select Lives in Kerala as Yes when the member resides in Kerala",
            )
        if residence_state_id and city.state_id and residence_state_id != city.state_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected city does not belong to the chosen state",
            )
        return resolved_location, city.state_id or residence_state_id, residence_city_id

    if residence_state_id:
        state = await get_state_with_country(db, residence_state_id)
        if _is_kerala_state(state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Select Lives in Kerala as Yes when the member resides in Kerala",
            )
        return residence_location_for_state(state), state.id, None

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="State is required when the member does not live in Kerala",
    )


def member_residence_is_complete(
    residence_location: ResidenceLocation | None,
    residence_state_id: int | None,
    residence_city_id: int | None,
) -> bool:
    if residence_location is None:
        return False
    if residence_location == ResidenceLocation.WITHIN_KERALA:
        return residence_state_id is not None
    return residence_state_id is not None
