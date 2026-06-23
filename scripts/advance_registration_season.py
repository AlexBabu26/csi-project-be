"""Close a registration season and advance to the next year.

Ensures both unit_registration_cycle and unit_registration_payment are fully
reconciled for the closing season before opening the new one:

  - One completed cycle per active unit for close_year
  - One approved payment (null proof) per close_year cycle
  - member_count_at_submit / total_fee_at_submit / completed_at populated
  - path_type set from prior completed seasons
  - unit_details.registration_year synced to close_year
  - site_settings.current_registration_year set to open_year
  - No cycles or payments for open_year (created when units renew)

Usage:
    python scripts/advance_registration_season.py
    python scripts/advance_registration_season.py --close-year 2026 --open-year 2027
    python scripts/advance_registration_season.py --close-year 2026 --open-year 2027 --reconcile-only
"""

import argparse
import asyncio
import sys
from app.common.datetime_utils import now_ist

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.auth.models  # noqa: F401
import app.units.models  # noqa: F401
from app.admin.models import SiteSettings
from app.auth.models import CustomUser, UnitDetails, UnitMembers, UnitRegistrationData, UserType
from app.common.cache import clear_cache
from app.common.db import get_async_engine
from app.units import registration_cycle_service as cycle_service
from app.units.models import PaymentProofStatus, UnitRegistrationCycle, UnitRegistrationPayment

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

REGISTRATION_COMPLETED = "Registration Completed"
SITE_SETTINGS_CACHE_KEY = "site_settings_v1"


async def get_fees(db) -> tuple[int, int]:
    settings = (await db.execute(select(SiteSettings).limit(1))).scalar_one_or_none()
    unit_fee = settings.unit_registration_fee if settings and settings.unit_registration_fee is not None else 100
    member_fee = settings.unit_member_fee if settings and settings.unit_member_fee is not None else 10
    return unit_fee, member_fee


async def resolve_path_type(db, user_id: int, close_year: int) -> str:
    prior = await db.execute(
        select(UnitRegistrationCycle.id)
        .where(
            UnitRegistrationCycle.registered_user_id == user_id,
            UnitRegistrationCycle.registration_year < close_year,
            UnitRegistrationCycle.status == REGISTRATION_COMPLETED,
        )
        .limit(1)
    )
    return "renewal" if prior.scalar_one_or_none() else "fresh"


async def reconcile_closed_season(db, close_year: int) -> dict[str, int]:
    """Ensure cycles and payments are complete for the closing season."""
    unit_fee, member_fee = await get_fees(db)
    now = now_ist()

    rows = (
        await db.execute(
            select(UnitRegistrationData, CustomUser)
            .join(CustomUser, CustomUser.id == UnitRegistrationData.registered_user_id)
            .where(
                CustomUser.user_type == UserType.UNIT,
                CustomUser.is_active.is_(True),
            )
        )
    ).all()

    stats = {
        "units_processed": len(rows),
        "cycles_created": 0,
        "cycles_completed": 0,
        "cycles_path_type_updated": 0,
        "payments_created": 0,
        "payments_updated": 0,
        "payments_linked": 0,
        "details_updated": 0,
    }

    for _reg, user in rows:
        user_id = user.id

        cycle = await cycle_service.get_cycle(db, user_id, close_year)
        if not cycle:
            path_type = await resolve_path_type(db, user_id, close_year)
            cycle = await cycle_service.create_cycle(db, user_id, close_year, path_type=path_type)
            stats["cycles_created"] += 1

        path_type = await resolve_path_type(db, user_id, close_year)
        if cycle.path_type != path_type:
            cycle.path_type = path_type
            stats["cycles_path_type_updated"] += 1

        members = (
            await db.execute(select(UnitMembers).where(UnitMembers.registered_user_id == user_id))
        ).scalars().all()
        member_count = len(members)
        total_amount = unit_fee + (member_count * member_fee)

        payment_result = await db.execute(
            select(UnitRegistrationPayment)
            .where(UnitRegistrationPayment.registration_cycle_id == cycle.id)
            .order_by(UnitRegistrationPayment.submitted_at.desc())
        )
        payment = payment_result.scalars().first()

        if payment is None:
            payment = UnitRegistrationPayment(
                registered_user_id=user_id,
                registration_cycle_id=cycle.id,
                file_path=None,
                total_amount=total_amount,
                status=PaymentProofStatus.APPROVED,
                submitted_at=now,
                reviewed_at=now,
            )
            db.add(payment)
            stats["payments_created"] += 1
        else:
            if payment.registration_cycle_id != cycle.id:
                payment.registration_cycle_id = cycle.id
                stats["payments_linked"] += 1
            changed = False
            if payment.status != PaymentProofStatus.APPROVED:
                payment.status = PaymentProofStatus.APPROVED
                changed = True
            if payment.file_path is not None:
                payment.file_path = None
                changed = True
            if payment.total_amount != total_amount:
                payment.total_amount = total_amount
                changed = True
            if payment.rejection_note:
                payment.rejection_note = None
                changed = True
            if not payment.reviewed_at:
                payment.reviewed_at = now
                changed = True
            if changed:
                stats["payments_updated"] += 1

        if cycle.status != REGISTRATION_COMPLETED:
            cycle.status = REGISTRATION_COMPLETED
            stats["cycles_completed"] += 1

        cycle.completed_at = cycle.completed_at or payment.reviewed_at or now
        cycle.member_count_at_submit = member_count
        cycle.total_fee_at_submit = total_amount

        details = (
            await db.execute(
                select(UnitDetails).where(UnitDetails.registered_user_id == user_id)
            )
        ).scalars().first()
        if details:
            if details.registration_year != close_year or details.number_of_unit_members != member_count:
                stats["details_updated"] += 1
            details.registration_year = close_year
            details.number_of_unit_members = member_count

    # Link any orphan payments for close_year users to their close_year cycle
    orphan_payments = (
        await db.execute(
            select(UnitRegistrationPayment).where(
                UnitRegistrationPayment.registration_cycle_id.is_(None)
            )
        )
    ).scalars().all()
    for payment in orphan_payments:
        cycle = await cycle_service.get_cycle(db, payment.registered_user_id, close_year)
        if cycle:
            payment.registration_cycle_id = cycle.id
            stats["payments_linked"] += 1

    return stats


