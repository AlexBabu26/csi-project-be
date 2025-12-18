"""Kalamela service layer - complete business logic implementation."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
import re

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status, UploadFile

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
    SeniorityCategory,
    PaymentStatus,
    AppealStatus,
)
from app.kalamela import schemas as kala_schema
from app.common.storage import save_upload_file


# Constants
INDIVIDUAL_FEE = 50
GROUP_FEE = 100
APPEAL_FEE = 1000

# Age range definitions
JUNIOR_DOB_START = date(2004, 1, 12)
JUNIOR_DOB_END = date(2010, 6, 30)
SENIOR_DOB_START = date(1989, 7, 1)
SENIOR_DOB_END = date(2004, 1, 11)


# Event Management Functions
async def list_all_individual_events(
    db: AsyncSession,
    district_id: int,
) -> Dict[str, List[Dict]]:
    """
    List all individual events with participation counts and remaining slots.
    
    Returns dict grouped by category.
    """
    stmt = select(IndividualEvent).order_by(IndividualEvent.category, IndividualEvent.name)
    result = await db.execute(stmt)
    events = list(result.scalars().all())
    
    event_dict = {}
    
    for event in events:
        # Count participations from this district
        stmt_count = select(func.count()).select_from(IndividualEventParticipation).join(
            CustomUser, IndividualEventParticipation.added_by_id == CustomUser.id
        ).where(
            and_(
                IndividualEventParticipation.individual_event_id == event.id,
                CustomUser.clergy_district_id == district_id
            )
        )
        result_count = await db.execute(stmt_count)
        count = result_count.scalar() or 0
        
        remaining_slots = max(0, 2 - count)
        
        category = event.category or "Uncategorized"
        if category not in event_dict:
            event_dict[category] = []
        
        event_dict[category].append({
            "event": event,
            "participation_count": count,
            "remaining_slots": remaining_slots,
        })
    
    return event_dict


async def list_all_group_events(
    db: AsyncSession,
    user: CustomUser,
) -> Dict[GroupEvent, List[Dict]]:
    """List all group events with team counts per district/unit."""
    stmt = select(GroupEvent).order_by(GroupEvent.name)
    result = await db.execute(stmt)
    events = list(result.scalars().all())
    
    group_events_dict = {}
    
    for event in events:
        # Count distinct units participating
        stmt_count = select(func.count(func.distinct(UnitMembers.registered_user_id))).select_from(
            GroupEventParticipation
        ).join(
            UnitMembers, GroupEventParticipation.participant_id == UnitMembers.id
        ).where(
            and_(
                GroupEventParticipation.group_event_id == event.id,
                GroupEventParticipation.added_by_id == user.id
            )
        )
        result_count = await db.execute(stmt_count)
        count = result_count.scalar() or 0
        
        group_events_dict[event] = [{
            "id": event.id,
            "name": event.name,
            "count": count,
        }]
    
    return group_events_dict


async def individual_event_members_data(
    db: AsyncSession,
    event: IndividualEvent,
    district_id: int,
    unit_id: Optional[int] = None,
) -> List[UnitMembers]:
    """
    Get eligible members for an individual event.
    
    Filters by:
    - District
    - Unit (optional)
    - Gender (from event name: boys/girls)
    - Age/DOB (from event name: junior/senior)
    - Not excluded
    - Not already registered for this event
    """
    # Get excluded members
    stmt_excluded = select(KalamelaExcludeMembers.members_id)
    result_excluded = await db.execute(stmt_excluded)
    excluded_ids = [row[0] for row in result_excluded.all()]
    
    # Get already registered members for this event from this district
    stmt_registered = select(IndividualEventParticipation.participant_id).join(
        CustomUser, IndividualEventParticipation.added_by_id == CustomUser.id
    ).where(
        and_(
            IndividualEventParticipation.individual_event_id == event.id,
            CustomUser.clergy_district_id == district_id
        )
    )
    result_registered = await db.execute(stmt_registered)
    registered_ids = [row[0] for row in result_registered.all()]
    
    # Base query
    stmt = select(UnitMembers).join(
        CustomUser, UnitMembers.registered_user_id == CustomUser.id
    ).join(
        UnitName, CustomUser.unit_name_id == UnitName.id
    ).where(
        UnitName.clergy_district_id == district_id
    )
    
    # Filter by unit if provided
    if unit_id:
        stmt = stmt.where(CustomUser.unit_name_id == unit_id)
    
    # Exclude already registered and excluded members
    if registered_ids:
        stmt = stmt.where(UnitMembers.id.notin_(registered_ids))
    if excluded_ids:
        stmt = stmt.where(UnitMembers.id.notin_(excluded_ids))
    
    # Gender filtering
    event_name_lower = event.name.lower()
    if "boys" in event_name_lower:
        stmt = stmt.where(UnitMembers.gender == "M")
    elif "girls" in event_name_lower:
        stmt = stmt.where(UnitMembers.gender == "F")
    
    # Age filtering
    if "junior" in event_name_lower:
        stmt = stmt.where(
            and_(
                UnitMembers.dob >= JUNIOR_DOB_START,
                UnitMembers.dob <= JUNIOR_DOB_END
            )
        )
    elif "senior" in event_name_lower:
        stmt = stmt.where(
            and_(
                UnitMembers.dob >= SENIOR_DOB_START,
                UnitMembers.dob <= SENIOR_DOB_END
            )
        )
    
    stmt = stmt.order_by(UnitMembers.name)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def group_event_members_data(
    db: AsyncSession,
    event: GroupEvent,
    district_id: int,
    unit_id: Optional[int] = None,
) -> List[UnitMembers]:
    """Get eligible members for a group event."""
    # Get excluded members
    stmt_excluded = select(KalamelaExcludeMembers.members_id)
    result_excluded = await db.execute(stmt_excluded)
    excluded_ids = [row[0] for row in result_excluded.all()]
    
    # Get already registered members
    stmt_registered = select(GroupEventParticipation.participant_id).join(
        CustomUser, GroupEventParticipation.added_by_id == CustomUser.id
    ).where(
        and_(
            GroupEventParticipation.group_event_id == event.id,
            CustomUser.clergy_district_id == district_id
        )
    )
    result_registered = await db.execute(stmt_registered)
    registered_ids = [row[0] for row in result_registered.all()]
    
    # Base query
    stmt = select(UnitMembers).join(
        CustomUser, UnitMembers.registered_user_id == CustomUser.id
    ).join(
        UnitName, CustomUser.unit_name_id == UnitName.id
    ).where(
        UnitName.clergy_district_id == district_id
    )
    
    if unit_id:
        stmt = stmt.where(CustomUser.unit_name_id == unit_id)
    
    if registered_ids:
        stmt = stmt.where(UnitMembers.id.notin_(registered_ids))
    if excluded_ids:
        stmt = stmt.where(UnitMembers.id.notin_(excluded_ids))
    
    stmt = stmt.order_by(UnitMembers.name)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def generate_individual_chest_number(
    db: AsyncSession,
    event_id: int,
    participant: UnitMembers,
    seniority_category: SeniorityCategory,
) -> str:
    """
    Generate chest number for individual event participant.
    
    Logic:
    - Check if participant already has a chest number (from another event)
    - If not, generate based on seniority: 100-199 for junior, 200-299 for senior
    - Increment from last chest number
    """
    # Check if participant already has a chest number
    stmt = select(IndividualEventParticipation.chest_number).where(
        IndividualEventParticipation.participant_id == participant.id
    ).order_by(IndividualEventParticipation.created_on)
    result = await db.execute(stmt)
    existing_chest = result.scalar_one_or_none()
    
    if existing_chest:
        return existing_chest
    
    # Generate new chest number
    if seniority_category == SeniorityCategory.JUNIOR:
        base_number = 100
    elif seniority_category == SeniorityCategory.SENIOR:
        base_number = 200
    else:
        base_number = 100
    
    # Get last chest number
    stmt = select(IndividualEventParticipation.chest_number).order_by(
        IndividualEventParticipation.chest_number.desc()
    )
    result = await db.execute(stmt)
    last_chest = result.scalar_one_or_none()
    
    if last_chest:
        try:
            last_number = int(last_chest)
            return str(last_number + 1)
        except ValueError:
            return str(base_number)
    
    return str(base_number)


async def generate_group_chest_number(
    db: AsyncSession,
    event: GroupEvent,
    unit_id: int,
) -> str:
    """
    Generate chest number for group event.
    
    Format: EventAbbrev-TeamNumber (e.g., "CDAS-1", "CDAS-2")
    """
    # Create event abbreviation (first letter of each word)
    event_name = re.sub(r"[()]", "", event.name)
    abbreviation = "".join([word[0].upper() for word in event_name.split()[:2]])
    
    # Check if team from this unit already exists
    stmt = select(GroupEventParticipation.chest_number).join(
        UnitMembers, GroupEventParticipation.participant_id == UnitMembers.id
    ).where(
        and_(
            GroupEventParticipation.group_event_id == event.id,
            UnitMembers.registered_user_id.in_(
                select(CustomUser.id).where(CustomUser.unit_name_id == unit_id)
            )
        )
    ).order_by(GroupEventParticipation.created_on.desc())
    result = await db.execute(stmt)
    existing_chest = result.scalar_one_or_none()
    
    if existing_chest:
        return existing_chest
    
    # Get last team number for this event
    stmt = select(GroupEventParticipation.chest_number).where(
        GroupEventParticipation.group_event_id == event.id
    ).order_by(GroupEventParticipation.created_on.desc())
    result = await db.execute(stmt)
    last_chest = result.scalar_one_or_none()
    
    team_number = 1
    if last_chest and "-" in last_chest:
        try:
            team_number = int(last_chest.split("-")[1]) + 1
        except (ValueError, IndexError):
            team_number = 1
    
    return f"{abbreviation}-{team_number}"


# Participation Management
async def add_individual_participant(
    db: AsyncSession,
    user: CustomUser,
    data: kala_schema.IndividualParticipationCreate,
) -> IndividualEventParticipation:
    """
    Add individual participant with validation.
    
    Validates:
    - Max 5 events per person
    - Max 2 per district per event per seniority
    - Not excluded
    - Not already registered
    """
    # Get member
    stmt = select(UnitMembers).where(UnitMembers.id == data.participant_id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    # Check if excluded
    stmt = select(KalamelaExcludeMembers).where(
        KalamelaExcludeMembers.members_id == member.id
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant is excluded from events"
        )
    
    # Check participant event count (max 5)
    stmt = select(func.count()).select_from(IndividualEventParticipation).where(
        IndividualEventParticipation.participant_id == member.id
    )
    result = await db.execute(stmt)
    event_count = result.scalar() or 0
    
    if event_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant already registered for 5 individual events"
        )
    
    # Check district quota (max 2 per event per seniority)
    stmt = select(func.count()).select_from(IndividualEventParticipation).join(
        CustomUser, IndividualEventParticipation.added_by_id == CustomUser.id
    ).where(
        and_(
            IndividualEventParticipation.individual_event_id == data.individual_event_id,
            IndividualEventParticipation.seniority_category == data.seniority_category,
            CustomUser.clergy_district_id == user.clergy_district_id
        )
    )
    result = await db.execute(stmt)
    district_count = result.scalar() or 0
    
    if district_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="District quota reached for this event and seniority"
        )
    
    # Check if already registered
    stmt = select(IndividualEventParticipation).where(
        and_(
            IndividualEventParticipation.individual_event_id == data.individual_event_id,
            IndividualEventParticipation.participant_id == member.id
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant already registered for this event"
        )
    
    # Get event
    stmt = select(IndividualEvent).where(IndividualEvent.id == data.individual_event_id)
    result = await db.execute(stmt)
    event = result.scalar_one()
    
    # Generate chest number
    chest_number = await generate_individual_chest_number(
        db, event.id, member, data.seniority_category
    )
    
    # Create participation
    participation = IndividualEventParticipation(
        individual_event_id=data.individual_event_id,
        participant_id=member.id,
        added_by_id=user.id,
        chest_number=chest_number,
        seniority_category=data.seniority_category,
    )
    
    db.add(participation)
    await db.commit()
    await db.refresh(participation)
    
    return participation


async def add_group_participants(
    db: AsyncSession,
    user: CustomUser,
    data: kala_schema.GroupParticipationCreate,
) -> List[GroupEventParticipation]:
    """
    Add multiple group participants with validation.
    
    Validates:
    - Team limits
    - Max 2 teams per district per event
    - Per-unit limits
    - Same-unit team detection
    """
    # Get event
    stmt = select(GroupEvent).where(GroupEvent.id == data.group_event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check all members exist and are from same unit
    stmt = select(UnitMembers).where(UnitMembers.id.in_(data.participant_ids)).options(
        selectinload(UnitMembers.registered_user)
    )
    result = await db.execute(stmt)
    members = list(result.scalars().all())
    
    if len(members) != len(data.participant_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some participants not found"
        )
    
    # Check if all from same unit
    unit_ids = set(m.registered_user.unit_name_id for m in members)
    if len(unit_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All participants must be from the same unit"
        )
    
    unit_id = unit_ids.pop()
    
    # Check if any excluded
    stmt = select(KalamelaExcludeMembers.members_id).where(
        KalamelaExcludeMembers.members_id.in_(data.participant_ids)
    )
    result = await db.execute(stmt)
    excluded_ids = [row[0] for row in result.all()]
    
    if excluded_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some participants are excluded from events"
        )
    
    # Check district team count (max 2 teams per event)
    stmt = select(func.count(func.distinct(GroupEventParticipation.chest_number))).select_from(
        GroupEventParticipation
    ).join(
        CustomUser, GroupEventParticipation.added_by_id == CustomUser.id
    ).where(
        and_(
            GroupEventParticipation.group_event_id == event.id,
            CustomUser.clergy_district_id == user.clergy_district_id
        )
    )
    result = await db.execute(stmt)
    team_count = result.scalar() or 0
    
    # Check if adding to existing team or new team
    stmt = select(GroupEventParticipation.chest_number).join(
        UnitMembers, GroupEventParticipation.participant_id == UnitMembers.id
    ).where(
        and_(
            GroupEventParticipation.group_event_id == event.id,
            UnitMembers.registered_user_id.in_(
                select(CustomUser.id).where(CustomUser.unit_name_id == unit_id)
            )
        )
    )
    result = await db.execute(stmt)
    existing_chest = result.scalar_one_or_none()
    
    if not existing_chest and team_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="District quota reached (max 2 teams per event)"
        )
    
    # Check if any already registered
    stmt = select(GroupEventParticipation.participant_id).where(
        and_(
            GroupEventParticipation.group_event_id == event.id,
            GroupEventParticipation.participant_id.in_(data.participant_ids)
        )
    )
    result = await db.execute(stmt)
    already_registered = [row[0] for row in result.all()]
    
    if already_registered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some participants already registered for this event"
        )
    
    # Generate or use existing chest number
    if existing_chest:
        chest_number = existing_chest
        
        # Check team size limit
        stmt = select(func.count()).select_from(GroupEventParticipation).where(
            and_(
                GroupEventParticipation.group_event_id == event.id,
                GroupEventParticipation.chest_number == chest_number
            )
        )
        result = await db.execute(stmt)
        current_team_size = result.scalar() or 0
        
        if current_team_size + len(data.participant_ids) > event.max_allowed_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team size limit exceeded (max {event.max_allowed_limit})"
            )
    else:
        chest_number = await generate_group_chest_number(db, event, unit_id)
        
        if len(data.participant_ids) > event.max_allowed_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team size exceeds limit (max {event.max_allowed_limit})"
            )
    
    # Create participations
    participations = []
    for participant_id in data.participant_ids:
        participation = GroupEventParticipation(
            group_event_id=event.id,
            participant_id=participant_id,
            chest_number=chest_number,
            added_by_id=user.id,
        )
        db.add(participation)
        participations.append(participation)
    
    await db.commit()
    
    return participations


async def remove_individual_participant(
    db: AsyncSession,
    participation_id: int,
) -> bool:
    """Remove individual participant."""
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
    
    await db.delete(participation)
    await db.commit()
    
    return True


async def remove_group_participant(
    db: AsyncSession,
    participation_id: int,
) -> bool:
    """Remove group participant."""
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
    
    await db.delete(participation)
    await db.commit()
    
    return True


# Scoring Functions
async def add_individual_scores_bulk(
    db: AsyncSession,
    data: kala_schema.IndividualScoreBulkCreate,
) -> List[IndividualEventScoreCard]:
    """Bulk add individual scores."""
    scores = []
    
    for score_data in data.participants:
        # Verify participation exists
        stmt = select(IndividualEventParticipation).where(
            IndividualEventParticipation.id == score_data.event_participation_id
        )
        result = await db.execute(stmt)
        participation = result.scalar_one_or_none()
        
        if not participation:
            continue
        
        score = IndividualEventScoreCard(
            event_participation_id=score_data.event_participation_id,
            participant_id=participation.participant_id,
            awarded_mark=score_data.awarded_mark,
            grade=score_data.grade,
            total_points=score_data.total_points,
        )
        db.add(score)
        scores.append(score)
    
    await db.commit()
    return scores


async def add_group_scores_bulk(
    db: AsyncSession,
    data: kala_schema.GroupScoreBulkCreate,
) -> List[GroupEventScoreCard]:
    """Bulk add group scores."""
    scores = []
    
    for score_data in data.participants:
        score = GroupEventScoreCard(
            event_name=score_data.event_name,
            chest_number=score_data.chest_number,
            awarded_mark=score_data.awarded_mark,
            grade=score_data.grade,
            total_points=score_data.total_points,
        )
        db.add(score)
        scores.append(score)
    
    await db.commit()
    return scores


async def update_individual_scores_bulk(
    db: AsyncSession,
    data: kala_schema.IndividualScoreBulkUpdate,
) -> List[IndividualEventScoreCard]:
    """Bulk update individual scores (for appeals)."""
    scores = []
    
    for score_data in data.participants:
        stmt = select(IndividualEventScoreCard).where(
            IndividualEventScoreCard.event_participation_id == score_data.event_participation_id
        )
        result = await db.execute(stmt)
        score = result.scalar_one_or_none()
        
        if score:
            score.awarded_mark = score_data.awarded_mark
            score.grade = score_data.grade
            score.total_points = score_data.total_points
            scores.append(score)
    
    await db.commit()
    return scores


async def update_group_scores_bulk(
    db: AsyncSession,
    data: kala_schema.GroupScoreBulkUpdate,
) -> List[GroupEventScoreCard]:
    """Bulk update group scores."""
    scores = []
    
    for score_data in data.participants:
        stmt = select(GroupEventScoreCard).where(
            GroupEventScoreCard.chest_number == score_data.chest_number
        )
        result = await db.execute(stmt)
        score = result.scalar_one_or_none()
        
        if score:
            score.awarded_mark = score_data.awarded_mark
            score.grade = score_data.grade
            score.total_points = score_data.total_points
            scores.append(score)
    
    await db.commit()
    return scores


# Payment Functions
async def create_kalamela_payment(
    db: AsyncSession,
    user: CustomUser,
    data: kala_schema.KalamelaPaymentCreate,
) -> KalamelaPayments:
    """Create payment record."""
    total_amount = (data.individual_events_count * INDIVIDUAL_FEE + 
                   data.group_events_count * GROUP_FEE)
    
    payment = KalamelaPayments(
        paid_by_id=user.id,
        individual_events_count=data.individual_events_count,
        group_events_count=data.group_events_count,
        total_amount_to_pay=total_amount,
        payment_status=PaymentStatus.PENDING,
    )
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    return payment


async def upload_payment_proof(
    db: AsyncSession,
    payment_id: int,
    file: UploadFile,
) -> KalamelaPayments:
    """Upload payment proof."""
    stmt = select(KalamelaPayments).where(KalamelaPayments.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Save file
    _, file_path = save_upload_file(file, subdir="kalamela/payments")
    
    payment.payment_proof_path = str(file_path)
    payment.payment_status = PaymentStatus.PROOF_UPLOADED
    
    await db.commit()
    await db.refresh(payment)
    
    return payment


async def update_payment_status(
    db: AsyncSession,
    payment_id: int,
    new_status: PaymentStatus,
) -> KalamelaPayments:
    """Update payment status (approve/decline)."""
    stmt = select(KalamelaPayments).where(KalamelaPayments.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment.payment_status = new_status
    
    await db.commit()
    await db.refresh(payment)
    
    return payment


# Appeal Functions
async def create_appeal(
    db: AsyncSession,
    data: kala_schema.AppealCreate,
) -> Appeal:
    """
    Create appeal with 30-minute window validation.
    """
    # Get participant
    stmt = select(UnitMembers).where(UnitMembers.id == data.participant_id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    # Find score and check 30-minute window
    now = datetime.utcnow()
    score_time = None
    
    # Check individual scores
    stmt = select(IndividualEventScoreCard).join(
        IndividualEventParticipation,
        IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
    ).where(
        IndividualEventParticipation.chest_number == data.chest_number
    ).order_by(IndividualEventScoreCard.added_on.desc())
    result = await db.execute(stmt)
    ind_score = result.scalar_one_or_none()
    
    if ind_score:
        score_time = ind_score.added_on
    
    # Check group scores
    if not score_time:
        stmt = select(GroupEventScoreCard).where(
            GroupEventScoreCard.chest_number == data.chest_number
        ).order_by(GroupEventScoreCard.added_on.desc())
        result = await db.execute(stmt)
        grp_score = result.scalar_one_or_none()
        
        if grp_score:
            score_time = grp_score.added_on
    
    if not score_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No score found for this chest number"
        )
    
    # Check 30-minute window
    if now - score_time > timedelta(minutes=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal window expired (30 minutes from score publication)"
        )
    
    # Check if appeal already exists
    stmt = select(Appeal).where(
        and_(
            Appeal.chest_number == data.chest_number,
            Appeal.event_name == data.event_name
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal already exists for this event"
        )
    
    # Create appeal
    appeal = Appeal(
        added_by_id=member.id,
        chest_number=data.chest_number,
        event_name=data.event_name,
        statement=data.statement,
        status=AppealStatus.PENDING,
    )
    db.add(appeal)
    await db.flush()
    
    # Create appeal payment
    appeal_payment = AppealPayments(
        appeal_id=appeal.id,
        total_amount_to_pay=APPEAL_FEE,
        payment_type=data.payment_type,
        payment_status="Confirmation Pending",
    )
    db.add(appeal_payment)
    
    await db.commit()
    await db.refresh(appeal)
    
    return appeal


async def reply_to_appeal(
    db: AsyncSession,
    appeal_id: int,
    reply: str,
) -> Appeal:
    """Reply to appeal and approve it."""
    stmt = select(Appeal).where(Appeal.id == appeal_id)
    result = await db.execute(stmt)
    appeal = result.scalar_one_or_none()
    
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appeal not found"
        )
    
    appeal.reply = reply
    appeal.status = AppealStatus.APPROVED
    
    # Update appeal payment
    stmt = select(AppealPayments).where(AppealPayments.appeal_id == appeal_id)
    result = await db.execute(stmt)
    appeal_payment = result.scalar_one_or_none()
    
    if appeal_payment:
        appeal_payment.payment_status = "PAID"
    
    await db.commit()
    await db.refresh(appeal)
    
    return appeal


# Aggregation Functions
async def view_all_individual_participants(
    db: AsyncSession,
    district_id: Optional[int] = None,
) -> Dict[str, List[Dict]]:
    """View all individual participants grouped by event."""
    stmt = select(IndividualEventParticipation).options(
        selectinload(IndividualEventParticipation.individual_event),
        selectinload(IndividualEventParticipation.participant).selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
    ).order_by(IndividualEventParticipation.individual_event_id)
    
    if district_id:
        stmt = stmt.join(
            CustomUser, IndividualEventParticipation.added_by_id == CustomUser.id
        ).where(CustomUser.clergy_district_id == district_id)
    
    result = await db.execute(stmt)
    participations = list(result.scalars().all())
    
    participation_dict = {}
    
    for p in participations:
        event_name = p.individual_event.name
        
        if event_name not in participation_dict:
            participation_dict[event_name] = []
        
        participation_dict[event_name].append({
            "individual_event_participation_id": p.id,
            "individual_event_id": p.individual_event_id,
            "participant_id": p.participant.id,
            "participant_name": p.participant.name.title(),
            "participant_unit": p.participant.registered_user.unit_name.name.title(),
            "participant_district": p.participant.registered_user.unit_name.district.name.title(),
            "participant_phone": p.participant.number,
            "participant_chest_number": p.chest_number,
        })
    
    return participation_dict


async def view_all_group_participants(
    db: AsyncSession,
    district_id: Optional[int] = None,
) -> Dict[str, Dict[str, List[Dict]]]:
    """View all group participants grouped by event then by team."""
    stmt = select(GroupEventParticipation).options(
        selectinload(GroupEventParticipation.group_event),
        selectinload(GroupEventParticipation.participant).selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
    ).order_by(GroupEventParticipation.group_event_id, GroupEventParticipation.chest_number)
    
    if district_id:
        stmt = stmt.join(
            CustomUser, GroupEventParticipation.added_by_id == CustomUser.id
        ).where(CustomUser.clergy_district_id == district_id)
    
    result = await db.execute(stmt)
    participations = list(result.scalars().all())
    
    participation_dict = {}
    
    for p in participations:
        event_name = p.group_event.name
        team_code = p.participant.registered_user.unit_name.name.title()
        
        if event_name not in participation_dict:
            participation_dict[event_name] = {}
        
        if team_code not in participation_dict[event_name]:
            participation_dict[event_name][team_code] = []
        
        participation_dict[event_name][team_code].append({
            "group_event_participation_id": p.id,
            "group_event_id": p.group_event_id,
            "group_event_max_allowed_limit": p.group_event.max_allowed_limit,
            "participant_id": p.participant.id,
            "participant_name": p.participant.name.title(),
            "participant_unit": p.participant.registered_user.unit_name.name.title(),
            "participant_district": p.participant.registered_user.unit_name.district.name.title(),
            "participant_phone": p.participant.number,
            "participant_chest_number": p.chest_number,
            "total_count": len(participation_dict[event_name][team_code]) + 1,
        })
    
    return participation_dict


async def calculate_kalaprathibha(
    db: AsyncSession,
) -> Dict[str, Optional[Dict]]:
    """
    Calculate Kalaprathibha (male) and Kalathilakam (female).
    
    Criteria: 2+ events with 2+ points each, sum points.
    """
    # Kalaprathibha (Male)
    stmt = select(
        UnitMembers.name,
        UnitMembers.id,
        func.count(IndividualEventScoreCard.id).label('event_count'),
        func.sum(IndividualEventScoreCard.total_points).label('combined_score')
    ).join(
        IndividualEventScoreCard, UnitMembers.id == IndividualEventScoreCard.participant_id
    ).where(
        and_(
            UnitMembers.gender == 'M',
            IndividualEventScoreCard.total_points >= 2
        )
    ).group_by(UnitMembers.id, UnitMembers.name).having(
        func.count(IndividualEventScoreCard.id) >= 2
    ).order_by(func.sum(IndividualEventScoreCard.total_points).desc())
    
    result = await db.execute(stmt)
    kalaprathibha_data = result.first()
    
    kalaprathibha = None
    if kalaprathibha_data:
        stmt = select(UnitMembers).where(UnitMembers.name == kalaprathibha_data[0]).options(
            selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district)
        )
        result = await db.execute(stmt)
        member = result.scalar_one()
        
        kalaprathibha = {
            "participant_name": member.name,
            "participant_unit": member.registered_user.unit_name.name,
            "participant_district": member.registered_user.unit_name.district.name,
            "combined_score": kalaprathibha_data[3],
            "event_count": kalaprathibha_data[2],
        }
    
    # Kalathilakam (Female)
    stmt = select(
        UnitMembers.name,
        UnitMembers.id,
        func.count(IndividualEventScoreCard.id).label('event_count'),
        func.sum(IndividualEventScoreCard.total_points).label('combined_score')
    ).join(
        IndividualEventScoreCard, UnitMembers.id == IndividualEventScoreCard.participant_id
    ).where(
        and_(
            UnitMembers.gender == 'F',
            IndividualEventScoreCard.total_points >= 2
        )
    ).group_by(UnitMembers.id, UnitMembers.name).having(
        func.count(IndividualEventScoreCard.id) >= 2
    ).order_by(func.sum(IndividualEventScoreCard.total_points).desc())
    
    result = await db.execute(stmt)
    kalathilakam_data = result.first()
    
    kalathilakam = None
    if kalathilakam_data:
        stmt = select(UnitMembers).where(UnitMembers.name == kalathilakam_data[0]).options(
            selectinload(UnitMembers.registered_user).selectinload(CustomUser.unit_name).selectinload(UnitName.district)
        )
        result = await db.execute(stmt)
        member = result.scalar_one()
        
        kalathilakam = {
            "participant_name": member.name,
            "participant_unit": member.registered_user.unit_name.name,
            "participant_district": member.registered_user.unit_name.district.name,
            "combined_score": kalathilakam_data[3],
            "event_count": kalathilakam_data[2],
        }
    
    return {
        "kalaprathibha": kalaprathibha,
        "kalathilakam": kalathilakam,
    }


async def get_district_statistics(
    db: AsyncSession,
    district_id: int,
) -> Dict[str, Any]:
    """Get event statistics for a district."""
    # Individual events count
    stmt = select(func.count()).select_from(IndividualEventParticipation).join(
        CustomUser, IndividualEventParticipation.added_by_id == CustomUser.id
    ).where(CustomUser.clergy_district_id == district_id)
    result = await db.execute(stmt)
    individual_count = result.scalar() or 0
    
    # Group events count (distinct teams)
    stmt = select(func.count(func.distinct(GroupEventParticipation.chest_number))).select_from(
        GroupEventParticipation
    ).join(
        CustomUser, GroupEventParticipation.added_by_id == CustomUser.id
    ).where(CustomUser.clergy_district_id == district_id)
    result = await db.execute(stmt)
    group_count = result.scalar() or 0
    
    # Calculate amounts
    individual_amount = individual_count * INDIVIDUAL_FEE
    group_amount = group_count * GROUP_FEE
    total_amount = individual_amount + group_amount
    
    # Get payment
    stmt = select(KalamelaPayments).join(
        CustomUser, KalamelaPayments.paid_by_id == CustomUser.id
    ).where(CustomUser.clergy_district_id == district_id).order_by(
        KalamelaPayments.created_on.desc()
    )
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    return {
        "individual_events_count": individual_count,
        "group_events_count": group_count,
        "individual_event_amount": individual_amount,
        "group_event_amount": group_amount,
        "total_amount_to_pay": total_amount,
        "payment_status": payment.payment_status.value if payment else None,
        "payment": payment,
    }


# Excluded Members
async def exclude_member(
    db: AsyncSession,
    member_id: int,
) -> KalamelaExcludeMembers:
    """Exclude a member from all events."""
    # Check if already excluded
    stmt = select(KalamelaExcludeMembers).where(
        KalamelaExcludeMembers.members_id == member_id
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member is already excluded"
        )
    
    excluded = KalamelaExcludeMembers(members_id=member_id)
    db.add(excluded)
    await db.commit()
    await db.refresh(excluded)
    
    return excluded


async def remove_exclusion(
    db: AsyncSession,
    exclusion_id: int,
) -> bool:
    """Remove member from exclusion list."""
    stmt = select(KalamelaExcludeMembers).where(KalamelaExcludeMembers.id == exclusion_id)
    result = await db.execute(stmt)
    excluded = result.scalar_one_or_none()
    
    if not excluded:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exclusion not found"
        )
    
    await db.delete(excluded)
    await db.commit()
    
    return True
