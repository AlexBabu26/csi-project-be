"""Kalamela official router - district official functionalities."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.common.security import get_current_user
from app.auth.models import CustomUser, UnitMembers, UnitName, UserType
from app.kalamela.models import (
    IndividualEvent,
    GroupEvent,
    IndividualEventParticipation,
    GroupEventParticipation,
    KalamelaPayments,
    KalamelaExcludeMembers,
    SeniorityCategory,
)
from app.kalamela.schemas import (
    IndividualParticipationCreate,
    GroupParticipationCreate,
    SelectEventSchema,
    KalamelaPaymentCreate,
    KalamelaPaymentResponse,
)
from app.kalamela import service as kalamela_service

# Seniority date ranges (from service.py)
JUNIOR_DOB_START = date(2004, 1, 12)
JUNIOR_DOB_END = date(2010, 6, 30)
SENIOR_DOB_START = date(1989, 7, 1)
SENIOR_DOB_END = date(2004, 1, 11)

router = APIRouter()


async def get_official_user(
    current_user: CustomUser = Depends(get_current_user),
) -> CustomUser:
    """Dependency to ensure user is a district official."""
    if current_user.user_type != UserType.DISTRICT_OFFICIAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. District official privileges required."
        )
    return current_user


def get_participation_category(dob: Optional[date]) -> str:
    """Determine participation category (Junior/Senior) based on date of birth."""
    if not dob:
        return "Unknown"
    
    if JUNIOR_DOB_START <= dob <= JUNIOR_DOB_END:
        return "Junior"
    elif SENIOR_DOB_START <= dob <= SENIOR_DOB_END:
        return "Senior"
    else:
        return "Ineligible"


def calculate_age(dob: Optional[date]) -> Optional[int]:
    """Calculate age from date of birth."""
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# District Members
@router.get("/district-members", response_model=dict)
async def list_district_members(
    unit_id: Optional[int] = Query(None, description="Filter by specific unit ID"),
    participation_category: Optional[str] = Query(
        None, 
        description="Filter by participation category: 'Junior', 'Senior', or 'Ineligible'"
    ),
    search: Optional[str] = Query(None, description="Search by member name"),
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all unit members within the logged-in district official's district.
    
    Returns:
    - id: Unit member ID
    - name: Full name
    - phone_number: Contact number
    - dob: Date of birth
    - age: Calculated age
    - gender: Gender (M/F)
    - unit_id: Unit ID
    - unit_name: Name of the unit
    - participation_category: Junior, Senior, or Ineligible (based on DOB ranges)
    - is_excluded: Whether the member is excluded from Kalamela
    
    Filters:
    - unit_id: Filter by specific unit
    - participation_category: Filter by Junior/Senior/Ineligible
    - search: Search by member name (case-insensitive)
    """
    # Base query - get all members from units in this district
    stmt = select(UnitMembers).join(
        CustomUser, UnitMembers.registered_user_id == CustomUser.id
    ).join(
        UnitName, CustomUser.unit_name_id == UnitName.id
    ).where(
        UnitName.clergy_district_id == current_user.clergy_district_id
    ).options(
        selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name)
    )
    
    # Filter by unit if provided
    if unit_id:
        stmt = stmt.where(CustomUser.unit_name_id == unit_id)
    
    # Filter by search term
    if search:
        stmt = stmt.where(UnitMembers.name.ilike(f"%{search}%"))
    
    stmt = stmt.order_by(UnitName.name, UnitMembers.name)
    
    result = await db.execute(stmt)
    members = list(result.scalars().all())
    
    # Get excluded member IDs
    stmt_excluded = select(KalamelaExcludeMembers.members_id)
    result_excluded = await db.execute(stmt_excluded)
    excluded_ids = set(row[0] for row in result_excluded.all())
    
    # Build response with calculated fields
    members_list = []
    for member in members:
        category = get_participation_category(member.dob)
        
        # Apply participation category filter if provided
        if participation_category and category.lower() != participation_category.lower():
            continue
        
        age = calculate_age(member.dob)
        unit_name = member.registered_user.unit_name.name if member.registered_user and member.registered_user.unit_name else None
        unit_id_val = member.registered_user.unit_name_id if member.registered_user else None
        
        members_list.append({
            "id": member.id,
            "name": member.name,
            "phone_number": member.number,
            "dob": member.dob.isoformat() if member.dob else None,
            "age": age,
            "gender": member.gender,
            "unit_id": unit_id_val,
            "unit_name": unit_name,
            "participation_category": category,
            "is_excluded": member.id in excluded_ids,
        })
    
    # Get units for filter dropdown
    stmt_units = select(UnitName).where(
        UnitName.clergy_district_id == current_user.clergy_district_id
    ).order_by(UnitName.name)
    result_units = await db.execute(stmt_units)
    units = list(result_units.scalars().all())
    
    # Summary counts
    junior_count = sum(1 for m in members_list if m["participation_category"] == "Junior")
    senior_count = sum(1 for m in members_list if m["participation_category"] == "Senior")
    ineligible_count = sum(1 for m in members_list if m["participation_category"] == "Ineligible")
    excluded_count = sum(1 for m in members_list if m["is_excluded"])
    
    return {
        "members": members_list,
        "total_count": len(members_list),
        "summary": {
            "junior_count": junior_count,
            "senior_count": senior_count,
            "ineligible_count": ineligible_count,
            "excluded_count": excluded_count,
        },
        "units": [{"id": u.id, "name": u.name} for u in units],
        "filters_applied": {
            "unit_id": unit_id,
            "participation_category": participation_category,
            "search": search,
        },
    }


