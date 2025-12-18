"""Admin units router - administrative endpoints for units management."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.common.security import get_current_user
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


@router.post("/transfer-requests/{request_id}/approve", response_model=UnitTransferRequestResponse)
async def approve_transfer_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a transfer request."""
    return await units_service.approve_unit_transfer_request(db, request_id)


@router.post("/transfer-requests/{request_id}/revert", response_model=UnitTransferRequestResponse)
async def revert_transfer_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert a transfer request."""
    return await units_service.revert_unit_transfer_request(db, request_id)


# Member Change Request Endpoints
@router.get("/member-change-requests", response_model=List[UnitMemberChangeRequestResponse])
async def list_member_change_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all member change requests."""
    return await units_service.get_member_change_requests(db)


@router.post("/member-change-requests/{request_id}/approve", response_model=UnitMemberChangeRequestResponse)
async def approve_member_change_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a member change request."""
    return await units_service.approve_member_info_change(db, request_id)


@router.post("/member-change-requests/{request_id}/revert", response_model=UnitMemberChangeRequestResponse)
async def revert_member_change_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert a member change request."""
    return await units_service.revert_member_info_change(db, request_id)


# Officials Change Request Endpoints
@router.get("/officials-change-requests", response_model=List[UnitOfficialsChangeRequestResponse])
async def list_officials_change_requests(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all officials change requests."""
    return await units_service.get_officials_change_requests(db)


@router.post("/officials-change-requests/{request_id}/approve", response_model=UnitOfficialsChangeRequestResponse)
async def approve_officials_change_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve an officials change request."""
    return await units_service.approve_officials_change(db, request_id)


@router.post("/officials-change-requests/{request_id}/revert", response_model=UnitOfficialsChangeRequestResponse)
async def revert_officials_change_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert an officials change request."""
    return await units_service.revert_officials_change(db, request_id)


@router.post("/officials-change-requests/{request_id}/reject", response_model=UnitOfficialsChangeRequestResponse)
async def reject_officials_change_request(
    request_id: int,
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


@router.post("/councilor-change-requests/{request_id}/approve", response_model=UnitCouncilorChangeRequestResponse)
async def approve_councilor_change_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a councilor change request."""
    return await units_service.approve_councilor_change(db, request_id)


@router.post("/councilor-change-requests/{request_id}/revert", response_model=UnitCouncilorChangeRequestResponse)
async def revert_councilor_change_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revert a councilor change request."""
    return await units_service.revert_councilor_change(db, request_id)


@router.post("/councilor-change-requests/{request_id}/reject", response_model=UnitCouncilorChangeRequestResponse)
async def reject_councilor_change_request(
    request_id: int,
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


@router.post("/member-add-requests/{request_id}/approve", response_model=UnitMemberAddRequestResponse)
async def approve_member_add_request(
    request_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve a member add request."""
    return await units_service.approve_member_add_request(db, request_id)


@router.post("/member-add-requests/{request_id}/reject", response_model=UnitMemberAddRequestResponse)
async def reject_member_add_request(
    request_id: int,
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
    
    # Get paginated data
    offset = (page - 1) * page_size
    stmt = select(ArchivedUnitMember).order_by(ArchivedUnitMember.archived_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    archived_list = list(result.scalars().all())
    
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
        }
        for member in archived_list
    ]
    
    return {"data": data, "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


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

