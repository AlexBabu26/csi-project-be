"""Admin units router - administrative endpoints for units management."""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, status, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.datetime_utils import format_timestamp_ist, now_ist

from app.common.db import get_async_db
from app.common.security import get_current_user, get_current_user_sync
from app.common.cache import get_cache, set_cache, clear_cache
from app.common.storage import save_upload_file
from app.admin.models import SiteSettings
from app.admin.routers.site import get_public_file_url, SITE_SETTINGS_CACHE_KEY
from app.auth.models import (
    CustomUser,
    UnitMembers,
    UnitOfficials,
    UnitCouncilor,
    UnitDetails,
    UnitRegistrationData,
    ClergyDistrict,
    UnitName,
    UserType,
    ResidenceLocation,
)
from app.units.models import (
    UnitTransferRequest,
    UnitMemberChangeRequest,
    UnitOfficialsChangeRequest,
    UnitCouncilorChangeRequest,
    UnitMemberAddRequest,
    ArchivedMemberConcernRequest,
    ArchivedUnitMember,
    RequestStatus,
    UnitRegistrationCycle,
    UnitRegistrationPayment,
    PaymentProofStatus,
)
from app.units import registration_cycle_service as cycle_service
from app.units.schemas import (
    UnitTransferRequestResponse,
    UnitMemberChangeRequestResponse,
    UnitOfficialsChangeRequestResponse,
    UnitCouncilorChangeRequestResponse,
    UnitMemberAddRequestResponse,
    ArchivedMemberConcernRequestResponse,
    RequestActionSchema,
)
from app.units import service as units_service
from app.kalamela.models import (
    Appeal,
    AppealPayments,
    GroupEventParticipation,
    IndividualEventParticipation,
    IndividualEventScoreCard,
    KalamelaExcludeMembers,
)
from app.conference.models import ConferenceDelegate
from app.common.exporter import (
    create_archived_members_csv,
    create_archived_members_excel,
    create_councilors_excel,
    create_members_excel,
    create_officials_excel,
    create_units_excel,
)
from app.units.member_serialization import (
    MEMBER_RESIDENCE_LOAD_OPTIONS,
    member_export_row,
    serialize_member,
)

router = APIRouter()


def _onboarded_unit_name_ids_subquery(admin_user_id: int):
    """UnitName IDs that have an active platform account with registration data."""
    return (
        select(CustomUser.unit_name_id)
        .join(UnitRegistrationData, UnitRegistrationData.registered_user_id == CustomUser.id)
        .where(
            CustomUser.user_type == UserType.UNIT,
            CustomUser.is_active.is_(True),
            CustomUser.unit_name_id.isnot(None),
            CustomUser.id != admin_user_id,
        )
        .distinct()
    )


async def get_admin_user(
    current_user: CustomUser = Depends(get_current_user),
) -> CustomUser:
    """Dependency to ensure user is an admin."""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    return current_user


