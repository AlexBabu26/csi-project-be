"""Units service layer - business logic for unit operations."""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.auth.models import (
    CustomUser,
    UnitDetails,
    UnitMembers,
    UnitOfficials,
    UnitCouncilor,
    UnitRegistrationData,
    UnitName,
    UserType,
)
from app.units.models import (
    ArchivedUnitMember,
    ArchivedMemberConcernRequest,
    RemovedUnitMember,
    UnitTransferRequest,
    UnitMemberChangeRequest,
    UnitOfficialsChangeRequest,
    UnitCouncilorChangeRequest,
    UnitMemberAddRequest,
    RequestStatus,
)
from app.units.schemas import (
    UnitTransferRequestCreate,
    UnitMemberChangeRequestCreate,
    UnitOfficialsChangeRequestCreate,
    UnitCouncilorChangeRequestCreate,
    UnitMemberAddRequestCreate,
    ArchivedMemberConcernRequestCreate,
)
from app.units import registration_cycle_service as cycle_service


# Unit Transfer Request Functions
async def get_transfer_destination_units(
    db: AsyncSession,
    user_id: int,
) -> List[Dict[str, Any]]:
    """List registered units that can receive a member transfer."""
    current_user_result = await db.execute(
        select(CustomUser).where(CustomUser.id == user_id)
    )
    current_user = current_user_result.scalar_one_or_none()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    stmt = (
        select(CustomUser)
        .where(
            CustomUser.user_type == UserType.UNIT,
            CustomUser.is_active.is_(True),
            CustomUser.unit_name_id.isnot(None),
            CustomUser.id != user_id,
        )
        .options(
            selectinload(CustomUser.unit_name).selectinload(UnitName.district)
        )
        .order_by(CustomUser.username)
    )
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    destinations: List[Dict[str, Any]] = []
    for user in users:
        if not user.unit_name_id or not user.unit_name:
            continue
        if current_user.unit_name_id and user.unit_name_id == current_user.unit_name_id:
            continue
        destinations.append(
            {
                "id": user.unit_name_id,
                "name": user.unit_name.name,
                "clergy_district": user.unit_name.district.name
                if user.unit_name.district
                else "Unknown",
                "unit_number": user.username,
            }
        )

    return destinations


