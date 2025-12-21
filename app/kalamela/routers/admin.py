"""Kalamela admin router - comprehensive administrative endpoints."""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.common.security import get_current_user
from app.auth.models import CustomUser, UnitMembers, UnitName, ClergyDistrict, UserType
from app.kalamela.models import (
    IndividualEvent,
    GroupEvent,
    IndividualEventParticipation,
    GroupEventParticipation,
    KalamelaExcludeMembers,
    KalamelaPayments,
    IndividualEventScoreCard,
    GroupEventScoreCard,
    Appeal,
    AppealPayments,
    PaymentStatus,
    EventCategory,
    RegistrationFee,
    KalamelaRules,
)
from app.kalamela.schemas import (
    IndividualEventCreate,
    IndividualEventUpdate,
    IndividualEventResponse,
    GroupEventCreate,
    GroupEventUpdate,
    GroupEventResponse,
    ExcludeMemberCreate,
    ChestNumberUpdate,
    EventFilterSchema,
    IndividualScoreBulkCreate,
    IndividualScoreBulkUpdate,
    GroupScoreBulkCreate,
    GroupScoreBulkUpdate,
    IndividualScoreResponse,
    GroupScoreResponse,
    AppealResponse,
    AppealReply,
    KalamelaPaymentResponse,
    EventCategoryCreate,
    EventCategoryUpdate,
    EventCategoryResponse,
    RegistrationFeeCreate,
    RegistrationFeeUpdate,
    RegistrationFeeResponse,
    KalamelaRuleCreate,
    KalamelaRuleUpdate,
    KalamelaRuleResponse,
)
from app.kalamela import service as kalamela_service

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


# =============================================================================
# Event Category Management
# =============================================================================

