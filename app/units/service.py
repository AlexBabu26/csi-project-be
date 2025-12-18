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
)
from app.units.models import (
    ArchivedUnitMember,
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
)


# Unit Transfer Request Functions
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
) -> UnitMemberAddRequest:
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
    
    # Create new member
    new_member = UnitMembers(
        registered_user_id=add_request.registered_user_id,
        name=add_request.name,
        gender=add_request.gender,
        dob=add_request.dob,
        number=add_request.number,
        qualification=add_request.qualification,
        blood_group=add_request.blood_group,
    )
    
    db.add(new_member)
    
    # Update status
    add_request.status = RequestStatus.APPROVED
    
    await db.commit()
    await db.refresh(add_request)
    
    return add_request


async def reject_member_add_request(
    db: AsyncSession,
    request_id: int,
) -> UnitMemberAddRequest:
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
    
    return add_request


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
) -> List[UnitOfficialsChangeRequest]:
    """Get list of officials change requests, optionally filtered."""
    stmt = select(UnitOfficialsChangeRequest)
    
    if user_id:
        # Join with UnitOfficials to filter by user
        stmt = stmt.join(UnitOfficials, UnitOfficialsChangeRequest.unit_official_id == UnitOfficials.id)
        stmt = stmt.where(UnitOfficials.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitOfficialsChangeRequest.status == status_filter)
    
    stmt = stmt.order_by(UnitOfficialsChangeRequest.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


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


async def get_member_add_requests(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_filter: Optional[RequestStatus] = None,
) -> List[UnitMemberAddRequest]:
    """Get list of member add requests, optionally filtered."""
    stmt = select(UnitMemberAddRequest)
    
    if user_id:
        stmt = stmt.where(UnitMemberAddRequest.registered_user_id == user_id)
    if status_filter:
        stmt = stmt.where(UnitMemberAddRequest.status == status_filter)
    
    stmt = stmt.order_by(UnitMemberAddRequest.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())