async def create_unit_transfer_request(
    db: AsyncSession,
    user_id: int,
    data: UnitTransferRequestCreate,
) -> UnitTransferRequest:
    """
    Create a new unit transfer request.
    
    Args:
        db: Database session
        user_id: ID of the user creating the request
        data: Transfer request data
    
    Returns:
        Created transfer request
    
    Raises:
        HTTPException: If member or unit not found
    """
    # Verify member exists and belongs to user
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.id == data.unit_member_id,
            UnitMembers.registered_user_id == user_id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit member not found or does not belong to you"
        )
    
    # Verify destination unit exists
    stmt = select(UnitName).where(UnitName.id == data.destination_unit_id)
    result = await db.execute(stmt)
    destination_unit = result.scalar_one_or_none()
    
    if not destination_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination unit not found"
        )
    
    # Get current unit and registered user
    stmt = select(CustomUser).where(CustomUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one()
    
    # Create transfer request
    transfer_request = UnitTransferRequest(
        unit_member_id=data.unit_member_id,
        current_unit_id=user.unit_name_id,
        original_registered_user_id=user_id,
        destination_unit_id=data.destination_unit_id,
        reason=data.reason,
        proof=data.proof,
        status=RequestStatus.PENDING,
    )
    
    db.add(transfer_request)
    await db.commit()
    await db.refresh(transfer_request)
    
    return transfer_request


async def approve_unit_transfer_request(
    db: AsyncSession,
    request_id: int,
) -> UnitTransferRequest:
    """
    Approve a unit transfer request and update member's unit.
    
    Args:
        db: Database session
        request_id: ID of the transfer request
    
    Returns:
        Updated transfer request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get transfer request with member
    stmt = select(UnitTransferRequest).where(
        and_(
            UnitTransferRequest.id == request_id,
            UnitTransferRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    transfer_request = result.scalar_one_or_none()
    
    if not transfer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer request not found or already processed"
        )
    
    # Get the member
    stmt = select(UnitMembers).where(UnitMembers.id == transfer_request.unit_member_id)
    result = await db.execute(stmt)
    member = result.scalar_one()
    
    # Get new registered user for destination unit
    stmt = select(CustomUser).where(CustomUser.unit_name_id == transfer_request.destination_unit_id)
    result = await db.execute(stmt)
    new_registered_user = result.scalar_one_or_none()
    
    if not new_registered_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user found for destination unit"
        )
    
    # Update member's registered user
    member.registered_user_id = new_registered_user.id
    
    # Update transfer request status
    transfer_request.status = RequestStatus.APPROVED
    
    await db.commit()
    await db.refresh(transfer_request)
    
    return transfer_request


async def revert_unit_transfer_request(
    db: AsyncSession,
    request_id: int,
) -> UnitTransferRequest:
    """
    Revert an approved unit transfer request.
    
    Args:
        db: Database session
        request_id: ID of the transfer request
    
    Returns:
        Reverted transfer request
    
    Raises:
        HTTPException: If request not found or not approved
    """
    # Get approved transfer request
    stmt = select(UnitTransferRequest).where(
        and_(
            UnitTransferRequest.id == request_id,
            UnitTransferRequest.status == RequestStatus.APPROVED
        )
    )
    result = await db.execute(stmt)
    transfer_request = result.scalar_one_or_none()
    
    if not transfer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer request not found or not approved"
        )
    
    if not transfer_request.original_registered_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No original registered user to revert to"
        )
    
    # Get the member
    stmt = select(UnitMembers).where(UnitMembers.id == transfer_request.unit_member_id)
    result = await db.execute(stmt)
    member = result.scalar_one()
    
    # Restore original registered user
    member.registered_user_id = transfer_request.original_registered_user_id
    
    # Update status back to pending
    transfer_request.status = RequestStatus.PENDING
    
    await db.commit()
    await db.refresh(transfer_request)
    
    return transfer_request


async def reject_unit_transfer_request(
    db: AsyncSession,
    request_id: int,
) -> UnitTransferRequest:
    """
    Reject a pending unit transfer request.
    
    Args:
        db: Database session
        request_id: ID of the transfer request
    
    Returns:
        Rejected transfer request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get pending transfer request
    stmt = select(UnitTransferRequest).where(
        and_(
            UnitTransferRequest.id == request_id,
            UnitTransferRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    transfer_request = result.scalar_one_or_none()
    
    if not transfer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer request not found or not pending"
        )
    
    # Update status to rejected
    transfer_request.status = RequestStatus.REJECTED
    
    await db.commit()
    await db.refresh(transfer_request)
    
    return transfer_request


# Member Info Change Request Functions
async def create_member_info_change_request(
    db: AsyncSession,
    user_id: int,
    data: UnitMemberChangeRequestCreate,
) -> UnitMemberChangeRequest:
    """
    Create a member information change request.
    
    Args:
        db: Database session
        user_id: ID of the user creating the request
        data: Change request data
    
    Returns:
        Created change request
    
    Raises:
        HTTPException: If member not found or no changes detected
    """
    # Verify member exists and belongs to user
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.id == data.unit_member_id,
            UnitMembers.registered_user_id == user_id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit member not found or does not belong to you"
        )
    
    # Check if any changes were requested
    has_changes = (
        (data.name and data.name != member.name) or
        (data.gender and data.gender != member.gender) or
        (data.dob and data.dob != member.dob) or
        (data.blood_group and data.blood_group != member.blood_group) or
        (data.qualification and data.qualification != member.qualification)
    )
    
    if not has_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes detected in the provided information"
        )
    
    # Create change request
    change_request = UnitMemberChangeRequest(
        unit_member_id=data.unit_member_id,
        name=data.name if data.name and data.name != member.name else None,
        original_name=member.name,
        gender=data.gender if data.gender and data.gender != member.gender else None,
        original_gender=member.gender,
        dob=data.dob if data.dob and data.dob != member.dob else None,
        original_dob=member.dob,
        blood_group=data.blood_group if data.blood_group and data.blood_group != member.blood_group else None,
        original_blood_group=member.blood_group,
        qualification=data.qualification if data.qualification and data.qualification != member.qualification else None,
        original_qualification=member.qualification,
        reason=data.reason,
        proof=data.proof,
        status=RequestStatus.PENDING,
    )
    
    db.add(change_request)
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def approve_member_info_change(
    db: AsyncSession,
    request_id: int,
) -> UnitMemberChangeRequest:
    """
    Approve a member information change request and apply changes.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Updated change request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get change request
    stmt = select(UnitMemberChangeRequest).where(
        and_(
            UnitMemberChangeRequest.id == request_id,
            UnitMemberChangeRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or already processed"
        )
    
    # Get the member
    stmt = select(UnitMembers).where(UnitMembers.id == change_request.unit_member_id)
    result = await db.execute(stmt)
    member = result.scalar_one()
    
    # Apply changes
    if change_request.name:
        member.name = change_request.name
    if change_request.gender:
        member.gender = change_request.gender
    if change_request.dob:
        member.dob = change_request.dob
    if change_request.blood_group:
        member.blood_group = change_request.blood_group
    if change_request.qualification:
        member.qualification = change_request.qualification
    
    # Update status
    change_request.status = RequestStatus.APPROVED
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def revert_member_info_change(
    db: AsyncSession,
    request_id: int,
) -> UnitMemberChangeRequest:
    """
    Revert an approved member information change request.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Reverted change request
    
    Raises:
        HTTPException: If request not found or not approved
    """
    # Get approved change request
    stmt = select(UnitMemberChangeRequest).where(
        and_(
            UnitMemberChangeRequest.id == request_id,
            UnitMemberChangeRequest.status == RequestStatus.APPROVED
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or not approved"
        )
    
    # Get the member
    stmt = select(UnitMembers).where(UnitMembers.id == change_request.unit_member_id)
    result = await db.execute(stmt)
    member = result.scalar_one()
    
    # Restore original values
    if change_request.original_name is not None:
        member.name = change_request.original_name
    if change_request.original_gender is not None:
        member.gender = change_request.original_gender
    if change_request.original_dob is not None:
        member.dob = change_request.original_dob
    if change_request.original_blood_group is not None:
        member.blood_group = change_request.original_blood_group
    if change_request.original_qualification is not None:
        member.qualification = change_request.original_qualification
    
    # Update status back to pending
    change_request.status = RequestStatus.PENDING
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def reject_member_info_change(
    db: AsyncSession,
    request_id: int,
) -> UnitMemberChangeRequest:
    """
    Reject a pending member information change request.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Rejected change request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get pending change request
    stmt = select(UnitMemberChangeRequest).where(
        and_(
            UnitMemberChangeRequest.id == request_id,
            UnitMemberChangeRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or not pending"
        )
    
    # Update status to rejected
    change_request.status = RequestStatus.REJECTED
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


# Officials Change Request Functions
async def create_officials_change_request(
    db: AsyncSession,
    user_id: int,
    data: UnitOfficialsChangeRequestCreate,
) -> UnitOfficialsChangeRequest:
    """
    Create an officials information change request.
    
    Args:
        db: Database session
        user_id: ID of the user creating the request
        data: Change request data
    
    Returns:
        Created change request
    
    Raises:
        HTTPException: If officials not found or no changes detected
    """
    # Verify officials exist and belong to user
    stmt = select(UnitOfficials).where(
        and_(
            UnitOfficials.id == data.unit_official_id,
            UnitOfficials.registered_user_id == user_id
        )
    )
    result = await db.execute(stmt)
    officials = result.scalar_one_or_none()
    
    if not officials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit officials not found or do not belong to you"
        )
    
    # Check for changes
    has_changes = any([
        data.president_designation and data.president_designation != officials.president_designation,
        data.president_name and data.president_name != officials.president_name,
        data.president_phone and data.president_phone != officials.president_phone,
        data.vice_president_name and data.vice_president_name != officials.vice_president_name,
        data.vice_president_phone and data.vice_president_phone != officials.vice_president_phone,
        data.secretary_name and data.secretary_name != officials.secretary_name,
        data.secretary_phone and data.secretary_phone != officials.secretary_phone,
        data.joint_secretary_name and data.joint_secretary_name != officials.joint_secretary_name,
        data.joint_secretary_phone and data.joint_secretary_phone != officials.joint_secretary_phone,
        data.treasurer_name and data.treasurer_name != officials.treasurer_name,
        data.treasurer_phone and data.treasurer_phone != officials.treasurer_phone,
    ])
    
    if not has_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes detected in the provided information"
        )
    
    # Create change request with all fields
    change_request = UnitOfficialsChangeRequest(
        unit_official_id=data.unit_official_id,
        president_designation=data.president_designation if data.president_designation and data.president_designation != officials.president_designation else None,
        original_president_designation=officials.president_designation,
        president_name=data.president_name if data.president_name and data.president_name != officials.president_name else None,
        original_president_name=officials.president_name,
        president_phone=data.president_phone if data.president_phone and data.president_phone != officials.president_phone else None,
        original_president_phone=officials.president_phone,
        vice_president_name=data.vice_president_name if data.vice_president_name and data.vice_president_name != officials.vice_president_name else None,
        original_vice_president_name=officials.vice_president_name,
        vice_president_phone=data.vice_president_phone if data.vice_president_phone and data.vice_president_phone != officials.vice_president_phone else None,
        original_vice_president_phone=officials.vice_president_phone,
        secretary_name=data.secretary_name if data.secretary_name and data.secretary_name != officials.secretary_name else None,
        original_secretary_name=officials.secretary_name,
        secretary_phone=data.secretary_phone if data.secretary_phone and data.secretary_phone != officials.secretary_phone else None,
        original_secretary_phone=officials.secretary_phone,
        joint_secretary_name=data.joint_secretary_name if data.joint_secretary_name and data.joint_secretary_name != officials.joint_secretary_name else None,
        original_joint_secretary_name=officials.joint_secretary_name,
        joint_secretary_phone=data.joint_secretary_phone if data.joint_secretary_phone and data.joint_secretary_phone != officials.joint_secretary_phone else None,
        original_joint_secretary_phone=officials.joint_secretary_phone,
        treasurer_name=data.treasurer_name if data.treasurer_name and data.treasurer_name != officials.treasurer_name else None,
        original_treasurer_name=officials.treasurer_name,
        treasurer_phone=data.treasurer_phone if data.treasurer_phone and data.treasurer_phone != officials.treasurer_phone else None,
        original_treasurer_phone=officials.treasurer_phone,
        reason=data.reason,
        proof=data.proof,
        status=RequestStatus.PENDING,
    )
    
    db.add(change_request)
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def approve_officials_change(
    db: AsyncSession,
    request_id: int,
) -> UnitOfficialsChangeRequest:
    """
    Approve an officials change request and apply changes.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Updated change request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get change request
    stmt = select(UnitOfficialsChangeRequest).where(
        and_(
            UnitOfficialsChangeRequest.id == request_id,
            UnitOfficialsChangeRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or already processed"
        )
    
    # Get the officials
    stmt = select(UnitOfficials).where(UnitOfficials.id == change_request.unit_official_id)
    result = await db.execute(stmt)
    officials = result.scalar_one()
    
    # Apply changes
    if change_request.president_designation:
        officials.president_designation = change_request.president_designation
    if change_request.president_name:
        officials.president_name = change_request.president_name
    if change_request.president_phone:
        officials.president_phone = change_request.president_phone
    if change_request.vice_president_name:
        officials.vice_president_name = change_request.vice_president_name
    if change_request.vice_president_phone:
        officials.vice_president_phone = change_request.vice_president_phone
    if change_request.secretary_name:
        officials.secretary_name = change_request.secretary_name
    if change_request.secretary_phone:
        officials.secretary_phone = change_request.secretary_phone
    if change_request.joint_secretary_name:
        officials.joint_secretary_name = change_request.joint_secretary_name
    if change_request.joint_secretary_phone:
        officials.joint_secretary_phone = change_request.joint_secretary_phone
    if change_request.treasurer_name:
        officials.treasurer_name = change_request.treasurer_name
    if change_request.treasurer_phone:
        officials.treasurer_phone = change_request.treasurer_phone
    
    # Update status
    change_request.status = RequestStatus.APPROVED
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def revert_officials_change(
    db: AsyncSession,
    request_id: int,
) -> UnitOfficialsChangeRequest:
    """
    Revert an approved officials change request.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Reverted change request
    
    Raises:
        HTTPException: If request not found or not approved
    """
    # Get approved change request
    stmt = select(UnitOfficialsChangeRequest).where(
        and_(
            UnitOfficialsChangeRequest.id == request_id,
            UnitOfficialsChangeRequest.status == RequestStatus.APPROVED
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or not approved"
        )
    
    # Get the officials
    stmt = select(UnitOfficials).where(UnitOfficials.id == change_request.unit_official_id)
    result = await db.execute(stmt)
    officials = result.scalar_one()
    
    # Restore original values
    if change_request.original_president_designation is not None:
        officials.president_designation = change_request.original_president_designation
    if change_request.original_president_name is not None:
        officials.president_name = change_request.original_president_name
    if change_request.original_president_phone is not None:
        officials.president_phone = change_request.original_president_phone
    if change_request.original_vice_president_name is not None:
        officials.vice_president_name = change_request.original_vice_president_name
    if change_request.original_vice_president_phone is not None:
        officials.vice_president_phone = change_request.original_vice_president_phone
    if change_request.original_secretary_name is not None:
        officials.secretary_name = change_request.original_secretary_name
    if change_request.original_secretary_phone is not None:
        officials.secretary_phone = change_request.original_secretary_phone
    if change_request.original_joint_secretary_name is not None:
        officials.joint_secretary_name = change_request.original_joint_secretary_name
    if change_request.original_joint_secretary_phone is not None:
        officials.joint_secretary_phone = change_request.original_joint_secretary_phone
    if change_request.original_treasurer_name is not None:
        officials.treasurer_name = change_request.original_treasurer_name
    if change_request.original_treasurer_phone is not None:
        officials.treasurer_phone = change_request.original_treasurer_phone
    
    # Update status back to pending
    change_request.status = RequestStatus.PENDING
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def reject_officials_change(
    db: AsyncSession,
    request_id: int,
) -> UnitOfficialsChangeRequest:
    """
    Reject an officials change request.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Rejected change request
    
    Raises:
        HTTPException: If request not found
    """
    stmt = select(UnitOfficialsChangeRequest).where(
        UnitOfficialsChangeRequest.id == request_id
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found"
        )
    
    change_request.status = RequestStatus.REJECTED
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


# Councilor Change Request Functions
async def create_councilor_change_request(
    db: AsyncSession,
    user_id: int,
    data: UnitCouncilorChangeRequestCreate,
) -> UnitCouncilorChangeRequest:
    """
    Create a councilor change request.
    
    Args:
        db: Database session
        user_id: ID of the user creating the request
        data: Change request data
    
    Returns:
        Created change request
    
    Raises:
        HTTPException: If councilor not found or no changes detected
    """
    # Verify councilor exists and belongs to user
    stmt = select(UnitCouncilor).where(
        and_(
            UnitCouncilor.id == data.unit_councilor_id,
            UnitCouncilor.registered_user_id == user_id
        )
    )
    result = await db.execute(stmt)
    councilor = result.scalar_one_or_none()
    
    if not councilor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit councilor not found or does not belong to you"
        )
    
    # Check if new member is different
    if data.unit_member_id and data.unit_member_id == councilor.unit_member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes detected in the councilor assignment"
        )
    
    # If new member specified, verify it exists and belongs to user
    if data.unit_member_id:
        stmt = select(UnitMembers).where(
            and_(
                UnitMembers.id == data.unit_member_id,
                UnitMembers.registered_user_id == user_id
            )
        )
        result = await db.execute(stmt)
        new_member = result.scalar_one_or_none()
        
        if not new_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New unit member not found or does not belong to you"
            )
    
    # Create change request
    change_request = UnitCouncilorChangeRequest(
        unit_councilor_id=data.unit_councilor_id,
        unit_member_id=data.unit_member_id,
        original_unit_member_id=councilor.unit_member_id,
        reason=data.reason,
        proof=data.proof,
        status=RequestStatus.PENDING,
    )
    
    db.add(change_request)
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def approve_councilor_change(
    db: AsyncSession,
    request_id: int,
) -> UnitCouncilorChangeRequest:
    """
    Approve a councilor change request and apply changes.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Updated change request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get change request
    stmt = select(UnitCouncilorChangeRequest).where(
        and_(
            UnitCouncilorChangeRequest.id == request_id,
            UnitCouncilorChangeRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or already processed"
        )
    
    if not change_request.unit_member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No new member specified in request"
        )
    
    # Get the councilor
    stmt = select(UnitCouncilor).where(UnitCouncilor.id == change_request.unit_councilor_id)
    result = await db.execute(stmt)
    councilor = result.scalar_one()
    
    # Apply change
    councilor.unit_member_id = change_request.unit_member_id
    
    # Update status
    change_request.status = RequestStatus.APPROVED
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def revert_councilor_change(
    db: AsyncSession,
    request_id: int,
) -> UnitCouncilorChangeRequest:
    """
    Revert an approved councilor change request.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Reverted change request
    
    Raises:
        HTTPException: If request not found or not approved
    """
    # Get approved change request
    stmt = select(UnitCouncilorChangeRequest).where(
        and_(
            UnitCouncilorChangeRequest.id == request_id,
            UnitCouncilorChangeRequest.status == RequestStatus.APPROVED
        )
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found or not approved"
        )
    
    if not change_request.original_unit_member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No original member to revert to"
        )
    
    # Get the councilor
    stmt = select(UnitCouncilor).where(UnitCouncilor.id == change_request.unit_councilor_id)
    result = await db.execute(stmt)
    councilor = result.scalar_one()
    
    # Restore original member
    councilor.unit_member_id = change_request.original_unit_member_id
    
    # Update status back to pending
    change_request.status = RequestStatus.PENDING
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