async def advance(close_year: int, open_year: int, *, reconcile_only: bool = False) -> None:
    engine = get_async_engine()
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession() as db:
        settings = (await db.execute(select(SiteSettings).limit(1))).scalar_one_or_none()
        if not settings:
            settings = SiteSettings(app_name="CSI MKD YOUTH MOVEMENT")
            db.add(settings)
            await db.flush()

        print(f"Reconciling closed season {close_year - 1}-{close_year} (ending year {close_year})...")
        stats = await reconcile_closed_season(db, close_year)
        for key, value in stats.items():
            print(f"  {key}: {value}")

        if not reconcile_only:
            settings.current_registration_year = open_year
            print(f"Active season set to {open_year - 1}-{open_year} (ending year {open_year})")

        await db.commit()

        clear_cache(SITE_SETTINGS_CACHE_KEY)
        clear_cache("admin_dashboard")
        clear_cache("district_wise_data")

        # Verification summary
        close_cycles = (
            await db.execute(
                select(UnitRegistrationCycle).where(
                    UnitRegistrationCycle.registration_year == close_year
                )
            )
        ).scalars().all()
        close_completed = sum(1 for c in close_cycles if c.status == REGISTRATION_COMPLETED)

        close_payments = (
            await db.execute(
                select(UnitRegistrationPayment)
                .join(
                    UnitRegistrationCycle,
                    UnitRegistrationCycle.id == UnitRegistrationPayment.registration_cycle_id,
                )
                .where(
                    UnitRegistrationCycle.registration_year == close_year,
                    UnitRegistrationPayment.status == PaymentProofStatus.APPROVED,
                )
            )
        ).scalars().all()

        open_cycles = (
            await db.execute(
                select(UnitRegistrationCycle).where(
                    UnitRegistrationCycle.registration_year == open_year
                )
            )
        ).scalars().all()

        current = (await db.execute(select(SiteSettings.current_registration_year).limit(1))).scalar()

        print("\nVerification:")
        print(f"  close_year cycles: {len(close_cycles)} ({close_completed} completed)")
        print(f"  close_year approved payments: {len(close_payments)}")
        print(f"  open_year cycles: {len(open_cycles)} (expected 0 until units renew)")
        print(f"  current_registration_year: {current}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Close and advance registration seasons.")
    parser.add_argument("--close-year", type=int, default=2026, help="Ending year of season being closed")
    parser.add_argument("--open-year", type=int, default=2027, help="Ending year of new active season")
    parser.add_argument(
        "--reconcile-only",
        action="store_true",
        help="Only reconcile close_year tables; do not change current_registration_year",
    )
    args = parser.parse_args()
    if not args.reconcile_only and args.open_year != args.close_year + 1:
        raise SystemExit("open-year must be exactly close-year + 1")
    asyncio.run(advance(args.close_year, args.open_year, reconcile_only=args.reconcile_only))


if __name__ == "__main__":
    main()