# Home
@router.get("/home", response_model=dict)
async def official_home(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Official home page showing:
    - All individual events with participation counts and remaining slots
    - All group events with team counts
    """
    individual_events = await kalamela_service.list_all_individual_events(
        db, current_user.clergy_district_id
    )
    
    group_events = await kalamela_service.list_all_group_events(db, current_user)
    
    return {
        "individual_events": individual_events,
        "group_events": group_events,
        "district_id": current_user.clergy_district_id,
    }


# Individual Events
@router.post("/events/individual/select", response_model=dict)
async def select_individual_event(
    data: SelectEventSchema,
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Select individual event and show eligible members.
    
    Filters members by:
    - District
    - Unit (optional)
    - Gender (boys/girls from event name)
    - Age (junior/senior from event name)
    - Not excluded
    - Not already registered
    """
    # Get event
    stmt = select(IndividualEvent).where(IndividualEvent.id == data.event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get eligible members
    members = await kalamela_service.individual_event_members_data(
        db, event, current_user.clergy_district_id, data.unit_id
    )
    
    # Get units for selection
    stmt = select(UnitName).where(
        UnitName.clergy_district_id == current_user.clergy_district_id
    ).order_by(UnitName.name)
    result = await db.execute(stmt)
    units = list(result.scalars().all())
    
    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "description": event.description,
        },
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "gender": m.gender,
                "dob": m.dob,
                "number": m.number,
            }
            for m in members
        ],
        "units": [{"id": u.id, "name": u.name} for u in units],
    }


@router.post("/events/individual/add", response_model=dict)
async def add_individual_participant(
    data: IndividualParticipationCreate,
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Add participant to individual event."""
    participation = await kalamela_service.add_individual_participant(
        db, current_user, data
    )
    
    return {
        "message": "Participant added successfully",
        "participation": {
            "id": participation.id,
            "individual_event_id": participation.individual_event_id,
            "participant_id": participation.participant_id,
            "chest_number": participation.chest_number,
            "seniority_category": participation.seniority_category.value if participation.seniority_category else None,
        },
    }


@router.get("/participants/individual", response_model=dict)
async def view_district_individual_participants(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """View all individual participants from this district grouped by event."""
    participation_dict = await kalamela_service.view_all_individual_participants(
        db, current_user.clergy_district_id
    )
    
    return {
        "individual_event_participations": participation_dict,
    }


@router.delete("/participants/individual/{participation_id}", response_model=dict)
async def remove_individual_participation(
    participation_id: int,
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Remove individual participant."""
    # Verify participation belongs to this district
    stmt = select(IndividualEventParticipation).where(
        IndividualEventParticipation.id == participation_id
    )
    result = await db.execute(stmt)
    participation = result.scalar_one_or_none()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )
    
    if participation.added_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove participants added by you"
        )
    
    await kalamela_service.remove_individual_participant(db, participation_id)
    
    return {"message": "Participant removed successfully"}