async def reject_councilor_change(
    db: AsyncSession,
    request_id: int,
) -> UnitCouncilorChangeRequest:
    """
    Reject a councilor change request.
    
    Args:
        db: Database session
        request_id: ID of the change request
    
    Returns:
        Rejected change request
    
    Raises:
        HTTPException: If request not found
    """
    stmt = select(UnitCouncilorChangeRequest).where(
        UnitCouncilorChangeRequest.id == request_id
    )
    result = await db.execute(stmt)
    change_request = result.scalar_one_or_none()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found"
        )
    
    change_request.status = RequestStatus.REJECTED
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


# Member Add Request Functions
async def create_member_add_request(
    db: AsyncSession,
    user_id: int,
    data: UnitMemberAddRequestCreate,
) -> UnitMemberAddRequest:
    """
    Create a request to add a new member.
    
    Args:
        db: Database session
        user_id: ID of the user creating the request
        data: Add request data
    
    Returns:
        Created add request
    """
    add_request = UnitMemberAddRequest(
        registered_user_id=user_id,
        name=data.name,
        gender=data.gender,
        dob=data.dob,
        number=data.number,
        qualification=data.qualification,
        blood_group=data.blood_group,
        reason=data.reason,
        proof=data.proof,
        status=RequestStatus.PENDING,
    )
    
    db.add(add_request)
    await db.commit()
    await db.refresh(add_request)
    
    return add_request


