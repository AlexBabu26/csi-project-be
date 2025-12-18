"""Kalamela admin router - comprehensive administrative endpoints."""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_db
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


# Dashboard
@router.get("/home", response_model=dict)
async def admin_home(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin dashboard with all events."""
    stmt_ind = select(IndividualEvent).order_by(IndividualEvent.name)
    result_ind = await db.execute(stmt_ind)
    individual_events = list(result_ind.scalars().all())
    
    stmt_grp = select(GroupEvent).order_by(GroupEvent.name)
    result_grp = await db.execute(stmt_grp)
    group_events = list(result_grp.scalars().all())
    
    return {
        "individual_events": individual_events,
        "group_events": group_events,
    }


# Unit/Member Management
@router.get("/units", response_model=List[dict])
async def list_all_units(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Exclude a member from all events."""
    await kalamela_service.exclude_member(db, member_id)
    return {"message": "Member excluded from all events"}


@router.get("/excluded-members", response_model=List[dict])
async def list_excluded_members(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Remove member from exclusion list."""
    await kalamela_service.remove_exclusion(db, exclusion_id)
    return {"message": "Member removed from exclusion list"}


# Event Management
@router.post("/events/individual", response_model=IndividualEventResponse)
async def create_individual_event(
    data: IndividualEventCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create individual event."""
    event = IndividualEvent(
        name=data.name,
        category=data.category,
        description=data.description,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return event


@router.put("/events/individual/{event_id}", response_model=IndividualEventResponse)
async def update_individual_event(
    event_id: int,
    data: IndividualEventUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    if data.category is not None:
        event.category = data.category
    if data.description is not None:
        event.description = data.description
    
    await db.commit()
    await db.refresh(event)
    
    return event


@router.post("/events/group", response_model=GroupEventResponse)
async def create_group_event(
    data: GroupEventCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create group event."""
    event = GroupEvent(
        name=data.name,
        description=data.description,
        max_allowed_limit=data.max_allowed_limit,
        min_allowed_limit=data.min_allowed_limit,
        per_unit_allowed_limit=data.per_unit_allowed_limit,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return event


@router.put("/events/group/{event_id}", response_model=GroupEventResponse)
async def update_group_event(
    event_id: int,
    data: GroupEventUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    if data.max_allowed_limit is not None:
        event.max_allowed_limit = data.max_allowed_limit
    if data.min_allowed_limit is not None:
        event.min_allowed_limit = data.min_allowed_limit
    if data.per_unit_allowed_limit is not None:
        event.per_unit_allowed_limit = data.per_unit_allowed_limit
    
    await db.commit()
    await db.refresh(event)
    
    return event


# Participant Management
@router.get("/participants/individual", response_model=dict)
async def list_individual_participants(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all individual participants grouped by event."""
    return await kalamela_service.view_all_individual_participants(db)


@router.get("/participants/group", response_model=dict)
async def list_group_participants(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all group participants grouped by event and team."""
    return await kalamela_service.view_all_group_participants(db)


@router.put("/participants/group/{participation_id}/chest-number", response_model=dict)
async def update_chest_number(
    participation_id: int,
    data: ChestNumberUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """
    View events preview with participation counts and payment info.
    Can filter by district.
    """
    # Get all districts
    stmt = select(ClergyDistrict)
    result = await db.execute(stmt)
    districts = list(result.scalars().all())
    
    # Get all events
    stmt = select(IndividualEvent)
    result = await db.execute(stmt)
    individual_events = list(result.scalars().all())
    
    stmt = select(GroupEvent)
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
    
    individual_amount = individual_count * 50
    group_amount = group_count * 100
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
    
    return {
        "clergy_districts": [{"id": d.id, "name": d.name} for d in districts],
        "individual_events": individual_events,
        "group_events": group_events,
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
    db: AsyncSession = Depends(get_db),
):
    """List all payments."""
    stmt = select(KalamelaPayments).order_by(KalamelaPayments.created_on.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/payments/{payment_id}/approve", response_model=dict)
async def approve_payment(
    payment_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve payment."""
    await kalamela_service.update_payment_status(db, payment_id, PaymentStatus.PAID)
    return {"message": "Payment approved successfully"}


@router.post("/payments/{payment_id}/decline", response_model=dict)
async def decline_payment(
    payment_id: int,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
@router.post("/events/individual/candidates", response_model=List[dict])
async def get_individual_candidates(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Bulk add individual scores."""
    scores = await kalamela_service.add_individual_scores_bulk(db, data)
    return {"message": f"Added {len(scores)} scores successfully"}


@router.post("/events/group/candidates", response_model=List[dict])
async def get_group_candidates(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Bulk add group scores."""
    scores = await kalamela_service.add_group_scores_bulk(db, data)
    return {"message": f"Added {len(scores)} scores successfully"}


@router.get("/scores/individual", response_model=dict)
async def view_individual_scores(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
            results_dict[event_name] = scores
    
    return {"results_dict": results_dict}


@router.get("/scores/group", response_model=dict)
async def view_group_scores(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
            results_dict[event_name] = scores
    
    return {"results_dict": results_dict}


@router.post("/scores/individual/update", response_model=dict)
async def update_individual_scores(
    data: IndividualScoreBulkUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update individual scores."""
    scores = await kalamela_service.update_individual_scores_bulk(db, data)
    return {"message": f"Updated {len(scores)} scores successfully"}


@router.post("/scores/group/update", response_model=dict)
async def update_group_scores(
    data: GroupScoreBulkUpdate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update group scores."""
    scores = await kalamela_service.update_group_scores_bulk(db, data)
    return {"message": f"Updated {len(scores)} scores successfully"}


@router.post("/scores/individual/event", response_model=dict)
async def get_scores_for_event(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
        "event_scores": scores,
    }


@router.post("/scores/group/event", response_model=dict)
async def get_group_scores_for_event(
    event_name: str,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all scores for a specific group event for editing."""
    stmt = select(GroupEventScoreCard).where(
        GroupEventScoreCard.event_name == event_name
    ).order_by(GroupEventScoreCard.total_points.desc())
    result = await db.execute(stmt)
    scores = list(result.scalars().all())
    
    return {
        "event_name": event_name,
        "event_scores": scores,
    }


# Appeals
@router.get("/appeals", response_model=List[dict])
async def list_all_appeals(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Reply to appeal and approve it."""
    appeal = await kalamela_service.reply_to_appeal(db, appeal_id, data.reply)
    return {"message": "Appeal replied and approved successfully"}


# Results
@router.get("/results/unit-wise", response_model=dict)
async def get_unit_wise_results(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
                "unit_results": scores
            }]
    
    return {"results_dict": results_dict}


@router.get("/results/district-wise", response_model=dict)
async def get_district_wise_results(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
                "district_results": scores,
                "total_points": total_points,
            }]
    
    return {"results_dict": results_dict}


# Excel Exports
@router.post("/export/events")
async def export_events_data(
    filters: EventFilterSchema,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