# Group Events
@router.post("/events/group/select", response_model=dict)
async def select_group_event(
    data: SelectEventSchema,
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Select group event and unit, show eligible members.
    """
    # Get event
    stmt = select(GroupEvent).where(GroupEvent.id == data.event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get eligible members
    members = await kalamela_service.group_event_members_data(
        db, event, current_user.clergy_district_id, data.unit_id
    )
    
    # Get units for selection
    stmt = select(UnitName).where(
        UnitName.clergy_district_id == current_user.clergy_district_id
    ).order_by(UnitName.name)
    result = await db.execute(stmt)
    units = list(result.scalars().all())
    
    # Check how many already registered from this unit if unit selected
    current_team_size = 0
    if data.unit_id:
        stmt = select(func.count()).select_from(GroupEventParticipation).join(
            UnitMembers, GroupEventParticipation.participant_id == UnitMembers.id
        ).where(
            and_(
                GroupEventParticipation.group_event_id == event.id,
                UnitMembers.registered_user.has(unit_name_id=data.unit_id)
            )
        )
        result = await db.execute(stmt)
        current_team_size = result.scalar() or 0
    
    remaining_slots = event.max_allowed_limit - current_team_size
    
    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "max_allowed_limit": event.max_allowed_limit,
            "min_allowed_limit": event.min_allowed_limit,
            "per_unit_allowed_limit": event.per_unit_allowed_limit,
        },
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "gender": m.gender,
                "dob": m.dob,
                "number": m.number,
            }
            for m in members
        ],
        "units": [{"id": u.id, "name": u.name} for u in units],
        "current_team_size": current_team_size,
        "remaining_slots": remaining_slots,
        "max_allowed_limit": event.max_allowed_limit,
    }


@router.post("/events/group/add", response_model=dict)
async def add_group_participants(
    data: GroupParticipationCreate,
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Add multiple participants to group event (team formation)."""
    participations = await kalamela_service.add_group_participants(
        db, current_user, data
    )
    
    return {
        "message": f"Added {len(participations)} participants successfully",
        "participations": [
            {
                "id": p.id,
                "group_event_id": p.group_event_id,
                "participant_id": p.participant_id,
                "chest_number": p.chest_number,
            }
            for p in participations
        ],
    }


@router.get("/participants/group", response_model=dict)
async def view_district_group_participants(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """View all group participants from this district grouped by event and team."""
    participation_dict = await kalamela_service.view_all_group_participants(
        db, current_user.clergy_district_id
    )
    
    return {
        "group_event_participations": participation_dict,
    }


@router.delete("/participants/group/{participation_id}", response_model=dict)
async def remove_group_participation(
    participation_id: int,
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Remove group participant."""
    # Verify participation belongs to this district
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
    
    if participation.added_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove participants added by you"
        )
    
    await kalamela_service.remove_group_participant(db, participation_id)
    
    return {"message": "Participant removed successfully"}


# Preview & Payment
@router.get("/preview", response_model=dict)
async def preview_district_participation(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Preview all district participations with:
    - Individual events count
    - Group events count (distinct teams)
    - Calculated amount
    - Payment status
    """
    stats = await kalamela_service.get_district_statistics(
        db, current_user.clergy_district_id
    )
    
    individual_participations = await kalamela_service.view_all_individual_participants(
        db, current_user.clergy_district_id
    )
    
    group_participations = await kalamela_service.view_all_group_participants(
        db, current_user.clergy_district_id
    )
    
    return {
        **stats,
        "individual_event_participations": individual_participations,
        "group_event_participations": group_participations,
    }


@router.post("/payment", response_model=KalamelaPaymentResponse)
async def create_payment(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create payment record based on current participations.
    Automatically calculates counts.
    """
    stats = await kalamela_service.get_district_statistics(
        db, current_user.clergy_district_id
    )
    
    data = KalamelaPaymentCreate(
        individual_events_count=stats["individual_events_count"],
        group_events_count=stats["group_events_count"],
    )
    
    payment = await kalamela_service.create_kalamela_payment(db, current_user, data)
    
    return payment


@router.post("/payment/{payment_id}/proof", response_model=KalamelaPaymentResponse)
async def upload_payment_proof_endpoint(
    payment_id: int,
    file: UploadFile = File(...),
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Upload payment proof."""
    # Verify payment belongs to this user
    stmt = select(KalamelaPayments).where(KalamelaPayments.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.paid_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload proof for your own payment"
        )
    
    payment = await kalamela_service.upload_payment_proof(db, payment_id, file)
    
    return payment


# Print
@router.get("/print", response_model=dict)
async def print_district_participation(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Formatted view for printing district participation.
    Similar to preview but optimized for print.
    """
    stats = await kalamela_service.get_district_statistics(
        db, current_user.clergy_district_id
    )
    
    individual_participations = await kalamela_service.view_all_individual_participants(
        db, current_user.clergy_district_id
    )
    
    group_participations = await kalamela_service.view_all_group_participants(
        db, current_user.clergy_district_id
    )
    
    # Get district name
    stmt = select(CustomUser).where(CustomUser.id == current_user.id).options(
        selectinload(CustomUser.clergy_district)
    )
    result = await db.execute(stmt)
    user_with_district = result.scalar_one()
    
    return {
        "district_name": user_with_district.clergy_district.name,
        **stats,
        "individual_event_participations": individual_participations,
        "group_event_participations": group_participations,
    }