async def approve_member_add_request(
    db: AsyncSession,
    request_id: int,
) -> Dict[str, Any]:
    """
    Approve a member add request and create the member.
    
    Args:
        db: Database session
        request_id: ID of the add request
    
    Returns:
        Approved add request
    
    Raises:
        HTTPException: If request not found or not pending
    """
    # Get add request
    stmt = select(UnitMemberAddRequest).where(
        and_(
            UnitMemberAddRequest.id == request_id,
            UnitMemberAddRequest.status == RequestStatus.PENDING
        )
    )
    result = await db.execute(stmt)
    add_request = result.scalar_one_or_none()
    
    if not add_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Add request not found or already processed"
        )
    
    current_year = await cycle_service.get_current_registration_year(db)
    cycle = await cycle_service.get_cycle(db, add_request.registered_user_id, current_year)

    new_member = UnitMembers(
        registered_user_id=add_request.registered_user_id,
        name=add_request.name,
        gender=add_request.gender,
        dob=add_request.dob,
        number=add_request.number,
        qualification=add_request.qualification,
        blood_group=add_request.blood_group,
        added_registration_cycle_id=cycle.id if cycle else None,
    )

    db.add(new_member)
    add_request.status = RequestStatus.APPROVED

    await cycle_service.adjust_fee_for_member_delta(
        db,
        registered_user_id=add_request.registered_user_id,
        delta_members=1,
    )

    await db.commit()
    await db.refresh(add_request)

    labels = await _lookup_unit_labels_for_users(db, [add_request.registered_user_id])
    unit_name, username = labels.get(add_request.registered_user_id, (None, None))
    return _member_add_request_dict(add_request, unit_name=unit_name, username=username)


