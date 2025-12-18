"""Units user router - endpoints for registered unit users."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.common.security import get_current_user
from app.auth.models import (
    CustomUser,
    UnitDetails,
    UnitMembers,
    UnitOfficials,
    UnitCouncilor,
    UnitRegistrationData,
    UserType,
)
from app.units.models import (
    ArchivedUnitMember,
    UnitTransferRequest,
    UnitMemberChangeRequest,
    UnitOfficialsChangeRequest,
    UnitCouncilorChangeRequest,
    UnitMemberAddRequest,
)
from app.units.schemas import (
    UnitDetailsCreate,
    UnitDetailsResponse,
    UnitMemberCreate,
    UnitMemberUpdate,
    UnitMemberResponse,
    UnitOfficialsUpdate,
    UnitOfficialsResponse,
    UnitCouncilorCreate,
    UnitCouncilorResponse,
    StatusUpdate,
    UnitTransferRequestCreate,
    UnitTransferRequestResponse,
    UnitMemberChangeRequestCreate,
    UnitMemberChangeRequestResponse,
    UnitOfficialsChangeRequestCreate,
    UnitOfficialsChangeRequestResponse,
    UnitCouncilorChangeRequestCreate,
    UnitCouncilorChangeRequestResponse,
    UnitMemberAddRequestCreate,
    UnitMemberAddRequestResponse,
    ArchivedUnitMemberResponse,
)
from app.units import service as units_service

router = APIRouter()


async def get_current_unit_user(
    current_user: CustomUser = Depends(get_current_user),
) -> CustomUser:
    """Dependency to ensure user is a registered unit user."""
    if current_user.user_type != UserType.UNIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Unit user required."
        )
    return current_user


@router.get("/application-form", response_model=dict)
async def get_application_form(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get application form data with current registration status."""
    # Get registration data
    stmt = select(UnitRegistrationData).where(
        UnitRegistrationData.registered_user_id == current_user.id
    )
    result = await db.execute(stmt)
    registration_data = result.scalar_one_or_none()
    
    # Get unit details
    stmt = select(UnitDetails).where(UnitDetails.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_details = result.scalar_one_or_none()
    
    # Get officials
    stmt = select(UnitOfficials).where(UnitOfficials.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_officials = result.scalar_one_or_none()
    
    # Get members
    stmt = select(UnitMembers).where(UnitMembers.registered_user_id == current_user.id).order_by(UnitMembers.name)
    result = await db.execute(stmt)
    unit_members = list(result.scalars().all())
    
    # Get councilors
    stmt = select(UnitCouncilor).where(UnitCouncilor.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_councilors = list(result.scalars().all())
    
    # Calculate counts and amounts
    member_count = len(unit_members)
    members_amount = member_count * 10
    total_amount = members_amount + 100
    
    # Calculate councilor fields needed
    number_of_fields = 0
    if 1 <= member_count <= 25:
        number_of_fields = 1
    elif 26 <= member_count <= 50:
        number_of_fields = 2
    elif 51 <= member_count <= 75:
        number_of_fields = 3
    elif 76 <= member_count <= 100:
        number_of_fields = 4
    else:
        number_of_fields = 5
    
    return {
        "user_data": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "unit_name": current_user.unit_name.name if current_user.unit_name else None,
        },
        "registration_status": registration_data.status if registration_data else "Not Started",
        "unit_details": unit_details,
        "unit_officials": unit_officials,
        "unit_members": unit_members,
        "unit_councilors": unit_councilors,
        "member_count": member_count,
        "councilor_count": len(unit_councilors),
        "number_of_councilor_fields": number_of_fields,
        "members_amount": members_amount,
        "total_amount": total_amount,
    }


@router.post("/details", response_model=dict)
async def save_unit_details(
    data: UnitDetailsCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Save unit details and president information."""
    # Create or get unit details
    stmt = select(UnitDetails).where(UnitDetails.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_details = result.scalar_one_or_none()
    
    if not unit_details:
        unit_details = UnitDetails(
            registered_user_id=current_user.id,
            registration_year=2025,
        )
        db.add(unit_details)
    
    # Create or update officials with president info
    stmt = select(UnitOfficials).where(UnitOfficials.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_officials = result.scalar_one_or_none()
    
    if not unit_officials:
        unit_officials = UnitOfficials(registered_user_id=current_user.id)
        db.add(unit_officials)
    
    unit_officials.president_designation = data.president_designation
    unit_officials.president_name = data.president_name.upper()
    unit_officials.president_phone = data.president_phone
    
    # Update registration status
    stmt = select(UnitRegistrationData).where(UnitRegistrationData.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    registration_data = result.scalar_one_or_none()
    
    if registration_data:
        registration_data.status = "Unit Details"
    
    await db.commit()
    
    return {"message": "Unit details saved successfully"}


@router.post("/members", response_model=dict)
async def add_unit_member(
    data: UnitMemberCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Add a unit member."""
    # Check for duplicates
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.registered_user_id == current_user.id,
            UnitMembers.name == data.name.upper()
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A member with the same name already exists"
        )
    
    # Check for duplicate name, dob, number
    if data.dob and data.number:
        stmt = select(UnitMembers).where(
            and_(
                UnitMembers.name == data.name.upper(),
                UnitMembers.dob == data.dob,
                UnitMembers.number == data.number
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A member with the same name, DOB, and phone number already exists"
            )
    
    # Create member
    member = UnitMembers(
        registered_user_id=current_user.id,
        name=data.name.upper(),
        gender=data.gender,
        dob=data.dob,
        number=data.number,
        qualification=data.qualification,
        blood_group=data.blood_group,
    )
    
    db.add(member)
    await db.commit()
    await db.refresh(member)
    
    return {"message": "Unit member added successfully", "member_id": member.id}


@router.post("/members/submit", response_model=dict)
async def submit_unit_members(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark members section as complete."""
    stmt = select(UnitRegistrationData).where(UnitRegistrationData.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    registration_data = result.scalar_one_or_none()
    
    if registration_data:
        registration_data.status = "Unit Members Completed"
        await db.commit()
    
    return {"message": "Members section completed successfully"}


@router.post("/officials", response_model=dict)
async def add_unit_official(
    data: UnitOfficialsUpdate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Add or update unit officials."""
    stmt = select(UnitOfficials).where(UnitOfficials.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    officials = result.scalar_one_or_none()
    
    if not officials:
        officials = UnitOfficials(registered_user_id=current_user.id)
        db.add(officials)
    
    position = data.position
    name = data.name.upper()
    phone = data.phone
    
    if position == "President":
        if not data.designation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Designation is required for President"
            )
        officials.president_designation = data.designation
        officials.president_name = name
        officials.president_phone = phone
    elif position == "Vice President":
        officials.vice_president_name = name
        officials.vice_president_phone = phone
    elif position == "Secretary":
        officials.secretary_name = name
        officials.secretary_phone = phone
    elif position == "Joint Secretary":
        officials.joint_secretary_name = name
        officials.joint_secretary_phone = phone
    elif position == "Treasurer":
        officials.treasurer_name = name
        officials.treasurer_phone = phone
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid position"
        )
    
    await db.commit()
    
    return {"message": f"{position} data added successfully"}


@router.post("/officials/confirm", response_model=dict)
async def confirm_unit_officials(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark officials section as complete."""
    stmt = select(UnitRegistrationData).where(UnitRegistrationData.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    registration_data = result.scalar_one_or_none()
    
    if registration_data:
        registration_data.status = "Unit Officials Completed"
        await db.commit()
    
    return {"message": "Officials section completed successfully"}


@router.post("/councilors", response_model=dict)
async def add_unit_councilor(
    data: UnitCouncilorCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Add a unit councilor."""
    # Verify member exists
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.id == data.unit_member_id,
            UnitMembers.registered_user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit member not found"
        )
    
    # Check if already a councilor
    stmt = select(UnitCouncilor).where(
        and_(
            UnitCouncilor.registered_user_id == current_user.id,
            UnitCouncilor.unit_member_id == data.unit_member_id
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member is already a councilor"
        )
    
    # Create councilor
    councilor = UnitCouncilor(
        registered_user_id=current_user.id,
        unit_member_id=data.unit_member_id,
    )
    
    db.add(councilor)
    await db.commit()
    await db.refresh(councilor)
    
    return {"message": "Member added to unit council successfully", "councilor_id": councilor.id}


@router.post("/councilors/confirm", response_model=dict)
async def confirm_unit_councilors(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark councilors section as complete."""
    stmt = select(UnitRegistrationData).where(UnitRegistrationData.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    registration_data = result.scalar_one_or_none()
    
    if registration_data:
        registration_data.status = "Unit Councilors Completed"
        await db.commit()
    
    return {"message": "Councilors section completed successfully"}


@router.post("/declaration", response_model=dict)
async def complete_declaration(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Complete the declaration and finalize registration."""
    stmt = select(UnitRegistrationData).where(UnitRegistrationData.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    registration_data = result.scalar_one_or_none()
    
    if registration_data:
        registration_data.status = "Registration Completed"
        await db.commit()
    
    return {"message": "Registration completed successfully"}


@router.get("/archived-members", response_model=List[ArchivedUnitMemberResponse])
async def get_archived_members(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get list of archived members."""
    stmt = select(ArchivedUnitMember).where(
        ArchivedUnitMember.registered_user_id == current_user.id
    ).order_by(ArchivedUnitMember.name)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/transfer-request", response_model=UnitTransferRequestResponse)
async def create_transfer_request(
    data: UnitTransferRequestCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a unit transfer request."""
    return await units_service.create_unit_transfer_request(db, current_user.id, data)


@router.get("/transfer-requests", response_model=List[UnitTransferRequestResponse])
async def get_transfer_requests(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get transfer requests for current user."""
    return await units_service.get_transfer_requests(db, user_id=current_user.id)


@router.post("/member-change-request", response_model=UnitMemberChangeRequestResponse)
async def create_member_change_request(
    data: UnitMemberChangeRequestCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a member information change request."""
    return await units_service.create_member_info_change_request(db, current_user.id, data)


@router.get("/member-change-requests", response_model=List[UnitMemberChangeRequestResponse])
async def get_member_change_requests(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get member change requests for current user."""
    return await units_service.get_member_change_requests(db, user_id=current_user.id)


@router.post("/officials-change-request", response_model=UnitOfficialsChangeRequestResponse)
async def create_officials_change_request(
    data: UnitOfficialsChangeRequestCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create an officials change request."""
    return await units_service.create_officials_change_request(db, current_user.id, data)


@router.get("/officials-change-requests", response_model=List[UnitOfficialsChangeRequestResponse])
async def get_officials_change_requests(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get officials change requests for current user."""
    return await units_service.get_officials_change_requests(db, user_id=current_user.id)


@router.post("/councilor-change-request", response_model=UnitCouncilorChangeRequestResponse)
async def create_councilor_change_request(
    data: UnitCouncilorChangeRequestCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a councilor change request."""
    return await units_service.create_councilor_change_request(db, current_user.id, data)


@router.get("/councilor-change-requests", response_model=List[UnitCouncilorChangeRequestResponse])
async def get_councilor_change_requests(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get councilor change requests for current user."""
    return await units_service.get_councilor_change_requests(db, user_id=current_user.id)


@router.post("/member-add-request", response_model=UnitMemberAddRequestResponse)
async def create_member_add_request(
    data: UnitMemberAddRequestCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a request to add a new member."""
    return await units_service.create_member_add_request(db, current_user.id, data)


@router.put("/members/{member_id}", response_model=dict)
async def update_member(
    member_id: int,
    data: UnitMemberUpdate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a unit member."""
    # Get member
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.id == member_id,
            UnitMembers.registered_user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Update fields
    if data.name is not None:
        member.name = data.name.upper()
    if data.gender is not None:
        member.gender = data.gender
    if data.dob is not None:
        member.dob = data.dob
    if data.number is not None:
        member.number = data.number
    if data.qualification is not None:
        member.qualification = data.qualification
    if data.blood_group is not None:
        member.blood_group = data.blood_group
    
    await db.commit()
    
    return {"message": "Member updated successfully"}


@router.delete("/members/{member_id}", response_model=dict)
async def delete_member(
    member_id: int,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a unit member."""
    # Get member
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.id == member_id,
            UnitMembers.registered_user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    member_name = member.name
    member_phone = member.number
    
    # Remove from officials if present
    stmt = select(UnitOfficials).where(UnitOfficials.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    officials = result.scalar_one_or_none()
    
    if officials:
        if officials.vice_president_name == member_name and officials.vice_president_phone == member_phone:
            officials.vice_president_name = None
            officials.vice_president_phone = None
        if officials.secretary_name == member_name and officials.secretary_phone == member_phone:
            officials.secretary_name = None
            officials.secretary_phone = None
        if officials.joint_secretary_name == member_name and officials.joint_secretary_phone == member_phone:
            officials.joint_secretary_name = None
            officials.joint_secretary_phone = None
        if officials.treasurer_name == member_name and officials.treasurer_phone == member_phone:
            officials.treasurer_name = None
            officials.treasurer_phone = None
    
    # Remove from councilors
    stmt = select(UnitCouncilor).where(
        and_(
            UnitCouncilor.unit_member_id == member_id,
            UnitCouncilor.registered_user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    councilors = list(result.scalars().all())
    
    for councilor in councilors:
        await db.delete(councilor)
    
    # Delete member
    await db.delete(member)
    await db.commit()
    
    return {"message": "Member removed successfully"}


@router.put("/officials", response_model=dict)
async def update_officials(
    data: UnitOfficialsUpdate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update unit officials."""
    return await add_unit_official(data, current_user, db)


@router.put("/councilors/{councilor_id}", response_model=dict)
async def update_councilor(
    councilor_id: int,
    data: UnitCouncilorCreate,
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a councilor."""
    # Get councilor
    stmt = select(UnitCouncilor).where(
        and_(
            UnitCouncilor.id == councilor_id,
            UnitCouncilor.registered_user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    councilor = result.scalar_one_or_none()
    
    if not councilor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Councilor not found"
        )
    
    # Verify new member exists
    stmt = select(UnitMembers).where(
        and_(
            UnitMembers.id == data.unit_member_id,
            UnitMembers.registered_user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    councilor.unit_member_id = data.unit_member_id
    await db.commit()
    
    return {"message": "Councilor updated successfully"}


@router.get("/finish-registration", response_model=dict)
async def get_finish_registration(
    current_user: CustomUser = Depends(get_current_unit_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get final registration summary."""
    # Get all data
    stmt = select(UnitDetails).where(UnitDetails.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_details = result.scalar_one_or_none()
    
    stmt = select(UnitOfficials).where(UnitOfficials.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_officials = result.scalar_one_or_none()
    
    stmt = select(UnitMembers).where(UnitMembers.registered_user_id == current_user.id).order_by(UnitMembers.name)
    result = await db.execute(stmt)
    unit_members = list(result.scalars().all())
    
    stmt = select(UnitCouncilor).where(UnitCouncilor.registered_user_id == current_user.id)
    result = await db.execute(stmt)
    unit_councilors = list(result.scalars().all())
    
    members_count = len(unit_members)
    members_amount = members_count * 10
    total_amount = members_amount + 100
    
    return {
        "unit_details": unit_details,
        "unit_officials": unit_officials,
        "unit_members": unit_members,
        "unit_councilors": unit_councilors,
        "councilors_count": len(unit_councilors),
        "members_count": members_count,
        "members_amount": members_amount,
        "total_amount": total_amount,
    }

