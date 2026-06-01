"""Helpers for per-year unit registration cycles."""

from datetime import datetime
from typing import Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import SiteSettings
from app.auth.models import UnitDetails
from app.units.models import (
    PaymentProofStatus,
    UnitRegistrationCycle,
    UnitRegistrationPayment,
)

REGISTRATION_COMPLETED = "Registration Completed"


async def get_site_settings(db: AsyncSession) -> Optional[SiteSettings]:
    result = await db.execute(select(SiteSettings).limit(1))
    return result.scalar_one_or_none()


async def get_current_registration_year(db: AsyncSession) -> int:
    settings = await get_site_settings(db)
    if settings and settings.current_registration_year:
        return settings.current_registration_year
    return datetime.utcnow().year


async def is_registration_enabled(db: AsyncSession) -> bool:
    settings = await get_site_settings(db)
    return bool(settings and settings.registration_enabled)


async def get_cycle(
    db: AsyncSession,
    user_id: int,
    registration_year: int,
) -> Optional[UnitRegistrationCycle]:
    result = await db.execute(
        select(UnitRegistrationCycle).where(
            UnitRegistrationCycle.registered_user_id == user_id,
            UnitRegistrationCycle.registration_year == registration_year,
        )
    )
    return result.scalar_one_or_none()


async def get_latest_completed_cycle(
    db: AsyncSession,
    user_id: int,
) -> Optional[UnitRegistrationCycle]:
    result = await db.execute(
        select(UnitRegistrationCycle)
        .where(
            UnitRegistrationCycle.registered_user_id == user_id,
            UnitRegistrationCycle.status == REGISTRATION_COMPLETED,
        )
        .order_by(UnitRegistrationCycle.registration_year.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def determine_path_type(
    db: AsyncSession,
    user_id: int,
    current_year: int,
) -> Literal["fresh", "renewal"]:
    prev_year = current_year - 1
    prev_cycle = await get_cycle(db, user_id, prev_year)
    if prev_cycle and prev_cycle.status == REGISTRATION_COMPLETED:
        return "renewal"
    return "fresh"


async def create_cycle(
    db: AsyncSession,
    user_id: int,
    registration_year: int,
    *,
    path_type: Literal["fresh", "renewal"],
    initial_status: str = "Registration Started",
) -> UnitRegistrationCycle:
    cycle = UnitRegistrationCycle(
        registered_user_id=user_id,
        registration_year=registration_year,
        status=initial_status,
        path_type=path_type,
    )
    db.add(cycle)
    await db.flush()
    return cycle


async def get_or_create_current_cycle(
    db: AsyncSession,
    user_id: int,
) -> Optional[UnitRegistrationCycle]:
    """
    Return the cycle for the current registration year, creating one when
    registration is open and the unit has no cycle yet for that year.
    """
    current_year = await get_current_registration_year(db)
    existing = await get_cycle(db, user_id, current_year)
    if existing:
        return existing

    if not await is_registration_enabled(db):
        return None

    path_type = await determine_path_type(db, user_id, current_year)
    cycle = await create_cycle(db, user_id, current_year, path_type=path_type)
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def resolve_active_cycle(
    db: AsyncSession,
    user_id: int,
) -> tuple[Optional[UnitRegistrationCycle], bool, bool]:
    """
    Resolve which cycle drives the application form.

    Returns (cycle, registration_enabled, has_any_completed_cycle).
    """
    current_year = await get_current_registration_year(db)
    enabled = await is_registration_enabled(db)

    cycle = await get_cycle(db, user_id, current_year)
    if not cycle and enabled:
        path_type = await determine_path_type(db, user_id, current_year)
        cycle = await create_cycle(db, user_id, current_year, path_type=path_type)
        await db.commit()
        await db.refresh(cycle)

    latest_completed = await get_latest_completed_cycle(db, user_id)
    has_completed = latest_completed is not None

    if cycle is None and latest_completed is not None:
        return latest_completed, enabled, has_completed

    return cycle, enabled, has_completed


def require_cycle_in_progress(cycle: UnitRegistrationCycle) -> None:
    if cycle.status == REGISTRATION_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration for this year is complete. Use change request workflows for updates.",
        )


async def update_cycle_status(
    db: AsyncSession,
    cycle: UnitRegistrationCycle,
    new_status: str,
) -> None:
    cycle.status = new_status
    await db.commit()


async def complete_cycle(
    db: AsyncSession,
    cycle: UnitRegistrationCycle,
    member_count: int,
    total_fee: int,
) -> None:
    cycle.status = REGISTRATION_COMPLETED
    cycle.member_count_at_submit = member_count
    cycle.total_fee_at_submit = total_fee
    cycle.completed_at = datetime.utcnow()

    details_result = await db.execute(
        select(UnitDetails).where(UnitDetails.registered_user_id == cycle.registered_user_id)
    )
    unit_details = details_result.scalar_one_or_none()
    if unit_details:
        unit_details.registration_year = cycle.registration_year
        unit_details.number_of_unit_members = member_count

    await db.commit()


async def get_payment_status_for_cycle(
    db: AsyncSession,
    user_id: int,
    cycle_id: int,
) -> dict:
    stmt = (
        select(UnitRegistrationPayment)
        .where(
            UnitRegistrationPayment.registered_user_id == user_id,
            UnitRegistrationPayment.registration_cycle_id == cycle_id,
        )
        .order_by(UnitRegistrationPayment.submitted_at.asc())
    )
    result = await db.execute(stmt)
    payments = list(result.scalars().all())

    if not payments:
        overall = "not_submitted"
    elif any(p.status == PaymentProofStatus.APPROVED for p in payments):
        overall = "approved"
    else:
        latest = payments[-1]
        overall = "rejected" if latest.status == PaymentProofStatus.REJECTED else "pending"

    latest_rejection_note = None
    items = []
    for p in payments:
        if p.status == PaymentProofStatus.REJECTED:
            latest_rejection_note = p.rejection_note
        items.append(p)

    return {
        "overall_status": overall,
        "latest_rejection_note": latest_rejection_note,
        "payments": items,
    }


async def cycle_has_approved_payment(db: AsyncSession, cycle_id: int) -> bool:
    result = await db.execute(
        select(UnitRegistrationPayment).where(
            UnitRegistrationPayment.registration_cycle_id == cycle_id,
            UnitRegistrationPayment.status == PaymentProofStatus.APPROVED,
        )
    )
    return result.scalar_one_or_none() is not None