async def reject_member_add_request(
    db: AsyncSession,
    request_id: int,
) -> Dict[str, Any]:
    """
    Reject a member add request.
    
    Args:
        db: Database session
        request_id: ID of the add request
    
    Returns:
        Rejected add request
    
    Raises:
        HTTPException: If request not found
    """
    stmt = select(UnitMemberAddRequest).where(
        UnitMemberAddRequest.id == request_id
    )
    result = await db.execute(stmt)
    add_request = result.scalar_one_or_none()
    
    if not add_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Add request not found"
        )
    
    add_request.status = RequestStatus.REJECTED
    
    await db.commit()
    await db.refresh(add_request)

    labels = await _lookup_unit_labels_for_users(db, [add_request.registered_user_id])
    unit_name, username = labels.get(add_request.registered_user_id, (None, None))
    return _member_add_request_dict(add_request, unit_name=unit_name, username=username)


# Archive Member Function
async def archive_unit_member(
    db: AsyncSession,
    member_id: int,
) -> RemovedUnitMember:
    """
    Archive a unit member to RemovedUnitMember and delete from UnitMembers.
    
    Args:
        db: Database session
        member_id: ID of the member to archive
    
    Returns:
        Created RemovedUnitMember record
    
    Raises:
        HTTPException: If member not found
    """
    # Get member
    stmt = select(UnitMembers).where(UnitMembers.id == member_id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit member not found"
        )
    
    # Create archived record
    removed_member = RemovedUnitMember(
        registered_user_id=member.registered_user_id,
        name=member.name,
        gender=member.gender,
        dob=member.dob,
        number=member.number,
        qualification=member.qualification,
        blood_group=member.blood_group,
    )
    
    db.add(removed_member)
    
    # Delete original member
    await db.delete(member)
    
    await db.commit()
    await db.refresh(removed_member)
    
    return removed_member


# List Functions for requests
async def get_transfer_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[Dict[str, Any]]:
    """Get list of transfer requests, optionally filtered."""
    stmt = select(UnitTransferRequest).options(
        selectinload(UnitTransferRequest.unit_member)
    )
    
    if user_id:
        stmt = stmt.where(UnitTransferRequest.original_registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitTransferRequest.status == status_filter)
    
    stmt = stmt.order_by(UnitTransferRequest.created_at.desc())
    
    result = await db.execute(stmt)
    requests = list(result.scalars().all())
    
    # Get unit names for current and destination units
    unit_ids = set()
    for req in requests:
        if req.current_unit_id:
            unit_ids.add(req.current_unit_id)
        if req.destination_unit_id:
            unit_ids.add(req.destination_unit_id)
    
    # Fetch unit names
    unit_names = {}
    if unit_ids:
        stmt = select(UnitName).where(UnitName.id.in_(unit_ids))
        result = await db.execute(stmt)
        for unit in result.scalars().all():
            unit_names[unit.id] = unit.name
    
    # Build response with additional fields
    return [
        {
            "id": req.id,
            "unit_member_id": req.unit_member_id,
            "destination_unit_id": req.destination_unit_id,
            "reason": req.reason,
            "current_unit_id": req.current_unit_id,
            "original_registered_user_id": req.original_registered_user_id,
            "proof": req.proof,
            "status": req.status,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
            "member_name": req.unit_member.name if req.unit_member else None,
            "current_unit_name": unit_names.get(req.current_unit_id) if req.current_unit_id else None,
            "destination_unit_name": unit_names.get(req.destination_unit_id) if req.destination_unit_id else None,
        }
        for req in requests
    ]


