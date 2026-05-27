"""Admin units router - administrative endpoints for units management."""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.common.security import get_current_user, get_current_user_sync
from app.common.cache import get_cache, set_cache
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
)
from app.units.models import (
    UnitTransferRequest,
    UnitMemberChangeRequest,
    UnitOfficialsChangeRequest,
    UnitCouncilorChangeRequest,
    UnitMemberAddRequest,
    ArchivedUnitMember,
    RequestStatus,
)
from app.units.schemas import (
    UnitTransferRequestResponse,
    UnitMemberChangeRequestResponse,
    UnitOfficialsChangeRequestResponse,
    UnitCouncilorChangeRequestResponse,
    UnitMemberAddRequestResponse,
    RequestActionSchema,
)
from app.units import service as units_service

router = APIRouter()


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
    
    # Single query for completed registrations and district counts
    stmt = select(
        func.count(distinct(UnitRegistrationData.id)).label('completed_units'),
        func.count(distinct(UnitName.clergy_district_id)).label('completed_districts')
    ).select_from(UnitRegistrationData).join(
        CustomUser, UnitRegistrationData.registered_user_id == CustomUser.id
    ).join(
        UnitName, CustomUser.unit_name_id == UnitName.id
    ).where(
        UnitRegistrationData.status == "Registration Completed",
        UnitRegistrationData.registered_user_id != current_user.id
    )
    result = await db.execute(stmt)
    completed = result.one()
    completed_units_count = completed[0] or 0
    completed_dist_count = completed[1] or 0
    
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
    stmt = select(UnitRegistrationData).where(
        UnitRegistrationData.registered_user_id != current_user.id
    ).options(
        selectinload(UnitRegistrationData.registered_user).selectinload(CustomUser.unit_name)
    )
    result = await db.execute(stmt)
    units_data = list(result.scalars().all())
    
    return [
        {
            "id": unit_data.id,
            "user_id": unit_data.registered_user_id,
            "username": unit_data.registered_user.username,
            "unit_name": unit_data.registered_user.unit_name.name if unit_data.registered_user.unit_name else None,
            "status": unit_data.status,
        }
        for unit_data in units_data
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


# Unit Officials Endpoint with Pagination
@router.get("/officials", response_model=dict)
async def list_all_unit_officials(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
    page: int = 1,
    page_size: int = 50,
):
    """List all unit officials across all units with pagination."""
    # Get total count
    count_stmt = select(func.count()).select_from(UnitOfficials)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(UnitOfficials).options(
        selectinload(UnitOfficials.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district)
    ).offset(offset).limit(page_size)
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
):
    """List all unit councilors across all units with pagination."""
    # Get total count
    count_stmt = select(func.count()).select_from(UnitCouncilor)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(UnitCouncilor).options(
        selectinload(UnitCouncilor.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
        selectinload(UnitCouncilor.unit_member)
    ).offset(offset).limit(page_size)
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
):
    """List all unit members across all units with pagination."""
    # Get total count
    count_stmt = select(func.count()).select_from(UnitMembers)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(UnitMembers).options(
        selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district)
    ).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    members_list = list(result.scalars().all())
    
    data = [
        {
            "id": member.id,
            "registered_user_id": member.registered_user_id,
            "unit_name": member.registered_user.unit_name.name if member.registered_user and member.registered_user.unit_name else None,
            "district": member.registered_user.unit_name.district.name if member.registered_user and member.registered_user.unit_name and member.registered_user.unit_name.district else None,
            "name": member.name,
            "gender": member.gender,
            "dob": member.dob.isoformat() if member.dob else None,
            "age": member.age,
            "number": member.number,
            "qualification": member.qualification,
            "blood_group": member.blood_group,
        }
        for member in members_list
    ]
    
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
            selectinload(UnitMembers.registered_user)
            .selectinload(CustomUser.unit_name)
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

    data = [
        {
            "id": m.id,
            "name": m.name,
            "gender": m.gender,
            "dob": m.dob.isoformat() if m.dob else None,
            "age": m.age,
            "number": m.number,
            "qualification": m.qualification,
            "blood_group": m.blood_group,
            "unit_name": (
                m.registered_user.unit_name.name
                if m.registered_user and m.registered_user.unit_name else None
            ),
            "registered_user_id": m.registered_user_id,
        }
        for m in members
    ]

    return {
        "data": data,
        "total": len(data),
        "min_dob": min_dob.isoformat(),
        "max_dob": max_dob.isoformat(),
    }


# ── Bulk Archive ──────────────────────────────────────────────────────────────

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
            archived_at=datetime.utcnow(),
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

    active_member = UnitMembers(
        registered_user_id=archived.registered_user_id,
        name=archived.name,
        gender=archived.gender,
        dob=archived.dob,
        number=archived.number,
        qualification=archived.qualification,
        blood_group=archived.blood_group,
    )
    db.add(active_member)
    await db.delete(archived)
    await db.commit()

    return {"message": f"{archived.name} has been restored to active members"}


# ── Archived Unit Members List ────────────────────────────────────────────────

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
    if current_user.user_type != UserType.ADMIN:
        ss_result = await db.execute(select(SiteSettings))
        ss = ss_result.scalar_one_or_none()
        user_type_val = current_user.user_type.value if hasattr(current_user.user_type, 'value') else current_user.user_type
        is_district = user_type_val == "DISTRICT_OFFICIAL"
        is_unit = user_type_val == "UNIT"
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


# Unit Details - MUST be last due to path parameter matching
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
    stmt = select(UnitCouncilor).where(UnitCouncilor.registered_user_id == unit_id)
    result = await db.execute(stmt)
    councilors = list(result.scalars().all())
    
    # Get members
    stmt = select(UnitMembers).where(UnitMembers.registered_user_id == unit_id)
    result = await db.execute(stmt)
    members = list(result.scalars().all())
    
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
        {"id": c.id, "unit_member_id": c.unit_member_id}
        for c in councilors
    ]
    
    # Convert members to list of dicts
    members_list = [
        {
            "id": m.id,
            "name": m.name,
            "gender": m.gender,
            "dob": m.dob.isoformat() if m.dob else None,
            "number": m.number,
            "qualification": m.qualification,
            "blood_group": m.blood_group,
        }
        for m in members
    ]
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "unit_name": user.unit_name.name if user.unit_name else None,
        },
        "officials": officials_dict,
        "councilors": councilors_list,
        "members": members_list,
        "member_count": len(members),
    }

