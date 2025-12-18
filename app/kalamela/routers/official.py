"""Kalamela official router - district official functionalities."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_db
from app.common.security import get_current_user
from app.auth.models import CustomUser, UnitMembers, UnitName, UserType
from app.kalamela.models import (
    IndividualEvent,
    GroupEvent,
    IndividualEventParticipation,
    GroupEventParticipation,
    KalamelaPayments,
)
from app.kalamela.schemas import (
    IndividualParticipationCreate,
    GroupParticipationCreate,
    SelectEventSchema,
    KalamelaPaymentCreate,
    KalamelaPaymentResponse,
)
from app.kalamela import service as kalamela_service

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


# Home
@router.get("/home", response_model=dict)
async def official_home(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        "event": event,
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
    db: AsyncSession = Depends(get_db),
):
    """Add participant to individual event."""
    participation = await kalamela_service.add_individual_participant(
        db, current_user, data
    )
    
    return {
        "message": "Participant added successfully",
        "participation": participation,
    }


@router.get("/participants/individual", response_model=dict)
async def view_district_individual_participants(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        "event": event,
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
    db: AsyncSession = Depends(get_db),
):
    """Add multiple participants to group event (team formation)."""
    participations = await kalamela_service.add_group_participants(
        db, current_user, data
    )
    
    return {
        "message": f"Added {len(participations)} participants successfully",
        "participations": participations,
    }


@router.get("/participants/group", response_model=dict)
async def view_district_group_participants(
    current_user: CustomUser = Depends(get_official_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