async def get_member_change_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[UnitMemberChangeRequest]:
    """Get list of member change requests, optionally filtered."""
    stmt = select(UnitMemberChangeRequest)
    
    if user_id:
        # Join with UnitMembers to filter by user
        stmt = stmt.join(UnitMembers, UnitMemberChangeRequest.unit_member_id == UnitMembers.id)
        stmt = stmt.where(UnitMembers.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitMemberChangeRequest.status == status_filter)
    
    stmt = stmt.order_by(UnitMemberChangeRequest.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_officials_change_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[Dict[str, Any]]:
    """Get list of officials change requests, optionally filtered."""
    stmt = (
        select(UnitOfficialsChangeRequest, UnitName.name.label("unit_name"))
        .join(UnitOfficials, UnitOfficialsChangeRequest.unit_official_id == UnitOfficials.id)
        .join(CustomUser, UnitOfficials.registered_user_id == CustomUser.id)
        .outerjoin(UnitName, CustomUser.unit_name_id == UnitName.id)
    )

    if user_id:
        stmt = stmt.where(UnitOfficials.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitOfficialsChangeRequest.status == status_filter)

    stmt = stmt.order_by(UnitOfficialsChangeRequest.created_at.desc())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": req.id,
            "unit_official_id": req.unit_official_id,
            "reason": req.reason,
            "president_designation": req.president_designation,
            "president_name": req.president_name,
            "president_phone": req.president_phone,
            "original_president_designation": req.original_president_designation,
            "original_president_name": req.original_president_name,
            "original_president_phone": req.original_president_phone,
            "vice_president_name": req.vice_president_name,
            "vice_president_phone": req.vice_president_phone,
            "original_vice_president_name": req.original_vice_president_name,
            "original_vice_president_phone": req.original_vice_president_phone,
            "secretary_name": req.secretary_name,
            "secretary_phone": req.secretary_phone,
            "original_secretary_name": req.original_secretary_name,
            "original_secretary_phone": req.original_secretary_phone,
            "joint_secretary_name": req.joint_secretary_name,
            "joint_secretary_phone": req.joint_secretary_phone,
            "original_joint_secretary_name": req.original_joint_secretary_name,
            "original_joint_secretary_phone": req.original_joint_secretary_phone,
            "treasurer_name": req.treasurer_name,
            "treasurer_phone": req.treasurer_phone,
            "original_treasurer_name": req.original_treasurer_name,
            "original_treasurer_phone": req.original_treasurer_phone,
            "proof": req.proof,
            "status": req.status,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
            "unit_name": unit_name,
        }
        for req, unit_name in rows
    ]


async def get_councilor_change_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[UnitCouncilorChangeRequest]:
    """Get list of councilor change requests, optionally filtered."""
    stmt = select(UnitCouncilorChangeRequest)
    
    if user_id:
        # Join with UnitCouncilor to filter by user
        stmt = stmt.join(UnitCouncilor, UnitCouncilorChangeRequest.unit_councilor_id == UnitCouncilor.id)
        stmt = stmt.where(UnitCouncilor.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitCouncilorChangeRequest.status == status_filter)
    
    stmt = stmt.order_by(UnitCouncilorChangeRequest.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _member_add_request_dict(
    req: UnitMemberAddRequest,
    *,
    unit_name: Optional[str] = None,
    username: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": req.id,
        "registered_user_id": req.registered_user_id,
        "name": req.name,
        "gender": req.gender,
        "dob": req.dob,
        "number": req.number,
        "qualification": req.qualification,
        "blood_group": req.blood_group,
        "reason": req.reason,
        "proof": req.proof,
        "status": req.status,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "unit_name": unit_name,
        "username": username,
    }


async def _lookup_unit_labels_for_users(
    db: AsyncSession,
    user_ids: List[int],
) -> Dict[int, tuple[Optional[str], Optional[str]]]:
    if not user_ids:
        return {}
    result = await db.execute(
        select(CustomUser.id, CustomUser.username, UnitName.name)
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .where(CustomUser.id.in_(user_ids))
    )
    return {
        row[0]: (row[2], row[1])
        for row in result.all()
    }


async def get_member_add_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[Dict[str, Any]]:
    """Get list of member add requests with unit labels, optionally filtered."""
    stmt = select(UnitMemberAddRequest)

    if user_id:
        stmt = stmt.where(UnitMemberAddRequest.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitMemberAddRequest.status == status_filter)

    stmt = stmt.order_by(UnitMemberAddRequest.created_at.desc())

    result = await db.execute(stmt)
    requests = list(result.scalars().all())
    labels = await _lookup_unit_labels_for_users(
        db,
        list({req.registered_user_id for req in requests}),
    )

    return [
        _member_add_request_dict(
            req,
            unit_name=labels.get(req.registered_user_id, (None, None))[0],
            username=labels.get(req.registered_user_id, (None, None))[1],
        )
        for req in requests
    ]


def _normalize_gender(gender: Optional[str]) -> Optional[str]:
    if not gender:
        return None
    value = gender.strip().upper()
    if value in ("M", "MALE"):
        return "M"
    if value in ("F", "FEMALE"):
        return "F"
    return value


def _summarize_archived_members(members: List[ArchivedUnitMember]) -> Dict[str, int]:
    male = 0
    female = 0
    for member in members:
        gender = _normalize_gender(member.gender)
        if gender == "M":
            male += 1
        elif gender == "F":
            female += 1
    return {"total": len(members), "male": male, "female": female}


async def get_recent_archived_members_for_unit(
    db: AsyncSession,
    user_id: int,
) -> Dict[str, Any]:
    """Return the most recent archive_year batch for a unit with summary stats."""
    year_stmt = (
        select(ArchivedUnitMember.archive_year)
        .where(
            ArchivedUnitMember.registered_user_id == user_id,
            ArchivedUnitMember.archive_year.isnot(None),
        )
        .distinct()
        .order_by(ArchivedUnitMember.archive_year.desc())
        .limit(1)
    )
    year_result = await db.execute(year_stmt)
    latest_year = year_result.scalar_one_or_none()

    if not latest_year:
        return {
            "archive_year": None,
            "archive_reason": None,
            "summary": {"total": 0, "male": 0, "female": 0},
            "members": [],
            "pending_concern_member_ids": [],
            "member_concerns": {},
        }

    members_stmt = (
        select(ArchivedUnitMember)
        .where(
            ArchivedUnitMember.registered_user_id == user_id,
            ArchivedUnitMember.archive_year == latest_year,
        )
        .order_by(ArchivedUnitMember.name)
    )
    members_result = await db.execute(members_stmt)
    members = list(members_result.scalars().all())

    archive_reason = next((m.archive_reason for m in members if m.archive_reason), None)
    member_ids = [m.id for m in members]

    pending_ids: List[int] = []
    member_concerns: Dict[str, Dict[str, Any]] = {}
    if member_ids:
        concerns_stmt = (
            select(ArchivedMemberConcernRequest)
            .where(
                ArchivedMemberConcernRequest.archived_unit_member_id.in_(member_ids),
                ArchivedMemberConcernRequest.registered_user_id == user_id,
            )
            .order_by(ArchivedMemberConcernRequest.created_at.desc())
        )
        concerns_result = await db.execute(concerns_stmt)
        for concern in concerns_result.scalars().all():
            key = str(concern.archived_unit_member_id)
            if key not in member_concerns:
                member_concerns[key] = {
                    "status": concern.status.value,
                    "admin_response": concern.admin_response,
                }
                if concern.status == RequestStatus.PENDING:
                    pending_ids.append(concern.archived_unit_member_id)

    return {
        "archive_year": latest_year,
        "archive_reason": archive_reason,
        "summary": _summarize_archived_members(members),
        "members": members,
        "pending_concern_member_ids": pending_ids,
        "member_concerns": member_concerns,
    }


async def _enrich_concern_requests(
    db: AsyncSession,
    requests: List[ArchivedMemberConcernRequest],
) -> List[Dict[str, Any]]:
    if not requests:
        return []

    archived_ids = {r.archived_unit_member_id for r in requests}
    user_ids = {r.registered_user_id for r in requests}

    archived_stmt = select(ArchivedUnitMember).where(ArchivedUnitMember.id.in_(archived_ids))
    archived_result = await db.execute(archived_stmt)
    archived_map = {m.id: m for m in archived_result.scalars().all()}

    users_stmt = (
        select(CustomUser, UnitName.name.label("unit_name"))
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .where(CustomUser.id.in_(user_ids))
    )
    users_result = await db.execute(users_stmt)
    unit_name_map = {user.id: unit_name for user, unit_name in users_result.all()}

    enriched: List[Dict[str, Any]] = []
    for request in requests:
        archived = archived_map.get(request.archived_unit_member_id)
        enriched.append({
            "id": request.id,
            "archived_unit_member_id": request.archived_unit_member_id,
            "registered_user_id": request.registered_user_id,
            "concern_text": request.concern_text,
            "admin_response": request.admin_response,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "updated_at": request.updated_at.isoformat(),
            "archived_member_name": archived.name if archived else None,
            "archived_member_gender": archived.gender if archived else None,
            "archived_member_dob": archived.dob.isoformat() if archived and archived.dob else None,
            "unit_name": unit_name_map.get(request.registered_user_id),
            "archive_year": archived.archive_year if archived else None,
        })
    return enriched


async def create_archived_member_concern_request(
    db: AsyncSession,
    user_id: int,
    data: ArchivedMemberConcernRequestCreate,
) -> ArchivedMemberConcernRequest:
    """Create a concern request for a recently archived member."""
    archived_stmt = select(ArchivedUnitMember).where(
        ArchivedUnitMember.id == data.archived_unit_member_id,
        ArchivedUnitMember.registered_user_id == user_id,
    )
    archived_result = await db.execute(archived_stmt)
    archived_member = archived_result.scalar_one_or_none()
    if not archived_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived member not found for this unit",
        )

    recent = await get_recent_archived_members_for_unit(db, user_id)
    recent_ids = {m.id for m in recent["members"]}
    if archived_member.id not in recent_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Concerns can only be raised for members from the most recent archive batch",
        )

    pending_stmt = select(ArchivedMemberConcernRequest).where(
        ArchivedMemberConcernRequest.archived_unit_member_id == data.archived_unit_member_id,
        ArchivedMemberConcernRequest.status == RequestStatus.PENDING,
    )
    pending_result = await db.execute(pending_stmt)
    if pending_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending concern already exists for this archived member",
        )

    concern_request = ArchivedMemberConcernRequest(
        archived_unit_member_id=data.archived_unit_member_id,
        registered_user_id=user_id,
        concern_text=data.concern_text.strip(),
        status=RequestStatus.PENDING,
    )
    db.add(concern_request)
    await db.commit()
    await db.refresh(concern_request)
    return concern_request