@router.get("/categories", response_model=List[EventCategoryResponse])
async def list_categories(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all event categories."""
    stmt = select(EventCategory).order_by(EventCategory.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/categories", response_model=EventCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: EventCategoryCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new event category."""
    # Check if category with same name exists
    stmt = select(EventCategory).where(EventCategory.name == data.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = EventCategory(
        name=data.name,
        description=data.description,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return category


@router.get("/categories/{category_id}", response_model=EventCategoryResponse)
async def get_category(
    category_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific event category by ID."""
    stmt = select(EventCategory).where(EventCategory.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category


@router.put("/categories/{category_id}", response_model=EventCategoryResponse)
async def update_category(
    category_id: int,
    data: EventCategoryUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update an event category."""
    stmt = select(EventCategory).where(EventCategory.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    if data.name is not None:
        # Check for duplicate name
        stmt = select(EventCategory).where(
            EventCategory.name == data.name,
            EventCategory.id != category_id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
        category.name = data.name
    
    if data.description is not None:
        category.description = data.description
    
    await db.commit()
    await db.refresh(category)
    
    return category


@router.delete("/categories/{category_id}", response_model=dict)
async def delete_category(
    category_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an event category."""
    stmt = select(EventCategory).where(EventCategory.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if category is in use
    stmt = select(IndividualEvent).where(IndividualEvent.category_id == category_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category that is in use by events"
        )
    
    await db.delete(category)
    await db.commit()
    
    return {"message": "Category deleted successfully"}


# =============================================================================
# Registration Fee Management
# =============================================================================

@router.get("/registration-fees", response_model=List[RegistrationFeeResponse])
async def list_registration_fees(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all registration fees."""
    stmt = select(RegistrationFee).order_by(RegistrationFee.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/registration-fees", response_model=RegistrationFeeResponse, status_code=status.HTTP_201_CREATED)
async def create_registration_fee(
    data: RegistrationFeeCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new registration fee."""
    # Check if fee with same name exists
    stmt = select(RegistrationFee).where(RegistrationFee.name == data.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration fee with this name already exists"
        )
    
    fee = RegistrationFee(
        name=data.name,
        event_type=data.event_type,
        amount=data.amount,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(fee)
    await db.commit()
    await db.refresh(fee)
    
    return fee


@router.get("/registration-fees/{fee_id}", response_model=RegistrationFeeResponse)
async def get_registration_fee(
    fee_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific registration fee by ID."""
    stmt = select(RegistrationFee).where(RegistrationFee.id == fee_id)
    result = await db.execute(stmt)
    fee = result.scalar_one_or_none()
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration fee not found"
        )
    
    return fee


@router.put("/registration-fees/{fee_id}", response_model=RegistrationFeeResponse)
async def update_registration_fee(
    fee_id: int,
    data: RegistrationFeeUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a registration fee."""
    stmt = select(RegistrationFee).where(RegistrationFee.id == fee_id)
    result = await db.execute(stmt)
    fee = result.scalar_one_or_none()
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration fee not found"
        )
    
    if data.name is not None:
        # Check for duplicate name
        stmt = select(RegistrationFee).where(
            RegistrationFee.name == data.name,
            RegistrationFee.id != fee_id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration fee with this name already exists"
            )
        fee.name = data.name
    
    if data.event_type is not None:
        fee.event_type = data.event_type
    
    if data.amount is not None:
        fee.amount = data.amount
    
    fee.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(fee)
    
    return fee


@router.delete("/registration-fees/{fee_id}", response_model=dict)
async def delete_registration_fee(
    fee_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a registration fee."""
    stmt = select(RegistrationFee).where(RegistrationFee.id == fee_id)
    result = await db.execute(stmt)
    fee = result.scalar_one_or_none()
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration fee not found"
        )
    
    # Check if fee is in use by individual events
    stmt = select(IndividualEvent).where(IndividualEvent.registration_fee_id == fee_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete registration fee that is in use by individual events"
        )
    
    # Check if fee is in use by group events
    stmt = select(GroupEvent).where(GroupEvent.registration_fee_id == fee_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete registration fee that is in use by group events"
        )
    
    await db.delete(fee)
    await db.commit()
    
    return {"message": "Registration fee deleted successfully"}


# Dashboard
@router.get("/home", response_model=dict)
async def admin_home(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Admin dashboard with all events."""
    stmt_ind = select(IndividualEvent).options(
        selectinload(IndividualEvent.event_category),
        selectinload(IndividualEvent.registration_fee)
    ).order_by(IndividualEvent.name)
    result_ind = await db.execute(stmt_ind)
    individual_events = list(result_ind.scalars().all())
    
    stmt_grp = select(GroupEvent).options(
        selectinload(GroupEvent.registration_fee)
    ).order_by(GroupEvent.name)
    result_grp = await db.execute(stmt_grp)
    group_events = list(result_grp.scalars().all())
    
    # Convert to dicts for serialization
    individual_events_list = [
        {
            "id": e.id,
            "name": e.name,
            "category_id": e.category_id,
            "category_name": e.event_category.name if e.event_category else None,
            "registration_fee_id": e.registration_fee_id,
            "registration_fee_amount": e.registration_fee.amount if e.registration_fee else None,
            "description": e.description,
        }
        for e in individual_events
    ]
    
    group_events_list = [
        {
            "id": e.id,
            "name": e.name,
            "description": e.description,
            "registration_fee_id": e.registration_fee_id,
            "registration_fee_amount": e.registration_fee.amount if e.registration_fee else None,
            "min_allowed_limit": e.min_allowed_limit,
            "max_allowed_limit": e.max_allowed_limit,
            "per_unit_allowed_limit": e.per_unit_allowed_limit,
        }
        for e in group_events
    ]
    
    return {
        "individual_events": individual_events_list,
        "group_events": group_events_list,
    }


# Unit/Member Management
@router.get("/units", response_model=List[dict])
async def list_all_units(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all units with district information."""
    stmt = select(UnitName).options(
        selectinload(UnitName.district)
    ).order_by(UnitName.district_id, UnitName.name)
    result = await db.execute(stmt)
    units = list(result.scalars().all())
    
    return [
        {
            "id": unit.id,
            "name": unit.name,
            "district_name": unit.district.name,
            "district_id": unit.clergy_district_id,
        }
        for unit in units
    ]


@router.post("/units/{unit_id}/members", response_model=List[dict])
async def view_unit_members(
    unit_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """View all members of a unit with ages."""
    # Get unit
    stmt = select(UnitName).where(UnitName.id == unit_id)
    result = await db.execute(stmt)
    unit = result.scalar_one_or_none()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Get members
    stmt = select(UnitMembers).join(
        CustomUser, UnitMembers.registered_user_id == CustomUser.id
    ).where(CustomUser.unit_name_id == unit_id).options(
        selectinload(UnitMembers.registered_user)
    )
    result = await db.execute(stmt)
    members = list(result.scalars().all())
    
    # Get excluded list
    stmt = select(KalamelaExcludeMembers.members_id)
    result = await db.execute(stmt)
    excluded_ids = [row[0] for row in result.all()]
    
    members_with_age = []
    today = date.today()
    
    for member in members:
        age = 0
        if member.dob:
            age = today.year - member.dob.year - ((today.month, today.day) < (member.dob.month, member.dob.day))
        
        members_with_age.append({
            "id": member.id,
            "name": member.name,
            "gender": member.gender,
            "dob": member.dob,
            "number": member.number,
            "qualification": member.qualification,
            "blood_group": member.blood_group,
            "age": age,
            "is_excluded": member.id in excluded_ids,
        })
    
    return members_with_age


@router.put("/members/{member_id}", response_model=dict)
async def edit_member(
    member_id: int,
    name: str,
    gender: Optional[str] = None,
    dob: Optional[date] = None,
    number: Optional[str] = None,
    qualification: Optional[str] = None,
    blood_group: Optional[str] = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Edit unit member details."""
    stmt = select(UnitMembers).where(UnitMembers.id == member_id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    member.name = name
    if gender is not None:
        member.gender = gender
    if dob is not None:
        member.dob = dob
    if number is not None:
        member.number = number
    if qualification is not None:
        member.qualification = qualification
    if blood_group is not None:
        member.blood_group = blood_group
    
    await db.commit()
    
    return {"message": "Member updated successfully"}


@router.post("/members/{member_id}/exclude", response_model=dict)
async def exclude_member_endpoint(
    member_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Exclude a member from all events."""
    await kalamela_service.exclude_member(db, member_id)
    return {"message": "Member excluded from all events"}


@router.get("/excluded-members", response_model=List[dict])
async def list_excluded_members(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all excluded members."""
    stmt = select(KalamelaExcludeMembers).options(
        selectinload(KalamelaExcludeMembers.member)
    )
    result = await db.execute(stmt)
    excluded = list(result.scalars().all())
    
    return [
        {
            "id": ex.id,
            "member_id": ex.members_id,
            "member_name": ex.member.name,
        }
        for ex in excluded
    ]


@router.delete("/excluded-members/{exclusion_id}", response_model=dict)
async def remove_from_exclusion(
    exclusion_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Remove member from exclusion list."""
    await kalamela_service.remove_exclusion(db, exclusion_id)
    return {"message": "Member removed from exclusion list"}


# Event Management
@router.post("/events/individual", response_model=dict)
async def create_individual_event(
    data: IndividualEventCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create individual event."""
    # Validate category_id if provided
    if data.category_id:
        stmt = select(EventCategory).where(EventCategory.id == data.category_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id. Category does not exist."
            )
    
    # Validate registration_fee_id if provided
    registration_fee_amount = None
    if data.registration_fee_id:
        stmt = select(RegistrationFee).where(RegistrationFee.id == data.registration_fee_id)
        result = await db.execute(stmt)
        fee = result.scalar_one_or_none()
        if not fee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid registration_fee_id. Registration fee does not exist."
            )
        registration_fee_amount = fee.amount
    
    event = IndividualEvent(
        name=data.name,
        category_id=data.category_id,
        registration_fee_id=data.registration_fee_id,
        description=data.description,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Load the category relationship
    category_name = None
    if event.category_id:
        stmt = select(EventCategory).where(EventCategory.id == event.category_id)
        result = await db.execute(stmt)
        category = result.scalar_one_or_none()
        category_name = category.name if category else None
    
    return {
        "id": event.id,
        "name": event.name,
        "category_id": event.category_id,
        "category_name": category_name,
        "registration_fee_id": event.registration_fee_id,
        "registration_fee_amount": registration_fee_amount,
        "description": event.description,
        "created_on": event.created_on,
    }


@router.put("/events/individual/{event_id}", response_model=dict)
async def update_individual_event(
    event_id: int,
    data: IndividualEventUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update individual event."""
    stmt = select(IndividualEvent).where(IndividualEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if data.name is not None:
        event.name = data.name
    if data.category_id is not None:
        # Validate category_id
        stmt = select(EventCategory).where(EventCategory.id == data.category_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id. Category does not exist."
            )
        event.category_id = data.category_id
    if data.registration_fee_id is not None:
        # Validate registration_fee_id
        stmt = select(RegistrationFee).where(RegistrationFee.id == data.registration_fee_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid registration_fee_id. Registration fee does not exist."
            )
        event.registration_fee_id = data.registration_fee_id
    if data.description is not None:
        event.description = data.description
    
    await db.commit()
    await db.refresh(event)
    
    # Load the category and registration fee relationships
    category_name = None
    if event.category_id:
        stmt = select(EventCategory).where(EventCategory.id == event.category_id)
        result = await db.execute(stmt)
        category = result.scalar_one_or_none()
        category_name = category.name if category else None
    
    registration_fee_amount = None
    if event.registration_fee_id:
        stmt = select(RegistrationFee).where(RegistrationFee.id == event.registration_fee_id)
        result = await db.execute(stmt)
        fee = result.scalar_one_or_none()
        registration_fee_amount = fee.amount if fee else None
    
    return {
        "id": event.id,
        "name": event.name,
        "category_id": event.category_id,
        "category_name": category_name,
        "registration_fee_id": event.registration_fee_id,
        "registration_fee_amount": registration_fee_amount,
        "description": event.description,
        "created_on": event.created_on,
    }


@router.post("/events/group", response_model=dict)
async def create_group_event(
    data: GroupEventCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create group event."""
    # Validate registration_fee_id if provided
    registration_fee_amount = None
    if data.registration_fee_id:
        stmt = select(RegistrationFee).where(RegistrationFee.id == data.registration_fee_id)
        result = await db.execute(stmt)
        fee = result.scalar_one_or_none()
        if not fee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid registration_fee_id. Registration fee does not exist."
            )
        registration_fee_amount = fee.amount
    
    event = GroupEvent(
        name=data.name,
        description=data.description,
        registration_fee_id=data.registration_fee_id,
        max_allowed_limit=data.max_allowed_limit,
        min_allowed_limit=data.min_allowed_limit,
        per_unit_allowed_limit=data.per_unit_allowed_limit,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return {
        "id": event.id,
        "name": event.name,
        "description": event.description,
        "registration_fee_id": event.registration_fee_id,
        "registration_fee_amount": registration_fee_amount,
        "max_allowed_limit": event.max_allowed_limit,
        "min_allowed_limit": event.min_allowed_limit,
        "per_unit_allowed_limit": event.per_unit_allowed_limit,
        "created_on": event.created_on,
    }


@router.put("/events/group/{event_id}", response_model=dict)
async def update_group_event(
    event_id: int,
    data: GroupEventUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update group event."""
    stmt = select(GroupEvent).where(GroupEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if data.name is not None:
        event.name = data.name
    if data.description is not None:
        event.description = data.description
    if data.registration_fee_id is not None:
        # Validate registration_fee_id
        stmt = select(RegistrationFee).where(RegistrationFee.id == data.registration_fee_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid registration_fee_id. Registration fee does not exist."
            )
        event.registration_fee_id = data.registration_fee_id
    if data.max_allowed_limit is not None:
        event.max_allowed_limit = data.max_allowed_limit
    if data.min_allowed_limit is not None:
        event.min_allowed_limit = data.min_allowed_limit
    if data.per_unit_allowed_limit is not None:
        event.per_unit_allowed_limit = data.per_unit_allowed_limit
    
    await db.commit()
    await db.refresh(event)
    
    # Load the registration fee relationship
    registration_fee_amount = None
    if event.registration_fee_id:
        stmt = select(RegistrationFee).where(RegistrationFee.id == event.registration_fee_id)
        result = await db.execute(stmt)
        fee = result.scalar_one_or_none()
        registration_fee_amount = fee.amount if fee else None
    
    return {
        "id": event.id,
        "name": event.name,
        "description": event.description,
        "registration_fee_id": event.registration_fee_id,
        "registration_fee_amount": registration_fee_amount,
        "max_allowed_limit": event.max_allowed_limit,
        "min_allowed_limit": event.min_allowed_limit,
        "per_unit_allowed_limit": event.per_unit_allowed_limit,
        "created_on": event.created_on,
    }


@router.delete("/events/individual/{event_id}", response_model=dict)
async def delete_individual_event(
    event_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an individual event."""
    stmt = select(IndividualEvent).where(IndividualEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if event has participations
    stmt = select(IndividualEventParticipation).where(
        IndividualEventParticipation.individual_event_id == event_id
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete event that has participations. Remove all participations first."
        )
    
    await db.delete(event)
    await db.commit()
    
    return {"message": "Individual event deleted successfully"}


@router.delete("/events/group/{event_id}", response_model=dict)
async def delete_group_event(
    event_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a group event."""
    stmt = select(GroupEvent).where(GroupEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if event has participations
    stmt = select(GroupEventParticipation).where(
        GroupEventParticipation.group_event_id == event_id
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete event that has participations. Remove all participations first."
        )
    
    await db.delete(event)
    await db.commit()
    
    return {"message": "Group event deleted successfully"}


# Participant Management
@router.get("/participants/individual", response_model=dict)
async def list_individual_participants(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all individual participants grouped by event."""
    return await kalamela_service.view_all_individual_participants(db)


@router.get("/participants/group", response_model=dict)
async def list_group_participants(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all group participants grouped by event and team."""
    return await kalamela_service.view_all_group_participants(db)


@router.put("/participants/group/{participation_id}/chest-number", response_model=dict)
async def update_chest_number(
    participation_id: int,
    data: ChestNumberUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update chest number for group participation."""
    stmt = select(GroupEventParticipation).where(
        GroupEventParticipation.id == participation_id
    )
    result = await db.execute(stmt)
    participation = result.scalar_one_or_none()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )
    
    participation.chest_number = data.chest_number
    await db.commit()
    
    return {"message": "Chest number updated successfully"}


# Event Preview
@router.get("/events/preview", response_model=dict)
async def view_events_preview(
    district_id: Optional[int] = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    View events preview with participation counts and payment info.
    Can filter by district.
    """
    # Get all districts
    stmt = select(ClergyDistrict)
    result = await db.execute(stmt)
    districts = list(result.scalars().all())
    
    # Get all events with category and registration fee info
    stmt = select(IndividualEvent).options(
        selectinload(IndividualEvent.event_category),
        selectinload(IndividualEvent.registration_fee)
    )
    result = await db.execute(stmt)
    individual_events = list(result.scalars().all())
    
    stmt = select(GroupEvent).options(
        selectinload(GroupEvent.registration_fee)
    )
    result = await db.execute(stmt)
    group_events = list(result.scalars().all())
    
    # Get participation data
    individual_participations = await kalamela_service.view_all_individual_participants(db, district_id)
    group_participations = await kalamela_service.view_all_group_participants(db, district_id)
    
    # Calculate counts
    individual_count = sum(len(participants) for participants in individual_participations.values())
    
    total_group_teams = []
    for event_teams in group_participations.values():
        for team_code in event_teams.keys():
            total_group_teams.append(team_code)
    group_count = len(total_group_teams)
    
    # Get default fees from registration_fee table (fallback to hardcoded if not found)
    from app.kalamela.models import EventType
    
    # Get default individual fee
    stmt = select(RegistrationFee).where(RegistrationFee.event_type == EventType.INDIVIDUAL).order_by(RegistrationFee.id).limit(1)
    result = await db.execute(stmt)
    default_individual_fee = result.scalar_one_or_none()
    individual_fee_amount = default_individual_fee.amount if default_individual_fee else 50
    
    # Get default group fee
    stmt = select(RegistrationFee).where(RegistrationFee.event_type == EventType.GROUP).order_by(RegistrationFee.id).limit(1)
    result = await db.execute(stmt)
    default_group_fee = result.scalar_one_or_none()
    group_fee_amount = default_group_fee.amount if default_group_fee else 100
    
    individual_amount = individual_count * individual_fee_amount
    group_amount = group_count * group_fee_amount
    total_amount = individual_amount + group_amount
    
    # Get district name if filtered
    district_name = None
    if district_id:
        stmt = select(ClergyDistrict).where(ClergyDistrict.id == district_id)
        result = await db.execute(stmt)
        district = result.scalar_one_or_none()
        district_name = district.name if district else None
    
    # Get scored events
    stmt = select(func.distinct(IndividualEventScoreCard.event_participation_id)).join(
        IndividualEventParticipation,
        IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
    ).join(
        IndividualEvent,
        IndividualEventParticipation.individual_event_id == IndividualEvent.id
    )
    result = await db.execute(stmt)
    individual_scored_events = [row[0] for row in result.all()]
    
    stmt = select(func.distinct(GroupEventScoreCard.event_name))
    result = await db.execute(stmt)
    group_scored_events = [row[0] for row in result.all()]
    
    # Convert events to dicts for serialization
    individual_events_list = [
        {
            "id": e.id,
            "name": e.name,
            "category_id": e.category_id,
            "category_name": e.event_category.name if e.event_category else None,
            "registration_fee_id": e.registration_fee_id,
            "registration_fee_amount": e.registration_fee.amount if e.registration_fee else individual_fee_amount,
            "description": e.description,
        }
        for e in individual_events
    ]
    
    group_events_list = [
        {
            "id": e.id,
            "name": e.name,
            "description": e.description,
            "registration_fee_id": e.registration_fee_id,
            "registration_fee_amount": e.registration_fee.amount if e.registration_fee else group_fee_amount,
            "min_allowed_limit": e.min_allowed_limit,
            "max_allowed_limit": e.max_allowed_limit,
            "per_unit_allowed_limit": e.per_unit_allowed_limit,
        }
        for e in group_events
    ]
    
    return {
        "clergy_districts": [{"id": d.id, "name": d.name} for d in districts],
        "individual_events": individual_events_list,
        "group_events": group_events_list,
        "district": district_name,
        "individual_event_participations": individual_participations,
        "group_event_participations": group_participations,
        "individual_events_count": individual_count,
        "group_events_count": group_count,
        "individual_event_amount": individual_amount,
        "group_event_amount": group_amount,
        "total_amount_to_pay": total_amount,
        "individual_events_scores": individual_scored_events,
        "group_events_scores": group_scored_events,
    }


# Payments
@router.get("/payments", response_model=List[KalamelaPaymentResponse])
async def list_all_payments(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all payments."""
    stmt = select(KalamelaPayments).order_by(KalamelaPayments.created_on.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/payments/{payment_id}/approve", response_model=dict)
async def approve_payment(
    payment_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Approve payment."""
    await kalamela_service.update_payment_status(db, payment_id, PaymentStatus.PAID)
    return {"message": "Payment approved successfully"}


@router.post("/payments/{payment_id}/decline", response_model=dict)
async def decline_payment(
    payment_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Decline payment and clear proof."""
    stmt = select(KalamelaPayments).where(KalamelaPayments.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment.payment_status = PaymentStatus.DECLINED
    payment.payment_proof_path = None
    
    await db.commit()
    
    return {"message": "Payment declined successfully"}


# Scoring
@router.get("/scores/individual/event/{event_id}/candidates", response_model=List[dict])
async def get_individual_candidates_by_id(
    event_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get candidates for scoring by event ID."""
    stmt = select(IndividualEventParticipation).where(
        IndividualEventParticipation.individual_event_id == event_id
    ).options(
        selectinload(IndividualEventParticipation.individual_event),
        selectinload(IndividualEventParticipation.participant)
    ).order_by(IndividualEventParticipation.chest_number)
    result = await db.execute(stmt)
    participations = list(result.scalars().all())
    
    return [
        {
            "event_participation_id": p.id,
            "chest_number": p.chest_number,
            "participant_name": p.participant.name if p.participant else None,
            "event_name": p.individual_event.name if p.individual_event else None,
            "event_id": p.individual_event_id,
        }
        for p in participations
    ]


@router.post("/events/individual/candidates", response_model=List[dict])
async def get_individual_candidates(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get candidates for scoring by event name."""
    stmt = select(IndividualEventParticipation).join(
        IndividualEvent,
        IndividualEventParticipation.individual_event_id == IndividualEvent.id
    ).where(IndividualEvent.name == event_name).options(
        selectinload(IndividualEventParticipation.individual_event),
        selectinload(IndividualEventParticipation.participant)
    ).order_by(IndividualEventParticipation.chest_number)
    result = await db.execute(stmt)
    participations = list(result.scalars().all())
    
    return [
        {
            "event_participation_id": p.id,
            "chest_number": p.chest_number,
            "participant_name": p.participant.name,
            "event_name": p.individual_event.name,
        }
        for p in participations
    ]


@router.post("/scores/individual", response_model=dict)
async def add_individual_scores(
    data: IndividualScoreBulkCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk add individual scores."""
    scores = await kalamela_service.add_individual_scores_bulk(db, data)
    return {"message": f"Added {len(scores)} scores successfully"}


@router.get("/scores/group/event/{event_id}/candidates", response_model=List[dict])
async def get_group_candidates_by_id(
    event_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get team candidates for scoring by event ID."""
    stmt = select(
        GroupEventParticipation.chest_number,
        GroupEvent.name,
        GroupEvent.id
    ).join(
        GroupEvent,
        GroupEventParticipation.group_event_id == GroupEvent.id
    ).where(GroupEvent.id == event_id).distinct()
    result = await db.execute(stmt)
    teams = result.all()
    
    return [
        {
            "chest_number": team[0],
            "event_name": team[1],
            "event_id": team[2],
        }
        for team in teams
    ]


@router.post("/events/group/candidates", response_model=List[dict])
async def get_group_candidates(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get team candidates for scoring by event name."""
    stmt = select(
        GroupEventParticipation.chest_number,
        GroupEvent.name
    ).join(
        GroupEvent,
        GroupEventParticipation.group_event_id == GroupEvent.id
    ).where(GroupEvent.name == event_name).distinct()
    result = await db.execute(stmt)
    teams = result.all()
    
    return [
        {
            "chest_number": team[0],
            "event_name": team[1],
        }
        for team in teams
    ]


@router.post("/scores/group", response_model=dict)
async def add_group_scores(
    data: GroupScoreBulkCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk add group scores."""
    scores = await kalamela_service.add_group_scores_bulk(db, data)
    return {"message": f"Added {len(scores)} scores successfully"}


@router.get("/scores/individual", response_model=dict)
async def view_individual_scores(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """View all individual scores grouped by event."""
    # Get all distinct events that have scores
    stmt = select(func.distinct(IndividualEvent.name)).join(
        IndividualEventParticipation,
        IndividualEvent.id == IndividualEventParticipation.individual_event_id
    ).join(
        IndividualEventScoreCard,
        IndividualEventParticipation.id == IndividualEventScoreCard.event_participation_id
    )
    result = await db.execute(stmt)
    event_names = [row[0] for row in result.all()]
    
    results_dict = {}
    
    for event_name in event_names:
        stmt = select(IndividualEventScoreCard).join(
            IndividualEventParticipation,
            IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
        ).join(
            IndividualEvent,
            IndividualEventParticipation.individual_event_id == IndividualEvent.id
        ).where(IndividualEvent.name == event_name).options(
            selectinload(IndividualEventScoreCard.participation),
            selectinload(IndividualEventScoreCard.participant)
        ).order_by(IndividualEventScoreCard.total_points.desc())
        result = await db.execute(stmt)
        scores = list(result.scalars().all())
        
        if scores:
            results_dict[event_name] = [
                {
                    "id": s.id,
                    "event_participation_id": s.event_participation_id,
                    "participant_id": s.participant_id,
                    "awarded_mark": s.awarded_mark,
                    "grade": s.grade,
                    "total_points": s.total_points,
                    "added_on": s.added_on.isoformat() if s.added_on else None,
                    "chest_number": s.participation.chest_number if s.participation else None,
                    "participant_name": s.participant.name if s.participant else None,
                }
                for s in scores
            ]
    
    return {"results_dict": results_dict}


@router.get("/scores/group", response_model=dict)
async def view_group_scores(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """View all group scores grouped by event."""
    # Get all distinct events
    stmt = select(func.distinct(GroupEventScoreCard.event_name))
    result = await db.execute(stmt)
    event_names = [row[0] for row in result.all()]
    
    results_dict = {}
    
    for event_name in event_names:
        stmt = select(GroupEventScoreCard).where(
            GroupEventScoreCard.event_name == event_name
        ).order_by(GroupEventScoreCard.total_points.desc())
        result = await db.execute(stmt)
        scores = list(result.scalars().all())
        
        if scores:
            results_dict[event_name] = [
                {
                    "id": s.id,
                    "event_name": s.event_name,
                    "chest_number": s.chest_number,
                    "awarded_mark": s.awarded_mark,
                    "grade": s.grade,
                    "total_points": s.total_points,
                    "added_on": s.added_on.isoformat() if s.added_on else None,
                }
                for s in scores
            ]
    
    return {"results_dict": results_dict}


@router.post("/scores/individual/update", response_model=dict)
async def update_individual_scores(
    data: IndividualScoreBulkUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk update individual scores."""
    scores = await kalamela_service.update_individual_scores_bulk(db, data)
    return {"message": f"Updated {len(scores)} scores successfully"}


@router.post("/scores/group/update", response_model=dict)
async def update_group_scores(
    data: GroupScoreBulkUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk update group scores."""
    scores = await kalamela_service.update_group_scores_bulk(db, data)
    return {"message": f"Updated {len(scores)} scores successfully"}


@router.post("/scores/individual/event", response_model=dict)
async def get_scores_for_event(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get all scores for a specific individual event for editing."""
    stmt = select(IndividualEventScoreCard).join(
        IndividualEventParticipation,
        IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
    ).join(
        IndividualEvent,
        IndividualEventParticipation.individual_event_id == IndividualEvent.id
    ).where(IndividualEvent.name == event_name).options(
        selectinload(IndividualEventScoreCard.participation),
        selectinload(IndividualEventScoreCard.participant)
    ).order_by(IndividualEventScoreCard.total_points.desc())
    result = await db.execute(stmt)
    scores = list(result.scalars().all())
    
    return {
        "event_name": event_name,
        "event_scores": [
            {
                "id": s.id,
                "event_participation_id": s.event_participation_id,
                "participant_id": s.participant_id,
                "awarded_mark": s.awarded_mark,
                "grade": s.grade,
                "total_points": s.total_points,
                "added_on": s.added_on.isoformat() if s.added_on else None,
                "chest_number": s.participation.chest_number if s.participation else None,
                "participant_name": s.participant.name if s.participant else None,
            }
            for s in scores
        ],
    }


@router.post("/scores/group/event", response_model=dict)
async def get_group_scores_for_event(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get all scores for a specific group event for editing."""
    stmt = select(GroupEventScoreCard).where(
        GroupEventScoreCard.event_name == event_name
    ).order_by(GroupEventScoreCard.total_points.desc())
    result = await db.execute(stmt)
    scores = list(result.scalars().all())
    
    return {
        "event_name": event_name,
        "event_scores": [
            {
                "id": s.id,
                "event_name": s.event_name,
                "chest_number": s.chest_number,
                "awarded_mark": s.awarded_mark,
                "grade": s.grade,
                "total_points": s.total_points,
                "added_on": s.added_on.isoformat() if s.added_on else None,
            }
            for s in scores
        ],
    }


# Appeals
@router.get("/appeals", response_model=List[dict])
async def list_all_appeals(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all appeals with payment status."""
    stmt = select(AppealPayments).options(
        selectinload(AppealPayments.appeal).selectinload(Appeal.added_by)
    ).order_by(AppealPayments.created_on)
    result = await db.execute(stmt)
    appeal_payments = list(result.scalars().all())
    
    return [
        {
            "id": ap.id,
            "appeal_id": ap.appeal_id,
            "participant_name": ap.appeal.added_by.name if ap.appeal else None,
            "event_name": ap.appeal.event_name if ap.appeal else None,
            "chest_number": ap.appeal.chest_number if ap.appeal else None,
            "statement": ap.appeal.statement if ap.appeal else None,
            "reply": ap.appeal.reply if ap.appeal else None,
            "appeal_status": ap.appeal.status.value if ap.appeal else None,
            "total_amount": ap.total_amount_to_pay,
            "payment_status": ap.payment_status,
            "created_on": ap.created_on,
        }
        for ap in appeal_payments
    ]


@router.post("/appeals/{appeal_id}/reply", response_model=dict)
async def reply_to_appeal(
    appeal_id: int,
    data: AppealReply,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Reply to appeal and approve it."""
    appeal = await kalamela_service.reply_to_appeal(db, appeal_id, data.reply)
    return {"message": "Appeal replied and approved successfully"}


# Results
@router.get("/results/unit-wise", response_model=dict)
async def get_unit_wise_results(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get top 3 results per unit."""
    stmt = select(UnitName).order_by(UnitName.name)
    result = await db.execute(stmt)
    units = list(result.scalars().all())
    
    results_dict = {}
    
    for unit in units:
        # Get top 3 scores for this unit
        stmt = select(IndividualEventScoreCard).join(
            UnitMembers, IndividualEventScoreCard.participant_id == UnitMembers.id
        ).where(
            UnitMembers.registered_user.has(unit_name_id=unit.id)
        ).order_by(IndividualEventScoreCard.total_points.desc()).limit(3)
        result = await db.execute(stmt)
        scores = list(result.scalars().all())
        
        if scores:
            results_dict[unit.name] = [{
                "unit_results": [
                    {
                        "id": s.id,
                        "participant_id": s.participant_id,
                        "awarded_mark": s.awarded_mark,
                        "grade": s.grade,
                        "total_points": s.total_points,
                    }
                    for s in scores
                ]
            }]
    
    return {"results_dict": results_dict}


@router.get("/results/district-wise", response_model=dict)
async def get_district_wise_results(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get top 3 results per district with aggregated points."""
    stmt = select(ClergyDistrict).order_by(ClergyDistrict.name)
    result = await db.execute(stmt)
    districts = list(result.scalars().all())
    
    results_dict = {}
    
    for district in districts:
        # Get top 3 scores for this district
        stmt = select(IndividualEventScoreCard).join(
            UnitMembers, IndividualEventScoreCard.participant_id == UnitMembers.id
        ).join(
            CustomUser, UnitMembers.registered_user_id == CustomUser.id
        ).join(
            UnitName, CustomUser.unit_name_id == UnitName.id
        ).where(
            UnitName.clergy_district_id == district.id
        ).order_by(IndividualEventScoreCard.total_points.desc()).limit(3)
        result = await db.execute(stmt)
        scores = list(result.scalars().all())
        
        # Calculate total points
        total_points = sum(s.total_points for s in scores)
        
        if scores:
            results_dict[district.name] = [{
                "district_results": [
                    {
                        "id": s.id,
                        "participant_id": s.participant_id,
                        "awarded_mark": s.awarded_mark,
                        "grade": s.grade,
                        "total_points": s.total_points,
                    }
                    for s in scores
                ],
                "total_points": total_points,
            }]
    
    return {"results_dict": results_dict}


# Excel Exports
@router.post("/export/events")
async def export_events_data(
    filters: EventFilterSchema,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Export call sheet with full formatting."""
    from app.common.exporter import export_kalamela_call_sheet
    
    individual_participations = await kalamela_service.view_all_individual_participants(
        db, filters.district_id
    )
    group_participations = await kalamela_service.view_all_group_participants(
        db, filters.district_id
    )
    
    # Get district name
    district_name = "All Districts"
    if filters.district_id:
        stmt = select(ClergyDistrict).where(ClergyDistrict.id == filters.district_id)
        result = await db.execute(stmt)
        district = result.scalar_one_or_none()
        if district:
            district_name = district.name
    
    excel_file = export_kalamela_call_sheet(
        individual_participations,
        group_participations,
        district_name,
    )
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=kalamela_call_sheet_{district_name}.xlsx"}
    )


@router.post("/export/chest-numbers")
async def export_chest_numbers(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Export all individual chest numbers."""
    from app.common.exporter import export_kalamela_chest_numbers
    
    individual_participations = await kalamela_service.view_all_individual_participants(db)
    
    excel_file = export_kalamela_chest_numbers(
        individual_participations,
        "All Districts",
    )
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=kalamela_chest_numbers.xlsx"}
    )


@router.post("/export/results")
async def export_results(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Export top 3 results for all events."""
    from app.common.exporter import export_kalamela_results
    
    # Get all events
    stmt = select(IndividualEvent)
    result = await db.execute(stmt)
    individual_events = list(result.scalars().all())
    
    stmt = select(GroupEvent)
    result = await db.execute(stmt)
    group_events = list(result.scalars().all())
    
    # Get top 3 for each individual event
    individual_results = {}
    for event in individual_events:
        stmt = select(IndividualEventScoreCard).join(
            IndividualEventParticipation,
            IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
        ).where(
            IndividualEventParticipation.individual_event_id == event.id
        ).options(
            selectinload(IndividualEventScoreCard.participant).selectinload(
                UnitMembers.registered_user
            ).selectinload(CustomUser.unit_name),
            selectinload(IndividualEventScoreCard.participation),
        ).order_by(IndividualEventScoreCard.total_points.desc()).limit(3)
        result = await db.execute(stmt)
        top_scores = list(result.scalars().all())
        
        if top_scores:
            individual_results[event.name] = [
                {
                    "position": idx + 1,
                    "participant_name": score.participant.name,
                    "unit_name": score.participant.registered_user.unit_name.name,
                    "total_points": score.total_points,
                }
                for idx, score in enumerate(top_scores)
            ]
    
    # Get top 3 for each group event
    group_results = {}
    for event in group_events:
        stmt = select(GroupEventScoreCard).where(
            GroupEventScoreCard.event_name == event.name
        ).order_by(GroupEventScoreCard.total_points.desc()).limit(3)
        result = await db.execute(stmt)
        top_scores = list(result.scalars().all())
        
        if top_scores:
            group_results[event.name] = [
                {
                    "position": idx + 1,
                    "chest_number": score.chest_number,
                    "total_points": score.total_points,
                }
                for idx, score in enumerate(top_scores)
            ]
    
    excel_file = export_kalamela_results(individual_results, group_results)
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=kalamela_results.xlsx"}
    )


# =============================================================================
# Kalamela Rules Management
# =============================================================================

@router.get("/rules", response_model=List[KalamelaRuleResponse])
async def list_rules(
    category: Optional[str] = None,
    active_only: bool = True,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all Kalamela rules.
    
    Query Parameters:
    - category: Filter by rule category (age_restriction, participation_limit, fee)
    - active_only: If True, only return active rules (default: True)
    """
    stmt = select(KalamelaRules)
    
    if active_only:
        stmt = stmt.where(KalamelaRules.is_active == True)
    
    if category:
        from app.kalamela.models import RuleCategory
        try:
            rule_cat = RuleCategory(category)
            stmt = stmt.where(KalamelaRules.rule_category == rule_cat)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: age_restriction, participation_limit, fee"
            )
    
    stmt = stmt.order_by(KalamelaRules.rule_category, KalamelaRules.rule_key)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/rules/grouped", response_model=dict)
async def get_rules_grouped(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get all active rules grouped by category for easier frontend consumption.
    
    Returns:
    {
        "age_restrictions": {
            "senior_dob_start": "1991-01-11",
            "senior_dob_end": "2005-01-10",
            ...
        },
        "participation_limits": {
            "max_individual_events_per_person": "5",
            ...
        },
        "fees": {
            "individual_event_fee": "50",
            ...
        }
    }
    """
    stmt = select(KalamelaRules).where(KalamelaRules.is_active == True)
    result = await db.execute(stmt)
    rules = list(result.scalars().all())
    
    grouped = {
        "age_restrictions": {},
        "participation_limits": {},
        "fees": {},
    }
    
    for rule in rules:
        if rule.rule_category.value == "age_restriction":
            grouped["age_restrictions"][rule.rule_key] = rule.rule_value
        elif rule.rule_category.value == "participation_limit":
            grouped["participation_limits"][rule.rule_key] = rule.rule_value
        elif rule.rule_category.value == "fee":
            grouped["fees"][rule.rule_key] = rule.rule_value
    
    return grouped


@router.get("/rules/{rule_id}", response_model=KalamelaRuleResponse)
async def get_rule(
    rule_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a single rule by ID."""
    stmt = select(KalamelaRules).where(KalamelaRules.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    return rule


@router.put("/rules/{rule_id}", response_model=KalamelaRuleResponse)
async def update_rule(
    rule_id: int,
    data: KalamelaRuleUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a Kalamela rule.
    
    Note: rule_key and rule_category cannot be changed to maintain data integrity.
    Only rule_value, display_name, description, and is_active can be updated.
    """
    stmt = select(KalamelaRules).where(KalamelaRules.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    # Update fields
    if data.rule_value is not None:
        rule.rule_value = data.rule_value
    if data.display_name is not None:
        rule.display_name = data.display_name
    if data.description is not None:
        rule.description = data.description
    if data.is_active is not None:
        rule.is_active = data.is_active
    
    rule.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


@router.post("/rules", response_model=KalamelaRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: KalamelaRuleCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new Kalamela rule.
    
    Note: This is typically not needed as rules are seeded during migration.
    Use this only if you need to add new rules dynamically.
    """
    from app.kalamela.models import RuleCategory
    
    # Check if rule_key already exists
    stmt = select(KalamelaRules).where(KalamelaRules.rule_key == data.rule_key)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule with this key already exists"
        )
    
    rule = KalamelaRules(
        rule_key=data.rule_key,
        rule_category=RuleCategory(data.rule_category.value),
        rule_value=data.rule_value,
        display_name=data.display_name,
        description=data.description,
        is_active=data.is_active,
        updated_by_id=current_user.id,
    )
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a Kalamela rule.
    
    Warning: This permanently removes the rule. Consider deactivating instead.
    """
    stmt = select(KalamelaRules).where(KalamelaRules.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    await db.delete(rule)
    await db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