@router.get("/home", response_model=dict)
@router.get("/dashboard", response_model=dict)
async def admin_home_page(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get admin dashboard statistics. Accessible via /home or /dashboard. Cached for 5 minutes."""
    from sqlalchemy import case, distinct
    
    cache_key = "admin_dashboard"
    
    # Check cache unless refresh is requested
    if not refresh:
        cached_data = get_cache(cache_key)
        if cached_data is not None:
            return cached_data
    
    # Single query for total counts
    stmt = select(
        func.count(distinct(ClergyDistrict.id)).label('total_districts'),
        func.count(distinct(UnitName.id)).label('total_units')
    ).select_from(ClergyDistrict).outerjoin(UnitName)
    result = await db.execute(stmt)
    counts = result.one()
    total_dist_count = counts[0] or 0
    total_units_count = counts[1] or 0

    current_year = await cycle_service.get_current_registration_year(db)
    
    # Completed registrations for the current registration year
    stmt = select(
        func.count(distinct(UnitRegistrationCycle.id)).label('completed_units'),
        func.count(distinct(UnitName.clergy_district_id)).label('completed_districts')
    ).select_from(UnitRegistrationCycle).join(
        CustomUser, UnitRegistrationCycle.registered_user_id == CustomUser.id
    ).join(
        UnitName, CustomUser.unit_name_id == UnitName.id
    ).where(
        UnitRegistrationCycle.status == cycle_service.REGISTRATION_COMPLETED,
        UnitRegistrationCycle.registration_year == current_year,
        UnitRegistrationCycle.registered_user_id != current_user.id
    )
    result = await db.execute(stmt)
    completed = result.one()
    completed_units_count = completed[0] or 0
    completed_dist_count = completed[1] or 0

    in_progress_result = await db.execute(
        select(func.count(distinct(UnitRegistrationCycle.id))).select_from(
            UnitRegistrationCycle
        ).join(
            CustomUser, UnitRegistrationCycle.registered_user_id == CustomUser.id
        ).where(
            UnitRegistrationCycle.registration_year == current_year,
            UnitRegistrationCycle.status != cycle_service.REGISTRATION_COMPLETED,
            UnitRegistrationCycle.registered_user_id != current_user.id,
        )
    )
    in_progress_units_count = in_progress_result.scalar() or 0

    registered_units_result = await db.execute(
        select(func.count(UnitRegistrationData.id)).where(
            UnitRegistrationData.registered_user_id != current_user.id,
        )
    )
    registered_units_count = registered_units_result.scalar() or 0
    not_started_units_count = max(
        0,
        registered_units_count - completed_units_count - in_progress_units_count,
    )

    not_onboarded_result = await db.execute(
        select(func.count(UnitName.id))
        .select_from(UnitName)
        .where(UnitName.id.not_in(_onboarded_unit_name_ids_subquery(current_user.id)))
    )
    not_onboarded_units_count = not_onboarded_result.scalar() or 0

    pending_payments_result = await db.execute(
        select(func.count(UnitRegistrationPayment.id))
        .select_from(UnitRegistrationPayment)
        .join(
            UnitRegistrationCycle,
            UnitRegistrationCycle.id == UnitRegistrationPayment.registration_cycle_id,
        )
        .where(
            UnitRegistrationPayment.status == PaymentProofStatus.PENDING,
            UnitRegistrationCycle.registration_year == current_year,
        )
    )
    pending_payments_count = pending_payments_result.scalar() or 0

    pending_approval_result = await db.execute(
        select(func.count(distinct(UnitRegistrationCycle.id))).select_from(
            UnitRegistrationCycle
        ).join(
            CustomUser, UnitRegistrationCycle.registered_user_id == CustomUser.id
        ).where(
            UnitRegistrationCycle.registration_year == current_year,
            UnitRegistrationCycle.status == cycle_service.DECLARATION_SUBMITTED,
            UnitRegistrationCycle.registered_user_id != current_user.id,
        )
    )
    pending_approval_units_count = pending_approval_result.scalar() or 0

    pending_requests_count = 0
    for model in (
        UnitTransferRequest,
        UnitMemberChangeRequest,
        UnitOfficialsChangeRequest,
        UnitCouncilorChangeRequest,
        UnitMemberAddRequest,
        ArchivedMemberConcernRequest,
    ):
        req_result = await db.execute(
            select(func.count(model.id)).where(model.status == RequestStatus.PENDING)
        )
        pending_requests_count += req_result.scalar() or 0
    
    # Single query for all member counts (total, male, female)
    stmt = select(
        func.count(UnitMembers.id).label('total'),
        func.count(case((UnitMembers.gender == 'M', 1))).label('male'),
        func.count(case((UnitMembers.gender == 'F', 1))).label('female')
    ).select_from(UnitMembers)
    result = await db.execute(stmt)
    member_counts = result.one()
    unit_members_count = member_counts[0] or 0
    unit_members_males_count = member_counts[1] or 0
    unit_females_count = member_counts[2] or 0
    
    # Single query for max member unit with unit name
    stmt = select(
        UnitName.name,
        func.count(UnitMembers.id).label('count')
    ).select_from(UnitMembers).join(
        CustomUser, UnitMembers.registered_user_id == CustomUser.id
    ).join(
        UnitName, CustomUser.unit_name_id == UnitName.id
    ).group_by(UnitName.id, UnitName.name).order_by(
        func.count(UnitMembers.id).desc()
    ).limit(1)
    result = await db.execute(stmt)
    max_unit = result.first()
    
    max_member_unit_name = max_unit[0] if max_unit else "N/A"
    max_member_count = max_unit[1] if max_unit else 0
    
    completed_dists_percent = (completed_dist_count / total_dist_count * 100) if total_dist_count > 0 else 0
    completed_units_percent = (completed_units_count / total_units_count * 100) if total_units_count > 0 else 0
    
    result_data = {
        "total_dist_count": total_dist_count,
        "total_units_count": total_units_count,
        "completed_dist_count": completed_dist_count,
        "completed_units_count": completed_units_count,
        "completed_dists_percent": f"{completed_dists_percent:.2f}",
        "completed_units_percent": f"{completed_units_percent:.2f}",
        "current_registration_year": current_year,
        "registered_units_count": registered_units_count,
        "in_progress_units_count": in_progress_units_count,
        "not_started_units_count": not_started_units_count,
        "not_onboarded_units_count": not_onboarded_units_count,
        "pending_payments_count": pending_payments_count,
        "pending_approval_units_count": pending_approval_units_count,
        "pending_requests": pending_requests_count,
        "total_unit_members": unit_members_count,
        "total_male_members": unit_members_males_count,
        "total_female_members": unit_females_count,
        "max_member_unit": max_member_unit_name,
        "max_member_unit_count": max_member_count,
    }
    
    # Cache for 5 minutes (300 seconds)
    set_cache(cache_key, result_data, ttl_seconds=300)
    
    return result_data


@router.get("/all", response_model=List[dict])
@router.get("", response_model=List[dict])
async def list_all_units(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all registered units. Accessible via /all or root path."""
    current_year = await cycle_service.get_current_registration_year(db)

    stmt = select(UnitRegistrationData).where(
        UnitRegistrationData.registered_user_id != current_user.id
    ).options(
        selectinload(UnitRegistrationData.registered_user).selectinload(CustomUser.unit_name)
    )
    result = await db.execute(stmt)
    units_data = list(result.scalars().all())

    user_ids = [u.registered_user_id for u in units_data]
    cycles_by_user: dict[int, UnitRegistrationCycle] = {}
    if user_ids:
        cycles_result = await db.execute(
            select(UnitRegistrationCycle).where(
                UnitRegistrationCycle.registered_user_id.in_(user_ids),
                UnitRegistrationCycle.registration_year == current_year,
            )
        )
        for cycle in cycles_result.scalars().all():
            cycles_by_user[cycle.registered_user_id] = cycle

    payment_status_by_user: dict[int, str] = {}
    payment_fully_approved_by_user: dict[int, bool] = {}
    payment_reviewed_at_by_user: dict[int, Optional[datetime]] = {}
    if user_ids:
        payments_result = await db.execute(
            select(UnitRegistrationPayment).where(
                UnitRegistrationPayment.registered_user_id.in_(user_ids),
            )
        )
        payments = list(payments_result.scalars().all())
        for user_id in user_ids:
            cycle = cycles_by_user.get(user_id)
            if not cycle:
                payment_status_by_user[user_id] = "not_submitted"
                payment_fully_approved_by_user[user_id] = False
                payment_reviewed_at_by_user[user_id] = None
                continue
            user_payments = sorted(
                [p for p in payments if p.registration_cycle_id == cycle.id],
                key=lambda p: p.submitted_at,
            )
            if not user_payments:
                payment_status_by_user[user_id] = "not_submitted"
                payment_fully_approved_by_user[user_id] = False
                payment_reviewed_at_by_user[user_id] = None
                continue

            approved_payments = [
                p for p in user_payments if p.status == PaymentProofStatus.APPROVED
            ]
            if approved_payments:
                latest_approved = approved_payments[-1]
                payment_reviewed_at_by_user[user_id] = latest_approved.reviewed_at
                if (
                    latest_approved.balance_amount is not None
                    and latest_approved.balance_amount > 0
                ):
                    payment_status_by_user[user_id] = "partial"
                    payment_fully_approved_by_user[user_id] = False
                else:
                    payment_status_by_user[user_id] = "approved"
                    payment_fully_approved_by_user[user_id] = True
            elif user_payments[-1].status == PaymentProofStatus.REJECTED:
                payment_status_by_user[user_id] = "rejected"
                payment_fully_approved_by_user[user_id] = False
                payment_reviewed_at_by_user[user_id] = None
            else:
                payment_status_by_user[user_id] = "pending"
                payment_fully_approved_by_user[user_id] = False
                payment_reviewed_at_by_user[user_id] = None

    member_counts_by_user: dict[int, int] = {}
    if user_ids:
        member_counts_result = await db.execute(
            select(
                UnitMembers.registered_user_id,
                func.count(UnitMembers.id).label("count"),
            )
            .where(UnitMembers.registered_user_id.in_(user_ids))
            .group_by(UnitMembers.registered_user_id)
        )
        for row in member_counts_result.all():
            member_counts_by_user[row.registered_user_id] = row.count or 0
    
    return [
        {
            "id": unit_data.id,
            "user_id": unit_data.registered_user_id,
            "username": unit_data.registered_user.username,
            "unit_name": unit_data.registered_user.unit_name.name if unit_data.registered_user.unit_name else None,
            "member_count": member_counts_by_user.get(unit_data.registered_user_id, 0),
            "status": cycles_by_user[unit_data.registered_user_id].status
            if unit_data.registered_user_id in cycles_by_user
            else "Not Started",
            "registration_year": current_year,
            "cycle_status": cycles_by_user[unit_data.registered_user_id].status
            if unit_data.registered_user_id in cycles_by_user
            else None,
            "path_type": cycles_by_user[unit_data.registered_user_id].path_type
            if unit_data.registered_user_id in cycles_by_user
            else None,
            "payment_status": payment_status_by_user.get(unit_data.registered_user_id, "not_submitted"),
            "payment_fully_approved": payment_fully_approved_by_user.get(
                unit_data.registered_user_id, False
            ),
            "can_complete_registration": cycle_service.can_admin_complete_registration(
                cycles_by_user.get(unit_data.registered_user_id),
                payment_fully_approved=payment_fully_approved_by_user.get(
                    unit_data.registered_user_id, False
                ),
                current_registration_year=current_year,
                latest_payment_reviewed_at=payment_reviewed_at_by_user.get(
                    unit_data.registered_user_id
                ),
            ),
        }
        for unit_data in units_data
    ]


@router.get("/not-onboarded", response_model=List[dict])
async def list_not_onboarded_units(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Master-list churches with no active platform registration account."""
    stmt = (
        select(
            UnitName.id,
            UnitName.name,
            UnitName.clergy_district_id,
            ClergyDistrict.name.label("clergy_district"),
        )
        .join(ClergyDistrict, ClergyDistrict.id == UnitName.clergy_district_id)
        .where(UnitName.id.not_in(_onboarded_unit_name_ids_subquery(current_user.id)))
        .order_by(ClergyDistrict.name, UnitName.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "clergy_district_id": row.clergy_district_id,
            "clergy_district": row.clergy_district,
        }
        for row in rows
    ]


# Transfer Request Endpoints
@router.get("/transfer-requests", response_model=List[UnitTransferRequestResponse])
async def list_transfer_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all transfer requests."""
    return await units_service.get_transfer_requests(db)


@router.put("/transfer-requests/{request_id}/approve", response_model=UnitTransferRequestResponse)
async def approve_transfer_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a transfer request."""
    return await units_service.approve_unit_transfer_request(db, request_id)


@router.put("/transfer-requests/{request_id}/revert", response_model=UnitTransferRequestResponse)
async def revert_transfer_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert a transfer request."""
    return await units_service.revert_unit_transfer_request(db, request_id)


@router.put("/transfer-requests/{request_id}/reject", response_model=UnitTransferRequestResponse)
async def reject_transfer_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject a transfer request."""
    return await units_service.reject_unit_transfer_request(db, request_id)


# Member Change Request Endpoints
@router.get("/member-change-requests", response_model=List[UnitMemberChangeRequestResponse])
async def list_member_change_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all member change requests."""
    return await units_service.get_member_change_requests(db)


@router.put("/member-change-requests/{request_id}/approve", response_model=UnitMemberChangeRequestResponse)
async def approve_member_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a member change request."""
    return await units_service.approve_member_info_change(db, request_id)


@router.put("/member-change-requests/{request_id}/revert", response_model=UnitMemberChangeRequestResponse)
async def revert_member_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert a member change request."""
    return await units_service.revert_member_info_change(db, request_id)


@router.put("/member-change-requests/{request_id}/reject", response_model=UnitMemberChangeRequestResponse)
async def reject_member_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject a member change request."""
    return await units_service.reject_member_info_change(db, request_id)


# Officials Change Request Endpoints
@router.get("/officials-change-requests", response_model=List[UnitOfficialsChangeRequestResponse])
async def list_officials_change_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all officials change requests."""
    return await units_service.get_officials_change_requests(db)


@router.put("/officials-change-requests/{request_id}/approve", response_model=UnitOfficialsChangeRequestResponse)
async def approve_officials_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve an officials change request."""
    return await units_service.approve_officials_change(db, request_id)


@router.put("/officials-change-requests/{request_id}/revert", response_model=UnitOfficialsChangeRequestResponse)
async def revert_officials_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert an officials change request."""
    return await units_service.revert_officials_change(db, request_id)


@router.put("/officials-change-requests/{request_id}/reject", response_model=UnitOfficialsChangeRequestResponse)
async def reject_officials_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject an officials change request."""
    return await units_service.reject_officials_change(db, request_id)


# Councilor Change Request Endpoints
@router.get("/councilor-change-requests", response_model=List[UnitCouncilorChangeRequestResponse])
async def list_councilor_change_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all councilor change requests."""
    return await units_service.get_councilor_change_requests(db)


@router.put("/councilor-change-requests/{request_id}/approve", response_model=UnitCouncilorChangeRequestResponse)
async def approve_councilor_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a councilor change request."""
    return await units_service.approve_councilor_change(db, request_id)


@router.put("/councilor-change-requests/{request_id}/revert", response_model=UnitCouncilorChangeRequestResponse)
async def revert_councilor_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert a councilor change request."""
    return await units_service.revert_councilor_change(db, request_id)


@router.put("/councilor-change-requests/{request_id}/reject", response_model=UnitCouncilorChangeRequestResponse)
async def reject_councilor_change_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject a councilor change request."""
    return await units_service.reject_councilor_change(db, request_id)


# Member Add Request Endpoints
@router.get("/member-add-requests", response_model=List[UnitMemberAddRequestResponse])
async def list_member_add_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all member add requests."""
    return await units_service.get_member_add_requests(db)


@router.put("/member-add-requests/{request_id}/approve", response_model=UnitMemberAddRequestResponse)
async def approve_member_add_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a member add request."""
    return await units_service.approve_member_add_request(db, request_id)


@router.put("/member-add-requests/{request_id}/reject", response_model=UnitMemberAddRequestResponse)
async def reject_member_add_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject a member add request."""
    return await units_service.reject_member_add_request(db, request_id)


# Archived Member Concern Request Endpoints
@router.get("/archived-member-concern-requests")
async def list_archived_member_concern_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all archived member concern requests."""
    return await units_service.get_archived_member_concern_requests(db)


@router.put("/archived-member-concern-requests/{request_id}/approve")
async def approve_archived_member_concern_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Resolve an archived member concern after admin review."""
    concern = await units_service.approve_archived_member_concern_request(
        db,
        request_id,
        admin_response=action.remarks if action else None,
    )
    enriched = await units_service.get_archived_member_concern_requests(db)
    match = next((item for item in enriched if item["id"] == concern.id), None)
    return match or concern


@router.put("/archived-member-concern-requests/{request_id}/reject")
async def reject_archived_member_concern_request(
    request_id: int,
    action: RequestActionSchema = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject an archived member concern after admin review."""
    concern = await units_service.reject_archived_member_concern_request(
        db,
        request_id,
        admin_response=action.remarks if action else None,
    )
    enriched = await units_service.get_archived_member_concern_requests(db)
    match = next((item for item in enriched if item["id"] == concern.id), None)
    return match or concern


# Unit Officials Endpoint with Pagination
@router.get("/officials", response_model=dict)
async def list_all_unit_officials(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
    page: int = 1,
    page_size: int = 50,
    unit_id: Optional[int] = Query(None, description="Filter by registered unit user id"),
):
    """List all unit officials across all units with pagination."""
    filters = []
    if unit_id is not None:
        filters.append(UnitOfficials.registered_user_id == unit_id)

    # Get total count
    count_stmt = select(func.count()).select_from(UnitOfficials)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(UnitOfficials).options(
        selectinload(UnitOfficials.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district)
    ).offset(offset).limit(page_size)
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    officials_list = list(result.scalars().all())
    
    data = [
        {
            "id": officials.id,
            "registered_user_id": officials.registered_user_id,
            "unit_name": officials.registered_user.unit_name.name if officials.registered_user and officials.registered_user.unit_name else None,
            "district": officials.registered_user.unit_name.district.name if officials.registered_user and officials.registered_user.unit_name and officials.registered_user.unit_name.district else None,
            "president_designation": officials.president_designation,
            "president_name": officials.president_name,
            "president_phone": officials.president_phone,
            "vice_president_name": officials.vice_president_name,
            "vice_president_phone": officials.vice_president_phone,
            "secretary_name": officials.secretary_name,
            "secretary_phone": officials.secretary_phone,
            "joint_secretary_name": officials.joint_secretary_name,
            "joint_secretary_phone": officials.joint_secretary_phone,
            "treasurer_name": officials.treasurer_name,
            "treasurer_phone": officials.treasurer_phone,
        }
        for officials in officials_list
    ]
    
    return {"data": data, "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


# Unit Councilors Endpoint with Pagination
@router.get("/councilors", response_model=dict)
async def list_all_unit_councilors(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
    page: int = 1,
    page_size: int = 50,
    unit_id: Optional[int] = Query(None, description="Filter by registered unit user id"),
):
    """List all unit councilors across all units with pagination."""
    filters = []
    if unit_id is not None:
        filters.append(UnitCouncilor.registered_user_id == unit_id)

    # Get total count
    count_stmt = select(func.count()).select_from(UnitCouncilor)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(UnitCouncilor).options(
        selectinload(UnitCouncilor.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
        selectinload(UnitCouncilor.unit_member)
    ).offset(offset).limit(page_size)
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    councilors_list = list(result.scalars().all())
    
    data = [
        {
            "id": councilor.id,
            "registered_user_id": councilor.registered_user_id,
            "unit_name": councilor.registered_user.unit_name.name if councilor.registered_user and councilor.registered_user.unit_name else None,
            "district": councilor.registered_user.unit_name.district.name if councilor.registered_user and councilor.registered_user.unit_name and councilor.registered_user.unit_name.district else None,
            "unit_member_id": councilor.unit_member_id,
            "member_name": councilor.unit_member.name if councilor.unit_member else None,
            "member_gender": councilor.unit_member.gender if councilor.unit_member else None,
            "member_phone": councilor.unit_member.number if councilor.unit_member else None,
        }
        for councilor in councilors_list
    ]
    
    return {"data": data, "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


# Unit Members Endpoint with Pagination
@router.get("/members", response_model=dict)
async def list_all_unit_members(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
    page: int = 1,
    page_size: int = 50,
    unit_id: Optional[int] = Query(None, description="Filter by registered unit user id"),
    residence_location: Optional[ResidenceLocation] = Query(None),
    missing_residence_location: Optional[bool] = Query(None),
):
    """List all unit members across all units with pagination."""
    filters = []
    if unit_id is not None:
        filters.append(UnitMembers.registered_user_id == unit_id)
    if missing_residence_location:
        filters.append(UnitMembers.residence_location.is_(None))
    elif residence_location is not None:
        filters.append(UnitMembers.residence_location == residence_location)

    # Get total count
    count_stmt = select(func.count()).select_from(UnitMembers)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(UnitMembers).options(
        selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
        *MEMBER_RESIDENCE_LOAD_OPTIONS,
    ).offset(offset).limit(page_size)
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    members_list = list(result.scalars().all())
    
    data = []
    for member in members_list:
        row = serialize_member(member)
        row["unit_name"] = (
            member.registered_user.unit_name.name
            if member.registered_user and member.registered_user.unit_name
            else None
        )
        row["district"] = (
            member.registered_user.unit_name.district.name
            if member.registered_user
            and member.registered_user.unit_name
            and member.registered_user.unit_name.district
            else None
        )
        data.append(row)
    
    return {"data": data, "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


# ── Archive Preview ──────────────────────────────────────────────────────────

@router.get("/archive-preview", response_model=dict)
async def archive_preview(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Return all active unit members whose DOB falls outside the configured
    Min DOB / Max DOB limits (i.e. candidates for yearly archiving).
    Reads limits from site_settings; falls back to 1990-01-01 / 2011-12-31.
    """
    from app.admin.models import SiteSettings

    # Load DOB limits from site settings
    ss_result = await db.execute(select(SiteSettings))
    ss = ss_result.scalar_one_or_none()
    min_dob: date = (ss.member_min_dob if ss and ss.member_min_dob else date(1990, 1, 1))
    max_dob: date = (ss.member_max_dob if ss and ss.member_max_dob else date(2011, 12, 31))

    # Find members whose DOB is outside [min_dob, max_dob]
    stmt = (
        select(UnitMembers)
        .options(
            selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name),
            *MEMBER_RESIDENCE_LOAD_OPTIONS,
        )
        .where(
            or_(
                UnitMembers.dob < min_dob,
                UnitMembers.dob > max_dob,
            )
        )
        .order_by(UnitMembers.dob.asc())
    )
    result = await db.execute(stmt)
    members = list(result.scalars().all())

    data = []
    for m in members:
        row = serialize_member(m)
        row["unit_name"] = (
            m.registered_user.unit_name.name
            if m.registered_user and m.registered_user.unit_name
            else None
        )
        data.append(row)

    return {
        "data": data,
        "total": len(data),
        "min_dob": min_dob.isoformat(),
        "max_dob": max_dob.isoformat(),
    }


# ── Bulk Archive ──────────────────────────────────────────────────────────────

async def _remove_member_dependencies(db: AsyncSession, member_ids: List[int]) -> None:
    """Remove records that reference unit_members before archive/delete."""
    if not member_ids:
        return

    appeal_ids = select(Appeal.id).where(Appeal.added_by_id.in_(member_ids))
    individual_participation_ids = select(IndividualEventParticipation.id).where(
        IndividualEventParticipation.participant_id.in_(member_ids)
    )
    councilor_ids = select(UnitCouncilor.id).where(
        UnitCouncilor.unit_member_id.in_(member_ids)
    )

    await db.execute(
        delete(AppealPayments).where(AppealPayments.appeal_id.in_(appeal_ids))
    )
    await db.execute(delete(Appeal).where(Appeal.added_by_id.in_(member_ids)))
    await db.execute(
        delete(IndividualEventScoreCard).where(
            or_(
                IndividualEventScoreCard.participant_id.in_(member_ids),
                IndividualEventScoreCard.event_participation_id.in_(individual_participation_ids),
            )
        )
    )
    await db.execute(
        delete(IndividualEventParticipation).where(
            IndividualEventParticipation.participant_id.in_(member_ids)
        )
    )
    await db.execute(
        delete(GroupEventParticipation).where(
            GroupEventParticipation.participant_id.in_(member_ids)
        )
    )
    await db.execute(
        delete(KalamelaExcludeMembers).where(
            KalamelaExcludeMembers.members_id.in_(member_ids)
        )
    )
    await db.execute(
        delete(UnitCouncilorChangeRequest).where(
            or_(
                UnitCouncilorChangeRequest.unit_councilor_id.in_(councilor_ids),
                UnitCouncilorChangeRequest.unit_member_id.in_(member_ids),
                UnitCouncilorChangeRequest.original_unit_member_id.in_(member_ids),
            )
        )
    )
    await db.execute(
        delete(UnitCouncilor).where(UnitCouncilor.unit_member_id.in_(member_ids))
    )
    await db.execute(
        delete(UnitMemberChangeRequest).where(
            UnitMemberChangeRequest.unit_member_id.in_(member_ids)
        )
    )
    await db.execute(
        delete(UnitTransferRequest).where(
            UnitTransferRequest.unit_member_id.in_(member_ids)
        )
    )
    await db.execute(
        delete(ConferenceDelegate).where(ConferenceDelegate.members_id.in_(member_ids))
    )
    await db.flush()


@router.post("/bulk-archive", response_model=dict)
async def bulk_archive_members(
    member_ids: List[int] = Body(..., embed=True),
    archive_year: str = Body(..., embed=True),
    archive_reason: Optional[str] = Body(None, embed=True),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Archive a set of active unit members into archived_unit_member with a
    registration year label (e.g. "2025-2026").
    """
    if not member_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No member IDs provided")

    stmt = select(UnitMembers).where(UnitMembers.id.in_(member_ids))
    result = await db.execute(stmt)
    members = list(result.scalars().all())

    found_ids = {m.id for m in members}
    missing = set(member_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Members not found: {sorted(missing)}",
        )

    await _remove_member_dependencies(db, member_ids)

    archived_count = 0
    for member in members:
        archived = ArchivedUnitMember(
            registered_user_id=member.registered_user_id,
            name=member.name,
            gender=member.gender,
            dob=member.dob,
            number=member.number,
            qualification=member.qualification,
            blood_group=member.blood_group,
            archived_at=now_ist(),
            archive_year=archive_year.strip(),
            archive_reason=archive_reason,
        )
        db.add(archived)
        await db.delete(member)
        archived_count += 1

    await db.commit()
    return {
        "message": f"{archived_count} member(s) archived successfully",
        "archived_count": archived_count,
        "archive_year": archive_year,
    }


# ── Restore Archived Member ───────────────────────────────────────────────────

@router.post("/restore-member/{member_id}", response_model=dict)
async def restore_archived_member(
    member_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Restore an archived member back to active unit_members."""
    stmt = select(ArchivedUnitMember).where(ArchivedUnitMember.id == member_id)
    result = await db.execute(stmt)
    archived = result.scalar_one_or_none()

    if not archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archived member not found")

    current_year = await cycle_service.get_current_registration_year(db)
    cycle = await cycle_service.get_cycle(db, archived.registered_user_id, current_year)

    active_member = UnitMembers(
        registered_user_id=archived.registered_user_id,
        name=archived.name,
        gender=archived.gender,
        dob=archived.dob,
        number=archived.number,
        qualification=archived.qualification,
        blood_group=archived.blood_group,
        added_registration_cycle_id=cycle.id if cycle else None,
    )
    db.add(active_member)
    await cycle_service.adjust_fee_for_member_delta(
        db,
        registered_user_id=archived.registered_user_id,
        delta_members=1,
    )
    await db.delete(archived)
    await db.commit()

    return {"message": f"{archived.name} has been restored to active members"}


# ── Archived Unit Members List ────────────────────────────────────────────────

async def _fetch_archived_members(
    db: AsyncSession,
    archive_year: Optional[str] = None,
) -> List[dict]:
    """Load archived members with unit names, optionally filtered by archive year."""
    stmt = (
        select(ArchivedUnitMember, UnitName.name.label("unit_name"))
        .outerjoin(CustomUser, CustomUser.id == ArchivedUnitMember.registered_user_id)
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .order_by(ArchivedUnitMember.archived_at.desc())
    )
    if archive_year and archive_year.lower() != "all":
        stmt = stmt.where(ArchivedUnitMember.archive_year == archive_year.strip())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": member.id,
            "registered_user_id": member.registered_user_id,
            "name": member.name,
            "gender": member.gender,
            "dob": member.dob.isoformat() if member.dob else None,
            "age": member.age,
            "number": member.number,
            "qualification": member.qualification,
            "blood_group": member.blood_group,
            "archived_at": member.archived_at.isoformat() if member.archived_at else None,
            "archive_year": member.archive_year,
            "archive_reason": member.archive_reason,
            "unit_name": unit_name,
        }
        for member, unit_name in rows
    ]


@router.get("/archived-members/export")
async def export_archived_members(
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    archive_year: Optional[str] = Query(
        None,
        description='Filter by archive year label, or omit / use "all" for every year',
    ),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Export archived unit members to Excel or CSV, respecting the archive year filter."""
    members = await _fetch_archived_members(db, archive_year)

    year_suffix = "all"
    if archive_year and archive_year.lower() != "all":
        year_suffix = archive_year.strip().replace("/", "-").replace("\\", "-")

    if format == "csv":
        export_file = create_archived_members_csv(members)
        media_type = "text/csv"
        filename = f"archived_members_{year_suffix}.csv"
    else:
        export_file = create_archived_members_excel(members)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"archived_members_{year_suffix}.xlsx"

    return StreamingResponse(
        export_file,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Archived Unit Members Endpoint with Pagination
@router.get("/archived-members", response_model=dict)
async def list_all_archived_members(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
    page: int = 1,
    page_size: int = 50,
):
    """List all archived unit members across all units with pagination."""
    # Get total count
    count_stmt = select(func.count()).select_from(ArchivedUnitMember)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Get paginated data — join CustomUser → UnitName to resolve the unit name
    offset = (page - 1) * page_size
    stmt = (
        select(ArchivedUnitMember, UnitName.name.label("unit_name"))
        .outerjoin(CustomUser, CustomUser.id == ArchivedUnitMember.registered_user_id)
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .order_by(ArchivedUnitMember.archived_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    data = [
        {
            "id": member.id,
            "registered_user_id": member.registered_user_id,
            "name": member.name,
            "gender": member.gender,
            "dob": member.dob.isoformat() if member.dob else None,
            "age": member.age,
            "number": member.number,
            "qualification": member.qualification,
            "blood_group": member.blood_group,
            "archived_at": member.archived_at.isoformat() if member.archived_at else None,
            "archive_year": member.archive_year,
            "archive_reason": member.archive_reason,
            "unit_name": unit_name,
        }
        for member, unit_name in rows
    ]

    return {"data": data, "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


# ── Blood Donor Search ────────────────────────────────────────────────────────

@router.get("/blood-donor-search", response_model=dict)
async def blood_donor_search(
    blood_group: Optional[str] = Query(None, description="Filter by blood group e.g. O+"),
    name: Optional[str] = Query(None, description="Partial name search"),
    gender: Optional[str] = Query(None, description="Filter by gender: M or F"),
    districts: List[str] = Query(default=[], description="Filter by district names (multi-select)"),
    units: List[str] = Query(default=[], description="Filter by unit names (multi-select)"),
    include_archived: bool = Query(True, description="Include archived members"),
    current_user: CustomUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Search for blood donors across active and archived unit members.
    Access: Admin always allowed. District officials / unit users only if enabled in site settings.
    """
    from app.admin.models import SiteSettings

    # ── Permission check ──────────────────────────────────────────────────────
    if current_user.user_type == UserType.BLOOD_BANK:
        pass  # Dedicated blood bank users always have access
    elif current_user.user_type != UserType.ADMIN:
        ss_result = await db.execute(select(SiteSettings))
        ss = ss_result.scalar_one_or_none()
        user_type_val = current_user.user_type.value if hasattr(current_user.user_type, 'value') else current_user.user_type
        is_district = user_type_val == "DISTRICT_OFFICIAL" or current_user.user_type == UserType.DISTRICT_OFFICIAL
        is_unit = user_type_val == "UNIT" or current_user.user_type == UserType.UNIT
        if is_district and not (ss and ss.blood_donor_district_access):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Blood Donor Search not enabled for District Officials")
        if is_unit and not (ss and ss.blood_donor_unit_access):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Blood Donor Search not enabled for Unit Officials")
        if not (is_district or is_unit):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    results = []

    # ── Helper: build filters ─────────────────────────────────────────────────
    def name_filter(col): return col.ilike(f"%{name}%") if name else True
    def unit_filter(col): return col.in_(units) if units else True
    def district_filter(col): return col.in_(districts) if districts else True
    def bg_filter(col): return col == blood_group if blood_group else True
    def gender_filter(col): return col == gender if gender else True

    # ── Active members ─────────────────────────────────────────────────────────
    active_stmt = (
        select(
            UnitMembers.id,
            UnitMembers.name,
            UnitMembers.gender,
            UnitMembers.dob,
            UnitMembers.number,
            UnitMembers.blood_group,
            UnitMembers.qualification,
            UnitName.name.label("unit_name"),
            ClergyDistrict.name.label("district_name"),
        )
        .outerjoin(CustomUser, CustomUser.id == UnitMembers.registered_user_id)
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .outerjoin(ClergyDistrict, ClergyDistrict.id == UnitName.clergy_district_id)
        .where(bg_filter(UnitMembers.blood_group))
        .where(name_filter(UnitMembers.name))
        .where(gender_filter(UnitMembers.gender))
        .where(unit_filter(UnitName.name))
        .where(district_filter(ClergyDistrict.name))
        .order_by(UnitMembers.name)
        .limit(500)
    )
    active_rows = (await db.execute(active_stmt)).all()
    for r in active_rows:
        results.append({
            "id": r.id,
            "name": r.name,
            "gender": r.gender,
            "dob": r.dob.isoformat() if r.dob else None,
            "blood_group": r.blood_group,
            "number": r.number,
            "qualification": r.qualification,
            "unit_name": r.unit_name,
            "district_name": r.district_name,
            "status": "active",
            "archive_year": None,
        })

    # ── Archived members ───────────────────────────────────────────────────────
    if include_archived:
        archived_stmt = (
            select(
                ArchivedUnitMember.id,
                ArchivedUnitMember.name,
                ArchivedUnitMember.gender,
                ArchivedUnitMember.dob,
                ArchivedUnitMember.number,
                ArchivedUnitMember.blood_group,
                ArchivedUnitMember.qualification,
                ArchivedUnitMember.archive_year,
                UnitName.name.label("unit_name"),
                ClergyDistrict.name.label("district_name"),
            )
            .outerjoin(CustomUser, CustomUser.id == ArchivedUnitMember.registered_user_id)
            .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
            .outerjoin(ClergyDistrict, ClergyDistrict.id == UnitName.clergy_district_id)
            .where(bg_filter(ArchivedUnitMember.blood_group))
            .where(name_filter(ArchivedUnitMember.name))
            .where(gender_filter(ArchivedUnitMember.gender))
            .where(unit_filter(UnitName.name))
            .where(district_filter(ClergyDistrict.name))
            .order_by(ArchivedUnitMember.name)
            .limit(500)
        )
        archived_rows = (await db.execute(archived_stmt)).all()
        for r in archived_rows:
            results.append({
                "id": r.id,
                "name": r.name,
                "gender": r.gender,
                "dob": r.dob.isoformat() if r.dob else None,
                "blood_group": r.blood_group,
                "number": r.number,
                "qualification": r.qualification,
                "unit_name": r.unit_name,
                "district_name": r.district_name,
                "status": "archived",
                "archive_year": r.archive_year,
            })

    # Sort combined results: active first, then by name
    results.sort(key=lambda x: (x["status"] != "active", x["name"] or ""))

    return {"data": results, "total": len(results)}


# Member Management
@router.delete("/members/{member_id}", response_model=dict)
async def archive_member(
    member_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Archive a unit member."""
    await units_service.archive_unit_member(db, member_id)
    return {"message": "Member archived successfully"}


# Password Reset
@router.post("/reset-password", response_model=dict)
async def reset_password(
    username: str,
    new_password: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reset a user's password."""
    from app.common.security import get_password_hash
    
    stmt = select(CustomUser).where(CustomUser.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found"
        )
    
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    
    return {"message": f"Password for user {username} reset successfully"}



# ── Registration Payment Review ──────────────────────────────────────────────


@router.get("/registration-payments", response_model=List[dict])
async def list_registration_payments(
    payment_status: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED"),
    registration_year: Optional[int] = Query(None, description="Filter by registration year"),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all unit registration payment proof submissions."""
    stmt = (
        select(UnitRegistrationPayment, CustomUser, UnitName, UnitRegistrationCycle)
        .join(CustomUser, CustomUser.id == UnitRegistrationPayment.registered_user_id)
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .outerjoin(
            UnitRegistrationCycle,
            UnitRegistrationCycle.id == UnitRegistrationPayment.registration_cycle_id,
        )
        .order_by(
            func.lower(func.coalesce(UnitName.name, CustomUser.username)).asc(),
            UnitRegistrationPayment.submitted_at.asc(),
        )
    )
    if payment_status:
        try:
            ps = PaymentProofStatus(payment_status.upper())
            stmt = stmt.where(UnitRegistrationPayment.status == ps)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")
    if registration_year is not None:
        stmt = stmt.where(UnitRegistrationCycle.registration_year == registration_year)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": p.id,
            "registered_user_id": p.registered_user_id,
            "username": u.username,
            "unit_name": un.name if un else None,
            "registration_year": cycle.registration_year if cycle else None,
            "file_url": get_public_file_url(p.file_path) if p.file_path else None,
            "total_amount": p.total_amount,
            "balance_amount": p.balance_amount,
            "registration_total_amount": cycle.total_fee_at_submit if cycle else None,
            "status": p.status.value,
            "rejection_note": p.rejection_note,
            "submitted_at": p.submitted_at.isoformat(),
            "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        }
        for p, u, un, cycle in rows
    ]


@router.post("/registration-payments/{payment_id}/approve", response_model=dict)
async def approve_registration_payment(
    payment_id: int,
    paid_amount: int = Body(..., embed=True),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a unit registration payment proof submission.

    Admin enters the amount paid in this proof; remaining balance is derived from
    the outstanding balance after prior approved proofs, not the full registration
    total. Print form unlocks for the unit once balance is 0.
    """
    if paid_amount < 0:
        raise HTTPException(status_code=400, detail="Paid amount cannot be negative")

    stmt = select(UnitRegistrationPayment).where(UnitRegistrationPayment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment submission not found")

    if payment.total_amount is None:
        raise HTTPException(
            status_code=400,
            detail="Payment total is unknown; cannot approve with a paid amount",
        )

    prior_stmt = (
        select(UnitRegistrationPayment)
        .where(
            UnitRegistrationPayment.registered_user_id == payment.registered_user_id,
            UnitRegistrationPayment.registration_cycle_id == payment.registration_cycle_id,
            UnitRegistrationPayment.status == PaymentProofStatus.APPROVED,
            UnitRegistrationPayment.id != payment.id,
        )
        .order_by(UnitRegistrationPayment.submitted_at.asc())
    )
    prior_result = await db.execute(prior_stmt)
    prior_approved = list(prior_result.scalars().all())

    if prior_approved:
        current_balance = prior_approved[-1].balance_amount
        if current_balance is None:
            current_balance = payment.total_amount
    else:
        current_balance = payment.total_amount

    if paid_amount > current_balance:
        raise HTTPException(
            status_code=400,
            detail="Paid amount cannot exceed the remaining balance",
        )

    balance_amount = max(0, current_balance - paid_amount)

    payment.status = PaymentProofStatus.APPROVED
    payment.balance_amount = balance_amount
    payment.rejection_note = None
    payment.reviewed_at = now_ist()
    payment.reviewed_by_id = current_user.id
    await db.commit()

    return {
        "message": "Payment approved successfully",
        "id": payment_id,
        "paid_amount": paid_amount,
        "balance_amount": balance_amount,
    }


@router.post("/registration-payments/{payment_id}/reject", response_model=dict)
async def reject_registration_payment(
    payment_id: int,
    rejection_note: str = Body(..., embed=True),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reject a unit registration payment proof submission with a note."""
    stmt = select(UnitRegistrationPayment).where(UnitRegistrationPayment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment submission not found")

    if not rejection_note.strip():
        raise HTTPException(status_code=400, detail="Rejection note is required")

    payment.status = PaymentProofStatus.REJECTED
    payment.rejection_note = rejection_note.strip()
    payment.reviewed_at = now_ist()
    payment.reviewed_by_id = current_user.id
    await db.commit()

    return {"message": "Payment rejected", "id": payment_id}


@router.post("/payment-qr", response_model=dict)
async def upload_payment_qr(
    file: UploadFile = File(..., description="QR code image for unit registration payment"),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Upload or replace the QR code used for unit registration fee collection."""
    from sqlalchemy.ext.asyncio import AsyncSession as _AS
    from app.common.storage import delete_file

    # Get or create site settings
    site_stmt = select(SiteSettings).limit(1)
    site_result = await db.execute(site_stmt)
    site = site_result.scalar_one_or_none()
    if not site:
        site = SiteSettings(app_name="CSI MKD YOUTH MOVEMENT")
        db.add(site)
        await db.flush()

    # Delete old QR if exists
    if site.payment_qr_url:
        delete_file(site.payment_qr_url)

    object_key, _ = save_upload_file(file, subdir="site/payment-qr")
    site.payment_qr_url = object_key
    await db.commit()
    clear_cache(SITE_SETTINGS_CACHE_KEY)

    return {
        "message": "Payment QR code uploaded successfully",
        "url": get_public_file_url(object_key),
    }


# Unit Details - MUST be last due to path parameter matching
async def _load_members_for_export(
    db: AsyncSession,
    *,
    registered_user_id: Optional[int] = None,
    district_id: Optional[int] = None,
) -> List[dict]:
    stmt = select(UnitMembers).options(
        selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
        *MEMBER_RESIDENCE_LOAD_OPTIONS,
    )
    if registered_user_id is not None:
        stmt = stmt.where(UnitMembers.registered_user_id == registered_user_id)
    if district_id is not None:
        stmt = stmt.join(CustomUser, CustomUser.id == UnitMembers.registered_user_id).join(
            UnitName, UnitName.id == CustomUser.unit_name_id
        ).where(UnitName.clergy_district_id == district_id)
    stmt = stmt.order_by(UnitMembers.name)
    result = await db.execute(stmt)
    members = list(result.scalars().all())
    rows: List[dict] = []
    for member in members:
        unit_name = ""
        district = ""
        if member.registered_user and member.registered_user.unit_name:
            unit_name = member.registered_user.unit_name.name or ""
            if member.registered_user.unit_name.district:
                district = member.registered_user.unit_name.district.name or ""
        rows.append(member_export_row(member, unit_name=unit_name, district=district))
    return rows


async def _load_officials_for_export(
    db: AsyncSession,
    *,
    registered_user_id: Optional[int] = None,
    district_id: Optional[int] = None,
) -> List[dict]:
    stmt = select(UnitOfficials).options(
        selectinload(UnitOfficials.registered_user).selectinload(CustomUser.unit_name)
    )
    if registered_user_id is not None:
        stmt = stmt.where(UnitOfficials.registered_user_id == registered_user_id)
    if district_id is not None:
        stmt = stmt.join(CustomUser, CustomUser.id == UnitOfficials.registered_user_id).join(
            UnitName, UnitName.id == CustomUser.unit_name_id
        ).where(UnitName.clergy_district_id == district_id)
    result = await db.execute(stmt)
    officials = list(result.scalars().all())
    return [
        {
            "unit_name": (
                official.registered_user.unit_name.name
                if official.registered_user and official.registered_user.unit_name
                else ""
            ),
            "president_name": official.president_name or "",
            "president_phone": official.president_phone or "",
            "vice_president_name": official.vice_president_name or "",
            "vice_president_phone": official.vice_president_phone or "",
            "secretary_name": official.secretary_name or "",
            "secretary_phone": official.secretary_phone or "",
            "joint_secretary_name": official.joint_secretary_name or "",
            "joint_secretary_phone": official.joint_secretary_phone or "",
            "treasurer_name": official.treasurer_name or "",
            "treasurer_phone": official.treasurer_phone or "",
        }
        for official in officials
    ]


async def _load_councilors_for_export(
    db: AsyncSession,
    *,
    registered_user_id: Optional[int] = None,
    district_id: Optional[int] = None,
) -> List[dict]:
    stmt = select(UnitCouncilor).options(
        selectinload(UnitCouncilor.registered_user).selectinload(CustomUser.unit_name),
        selectinload(UnitCouncilor.unit_member),
    )
    if registered_user_id is not None:
        stmt = stmt.where(UnitCouncilor.registered_user_id == registered_user_id)
    if district_id is not None:
        stmt = stmt.join(CustomUser, CustomUser.id == UnitCouncilor.registered_user_id).join(
            UnitName, UnitName.id == CustomUser.unit_name_id
        ).where(UnitName.clergy_district_id == district_id)
    result = await db.execute(stmt)
    councilors = list(result.scalars().all())
    return [
        {
            "name": councilor.unit_member.name if councilor.unit_member else "",
            "number": councilor.unit_member.number if councilor.unit_member else "",
            "unit_name": (
                councilor.registered_user.unit_name.name
                if councilor.registered_user and councilor.registered_user.unit_name
                else ""
            ),
        }
        for councilor in councilors
    ]


@router.get("/export/{export_type}")
async def export_unit_data(
    export_type: str,
    id: Optional[int] = Query(None, description="Unit user id or district id depending on export type"),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Export unit, member, official, or councilor data to Excel."""
    export_type = export_type.strip().lower()
    timestamp = format_timestamp_ist()

    if export_type == "members":
        rows = await _load_members_for_export(db)
        export_file = create_members_excel(rows)
        filename = f"unit_members_{timestamp}.xlsx"
    elif export_type == "unit":
        if id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit id is required")
        rows = await _load_members_for_export(db, registered_user_id=id)
        export_file = create_members_excel(rows)
        filename = f"unit_{id}_members_{timestamp}.xlsx"
    elif export_type == "officials":
        rows = await _load_officials_for_export(db)
        export_file = create_officials_excel(rows)
        filename = f"unit_officials_{timestamp}.xlsx"
    elif export_type == "councilors":
        rows = await _load_councilors_for_export(db)
        export_file = create_councilors_excel(rows)
        filename = f"unit_councilors_{timestamp}.xlsx"
    elif export_type == "district-officials":
        if id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="District id is required")
        rows = await _load_officials_for_export(db, district_id=id)
        export_file = create_officials_excel(rows)
        filename = f"district_{id}_officials_{timestamp}.xlsx"
    elif export_type == "district-councilors":
        if id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="District id is required")
        rows = await _load_councilors_for_export(db, district_id=id)
        export_file = create_councilors_excel(rows)
        filename = f"district_{id}_councilors_{timestamp}.xlsx"
    elif export_type == "unit-officials":
        if id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit id is required")
        rows = await _load_officials_for_export(db, registered_user_id=id)
        export_file = create_officials_excel(rows)
        filename = f"unit_{id}_officials_{timestamp}.xlsx"
    elif export_type == "unit-councilors":
        if id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit id is required")
        rows = await _load_councilors_for_export(db, registered_user_id=id)
        export_file = create_councilors_excel(rows)
        filename = f"unit_{id}_councilors_{timestamp}.xlsx"
    elif export_type == "units":
        units = await list_all_units(current_user=current_user, db=db)
        district_by_unit: dict[str, str] = {}
        unit_name_ids = [
            unit["user_id"]
            for unit in units
            if unit.get("user_id")
        ]
        if unit_name_ids:
            user_rows = await db.execute(
                select(CustomUser.id, UnitName.name, ClergyDistrict.name)
                .join(UnitName, UnitName.id == CustomUser.unit_name_id)
                .join(ClergyDistrict, ClergyDistrict.id == UnitName.clergy_district_id)
                .where(CustomUser.id.in_(unit_name_ids))
            )
            for user_id, unit_name, district_name in user_rows.all():
                district_by_unit[str(user_id)] = district_name or ""

        rows = [
            {
                "username": unit.get("username", ""),
                "unit_name": unit.get("unit_name", ""),
                "district": district_by_unit.get(str(unit.get("user_id", "")), ""),
                "member_count": unit.get("member_count", 0),
                "status": unit.get("status", ""),
                "payment_status": unit.get("payment_status", ""),
            }
            for unit in units
        ]
        export_file = create_units_excel(rows)
        filename = f"units_{timestamp}.xlsx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export type: {export_type}",
        )

    return StreamingResponse(
        export_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{user_id}/complete-registration", response_model=dict)
async def complete_unit_registration(
    user_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark a unit's current-season registration cycle as completed after admin approval."""
    cycle = await cycle_service.admin_complete_registration(db, user_id)
    return {
        "message": "Registration marked as completed.",
        "user_id": user_id,
        "registration_year": cycle.registration_year,
        "status": cycle.status,
    }


@router.post("/bulk-complete-legacy", response_model=dict)
async def bulk_complete_legacy_registrations(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk-mark older-season registration cycles as completed (no admin approval)."""
    updated = await cycle_service.bulk_complete_legacy_registrations(db, dry_run=False)
    clear_cache("admin_dashboard")
    return {
        "message": "Legacy registration cycles updated.",
        "updated_count": len(updated),
        "updated": updated,
    }


@router.get("/{unit_id}", response_model=dict)
async def view_unit_details(
    unit_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """View individual unit details."""
    stmt = select(CustomUser).where(CustomUser.id == unit_id).options(
        selectinload(CustomUser.unit_name)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Get officials
    stmt = select(UnitOfficials).where(UnitOfficials.registered_user_id == unit_id)
    result = await db.execute(stmt)
    officials = result.scalar_one_or_none()
    
    # Get councilors
    stmt = (
        select(UnitCouncilor)
        .where(UnitCouncilor.registered_user_id == unit_id)
        .options(selectinload(UnitCouncilor.unit_member))
    )
    result = await db.execute(stmt)
    councilors = list(result.scalars().all())
    
    # Get members
    stmt = (
        select(UnitMembers)
        .options(*MEMBER_RESIDENCE_LOAD_OPTIONS)
        .where(UnitMembers.registered_user_id == unit_id)
        .order_by(UnitMembers.name)
    )
    result = await db.execute(stmt)
    members = list(result.scalars().all())

    current_year = await cycle_service.get_current_registration_year(db)
    cycle_result = await db.execute(
        select(UnitRegistrationCycle).where(
            UnitRegistrationCycle.registered_user_id == unit_id,
            UnitRegistrationCycle.registration_year == current_year,
        )
    )
    cycle = cycle_result.scalar_one_or_none()

    registration_year = current_year
    
    # Convert officials to dict
    officials_dict = None
    if officials:
        officials_dict = {
            "id": officials.id,
            "president_designation": officials.president_designation,
            "president_name": officials.president_name,
            "president_phone": officials.president_phone,
            "vice_president_name": officials.vice_president_name,
            "vice_president_phone": officials.vice_president_phone,
            "secretary_name": officials.secretary_name,
            "secretary_phone": officials.secretary_phone,
            "joint_secretary_name": officials.joint_secretary_name,
            "joint_secretary_phone": officials.joint_secretary_phone,
            "treasurer_name": officials.treasurer_name,
            "treasurer_phone": officials.treasurer_phone,
        }
    
    # Convert councilors to list of dicts
    councilors_list = [
        {
            "id": c.id,
            "unit_member_id": c.unit_member_id,
            "member_name": c.unit_member.name if c.unit_member else None,
            "member_phone": c.unit_member.number if c.unit_member else None,
            "member_gender": c.unit_member.gender if c.unit_member else None,
        }
        for c in councilors
    ]
    
    members_list = [serialize_member(m) for m in members]
    member_count = len(members)

    settings_result = await db.execute(select(SiteSettings).limit(1))
    settings = settings_result.scalar_one_or_none()
    unit_registration_fee = (
        settings.unit_registration_fee
        if settings and settings.unit_registration_fee is not None
        else 100
    )
    unit_member_fee = (
        settings.unit_member_fee
        if settings and settings.unit_member_fee is not None
        else 10
    )
    total_amount = unit_registration_fee + member_count * unit_member_fee
    if cycle and cycle.total_fee_at_submit is not None:
        total_amount = cycle.total_fee_at_submit
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "unit_name": user.unit_name.name if user.unit_name else None,
        },
        "registration_year": registration_year,
        "cycle_status": cycle.status if cycle else None,
        "path_type": cycle.path_type if cycle else None,
        "officials": officials_dict,
        "councilors": councilors_list,
        "members": members_list,
        "member_count": member_count,
        "unit_registration_fee": unit_registration_fee,
        "unit_member_fee": unit_member_fee,
        "total_amount": total_amount,
    }