async def approve_archived_member_concern_request(
    db: AsyncSession,
    request_id: int,
    admin_response: Optional[str] = None,
) -> ArchivedMemberConcernRequest:
    """Mark a concern as reviewed and resolved."""
    stmt = select(ArchivedMemberConcernRequest).where(
        ArchivedMemberConcernRequest.id == request_id,
        ArchivedMemberConcernRequest.status == RequestStatus.PENDING,
    )
    result = await db.execute(stmt)
    concern_request = result.scalar_one_or_none()
    if not concern_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concern request not found or already processed",
        )

    concern_request.status = RequestStatus.APPROVED
    if admin_response:
        concern_request.admin_response = admin_response.strip()

    await db.commit()
    await db.refresh(concern_request)
    return concern_request


async def reject_archived_member_concern_request(
    db: AsyncSession,
    request_id: int,
    admin_response: Optional[str] = None,
) -> ArchivedMemberConcernRequest:
    """Reject a concern after admin review."""
    stmt = select(ArchivedMemberConcernRequest).where(
        ArchivedMemberConcernRequest.id == request_id,
        ArchivedMemberConcernRequest.status == RequestStatus.PENDING,
    )
    result = await db.execute(stmt)
    concern_request = result.scalar_one_or_none()
    if not concern_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concern request not found or already processed",
        )

    concern_request.status = RequestStatus.REJECTED
    if admin_response:
        concern_request.admin_response = admin_response.strip()

    await db.commit()
    await db.refresh(concern_request)
    return concern_request


