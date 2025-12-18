"""Admin units router - administrative endpoints for units management."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.common.security import get_current_user
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
async def admin_home_page(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get admin dashboard statistics."""
    # Get districts and units
    stmt = select(ClergyDistrict)
    result = await db.execute(stmt)
    districts = list(result.scalars().all())
    
    stmt = select(UnitName)
    result = await db.execute(stmt)
    units = list(result.scalars().all())
    
    # Get units data excluding admin
    stmt = select(UnitRegistrationData).where(
        UnitRegistrationData.registered_user_id != current_user.id
    ).options(selectinload(UnitRegistrationData.registered_user))
    result = await db.execute(stmt)
    units_data = list(result.scalars().all())
    
    # Get unit members counts
    stmt = select(func.count()).select_from(UnitMembers)
    result = await db.execute(stmt)
    unit_members_count = result.scalar()
    
    stmt = select(func.count()).select_from(UnitMembers).where(UnitMembers.gender == 'M')
    result = await db.execute(stmt)
    unit_members_males_count = result.scalar()
    
    stmt = select(func.count()).select_from(UnitMembers).where(UnitMembers.gender == 'F')
    result = await db.execute(stmt)
    unit_females_count = result.scalar()
    
    # Get unit with max members
    stmt = select(
        UnitMembers.registered_user_id,
        func.count(UnitMembers.id).label('count')
    ).group_by(UnitMembers.registered_user_id).order_by(func.count(UnitMembers.id).desc())
    result = await db.execute(stmt)
    max_member_unit = result.first()
    
    if max_member_unit:
        stmt = select(CustomUser).where(CustomUser.id == max_member_unit[0]).options(
            selectinload(CustomUser.unit_name)
        )
        result = await db.execute(stmt)
        max_user = result.scalar_one()
        max_member_unit_name = max_user.unit_name.name if max_user.unit_name else "Unknown"
        max_member_count = max_member_unit[1]
    else:
        max_member_unit_name = "N/A"
        max_member_count = 0
    
    # Calculate registered districts and units
    dist_list = [district.name for district in districts]
    units_list = [unit.name for unit in units]
    
    # Get registered districts
    registered_district_names = set()
    for unit_data in units_data:
        if unit_data.registered_user and unit_data.registered_user.unit_name:
            registered_district_names.add(unit_data.registered_user.unit_name.district.name)
    
    completed_dist_count = len(registered_district_names)
    completed_units_count = len([u for u in units_data if u.status == "Registration Completed"])
    
    total_dist_count = len(dist_list)
    total_units_count = len(units_list)
    
    completed_dists_percent = (completed_dist_count / total_dist_count * 100) if total_dist_count > 0 else 0
    completed_units_percent = (completed_units_count / total_units_count * 100) if total_units_count > 0 else 0
    
    return {
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


@router.get("/all", response_model=List[dict])
async def list_all_units(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all registered units."""
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
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "unit_name": user.unit_name.name if user.unit_name else None,
        },
        "officials": officials,
        "councilors": councilors,
        "members": members,
        "member_count": len(members),
    }


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