async def get_archived_member_concern_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[Dict[str, Any]]:
    """Get archived member concern requests, optionally filtered by unit user."""
    stmt = select(ArchivedMemberConcernRequest)
    if user_id:
        stmt = stmt.where(ArchivedMemberConcernRequest.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(ArchivedMemberConcernRequest.status == status_filter)
    stmt = stmt.order_by(ArchivedMemberConcernRequest.created_at.desc())

    result = await db.execute(stmt)
    requests = list(result.scalars().all())
    return await _enrich_concern_requests(db, requests)


async def get_unit_my_requests(
    db: AsyncSession,
    user_id: int,
) -> Dict[str, Any]:
    """Aggregate all request types for a unit user's My Requests page."""
    transfers = await get_transfer_requests(db, user_id=user_id)
    member_info_changes = await get_member_change_requests(db, user_id=user_id)
    officials_changes = await get_officials_change_requests(db, user_id=user_id)
    councilor_changes = await get_councilor_change_requests(db, user_id=user_id)
    member_adds = await get_member_add_requests(db, user_id=user_id)
    archived_concerns = await get_archived_member_concern_requests(db, user_id=user_id)

    user_stmt = (
        select(CustomUser, UnitName.name.label("unit_name"))
        .outerjoin(UnitName, UnitName.id == CustomUser.unit_name_id)
        .where(CustomUser.id == user_id)
    )
    user_result = await db.execute(user_stmt)
    user_row = user_result.first()
    unit_name = user_row[1] if user_row else None

    def _serialize_transfer(req: Dict[str, Any]) -> Dict[str, Any]:
        created_at = req["created_at"]
        status = req["status"]
        return {
            "id": req["id"],
            "createdAt": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            "memberId": req["unit_member_id"],
            "memberName": req.get("member_name") or f"Member #{req['unit_member_id']}",
            "currentUnitId": req.get("current_unit_id") or 0,
            "currentUnitName": req.get("current_unit_name") or "",
            "destinationUnitId": req["destination_unit_id"],
            "destinationUnitName": req.get("destination_unit_name") or "",
            "reason": req["reason"],
            "status": status.value if hasattr(status, "value") else status,
            "proof": req.get("proof"),
        }

    def _serialize_member_info(req: UnitMemberChangeRequest) -> Dict[str, Any]:
        return {
            "id": req.id,
            "createdAt": req.created_at.isoformat(),
            "memberId": req.unit_member_id,
            "memberName": req.original_name or req.name or f"Member #{req.unit_member_id}",
            "unitName": unit_name or "",
            "changes": {
                k: v
                for k, v in {
                    "name": req.name,
                    "gender": req.gender,
                    "dob": req.dob.isoformat() if req.dob else None,
                    "bloodGroup": req.blood_group,
                    "qualification": req.qualification,
                }.items()
                if v is not None
            },
            "reason": req.reason,
            "status": req.status.value,
            "proof": req.proof,
        }

    def _serialize_officials(req: Dict[str, Any]) -> Dict[str, Any]:
        status = req["status"]
        created_at = req["created_at"]
        return {
            "id": req["id"],
            "createdAt": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            "unitId": user_id,
            "unitName": req.get("unit_name") or unit_name or "",
            "originalOfficials": {
                "presidentDesignation": req.get("original_president_designation"),
                "presidentName": req.get("original_president_name") or "",
                "presidentPhone": req.get("original_president_phone") or "",
                "vicePresidentName": req.get("original_vice_president_name") or "",
                "vicePresidentPhone": req.get("original_vice_president_phone") or "",
                "secretaryName": req.get("original_secretary_name") or "",
                "secretaryPhone": req.get("original_secretary_phone") or "",
                "jointSecretaryName": req.get("original_joint_secretary_name") or "",
                "jointSecretaryPhone": req.get("original_joint_secretary_phone") or "",
                "treasurerName": req.get("original_treasurer_name") or "",
                "treasurerPhone": req.get("original_treasurer_phone") or "",
            },
            "requestedChanges": {
                k: v
                for k, v in {
                    "presidentDesignation": req.get("president_designation"),
                    "presidentName": req.get("president_name"),
                    "presidentPhone": req.get("president_phone"),
                    "vicePresidentName": req.get("vice_president_name"),
                    "vicePresidentPhone": req.get("vice_president_phone"),
                    "secretaryName": req.get("secretary_name"),
                    "secretaryPhone": req.get("secretary_phone"),
                    "jointSecretaryName": req.get("joint_secretary_name"),
                    "jointSecretaryPhone": req.get("joint_secretary_phone"),
                    "treasurerName": req.get("treasurer_name"),
                    "treasurerPhone": req.get("treasurer_phone"),
                }.items()
                if v is not None
            },
            "reason": req["reason"],
            "status": status.value if hasattr(status, "value") else status,
            "proof": req.get("proof"),
        }

    def _serialize_councilor(req: UnitCouncilorChangeRequest) -> Dict[str, Any]:
        return {
            "id": req.id,
            "createdAt": req.created_at.isoformat(),
            "unitId": user_id,
            "unitName": unit_name or "",
            "councilorId": req.unit_councilor_id,
            "originalMemberId": req.original_unit_member_id or 0,
            "originalMemberName": f"Member #{req.original_unit_member_id or 0}",
            "newMemberId": req.unit_member_id,
            "newMemberName": f"Member #{req.unit_member_id}" if req.unit_member_id else None,
            "reason": req.reason,
            "status": req.status.value,
            "proof": req.proof,
        }

    def _serialize_member_add(req: Dict[str, Any]) -> Dict[str, Any]:
        created_at = req["created_at"]
        status = req["status"]
        return {
            "id": req["id"],
            "createdAt": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            "unitId": req["registered_user_id"],
            "unitName": req.get("unit_name") or unit_name or "",
            "name": req["name"],
            "gender": req["gender"],
            "number": req["number"],
            "dob": req["dob"].isoformat() if hasattr(req["dob"], "isoformat") else req["dob"],
            "qualification": req.get("qualification"),
            "bloodGroup": req.get("blood_group"),
            "reason": req["reason"],
            "status": status.value if hasattr(status, "value") else status,
            "proof": req.get("proof"),
        }

    def _serialize_concern(req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": req["id"],
            "createdAt": req["created_at"],
            "archivedMemberId": req["archived_unit_member_id"],
            "archivedMemberName": req.get("archived_member_name") or "",
            "archiveYear": req.get("archive_year"),
            "unitName": req.get("unit_name") or "",
            "concernText": req["concern_text"],
            "adminResponse": req.get("admin_response"),
            "status": req["status"],
        }

    return {
        "transfers": [_serialize_transfer(r) for r in transfers],
        "memberInfoChanges": [_serialize_member_info(r) for r in member_info_changes],
        "officialsChanges": [_serialize_officials(r) for r in officials_changes],
        "councilorChanges": [_serialize_councilor(r) for r in councilor_changes],
        "memberAdds": [_serialize_member_add(r) for r in member_adds],
        "archivedMemberConcerns": [_serialize_concern(r) for r in archived_concerns],
    }

