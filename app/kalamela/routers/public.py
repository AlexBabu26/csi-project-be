"""Kalamela public router - public access endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_db
from app.auth.models import UnitMembers, UnitName, ClergyDistrict
from app.kalamela.models import (
    IndividualEvent,
    GroupEvent,
    IndividualEventParticipation,
    GroupEventParticipation,
    IndividualEventScoreCard,
    GroupEventScoreCard,
    Appeal,
)
from app.kalamela.schemas import (
    AppealCreate,
    AppealResponse,
    KalaprathibhaResult,
)
from app.kalamela import service as kalamela_service

router = APIRouter()


# Public Access
@router.get("/home", response_model=dict)
async def public_home(db: AsyncSession = Depends(get_async_db)):
    """
    Landing page data:
    - Total events
    - Total participants
    - Featured information
    """
    # Count events
    stmt = select(func.count()).select_from(IndividualEvent)
    result = await db.execute(stmt)
    individual_event_count = result.scalar() or 0
    
    stmt = select(func.count()).select_from(GroupEvent)
    result = await db.execute(stmt)
    group_event_count = result.scalar() or 0
    
    # Count participants
    stmt = select(func.count()).select_from(IndividualEventParticipation)
    result = await db.execute(stmt)
    individual_participant_count = result.scalar() or 0
    
    stmt = select(func.count(func.distinct(GroupEventParticipation.chest_number))).select_from(
        GroupEventParticipation
    )
    result = await db.execute(stmt)
    group_team_count = result.scalar() or 0
    
    return {
        "total_individual_events": individual_event_count,
        "total_group_events": group_event_count,
        "total_individual_participants": individual_participant_count,
        "total_group_teams": group_team_count,
        "message": "Welcome to CSI Madhya Kerala Diocese Youth Movement Kalamela",
    }


@router.post("/find-participant", response_model=dict)
async def find_participant_by_chest_number(
    chest_number: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Search participant by chest number.
    Returns individual and/or group participations with scores.
    """
    # Search in individual participations
    stmt = select(IndividualEventParticipation).where(
        IndividualEventParticipation.chest_number == chest_number
    ).options(
        selectinload(IndividualEventParticipation.individual_event),
        selectinload(IndividualEventParticipation.participant).selectinload(
            UnitMembers.registered_user
        ).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
    )
    result = await db.execute(stmt)
    individual_participations = list(result.scalars().all())
    
    # Search in group participations
    stmt = select(GroupEventParticipation).where(
        GroupEventParticipation.chest_number == chest_number
    ).options(
        selectinload(GroupEventParticipation.group_event),
        selectinload(GroupEventParticipation.participant).selectinload(
            UnitMembers.registered_user
        ).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
    )
    result = await db.execute(stmt)
    group_participations = list(result.scalars().all())
    
    if not individual_participations and not group_participations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No participant found with this chest number"
        )
    
    # Get scores for individual participations
    individual_scores = []
    for p in individual_participations:
        stmt = select(IndividualEventScoreCard).where(
            IndividualEventScoreCard.event_participation_id == p.id
        )
        result = await db.execute(stmt)
        score = result.scalar_one_or_none()
        
        individual_scores.append({
            "event_name": p.individual_event.name,
            "participant_name": p.participant.name,
            "unit_name": p.participant.registered_user.unit_name.name,
            "district_name": p.participant.registered_user.unit_name.district.name,
            "chest_number": p.chest_number,
            "score": score.total_points if score else None,
            "grade": score.grade if score else None,
            "awarded_mark": score.awarded_mark if score else None,
        })
    
    # Get scores for group participations
    group_scores = []
    for p in group_participations:
        stmt = select(GroupEventScoreCard).where(
            GroupEventScoreCard.chest_number == chest_number
        )
        result = await db.execute(stmt)
        score = result.scalar_one_or_none()
        
        group_scores.append({
            "event_name": p.group_event.name,
            "participant_name": p.participant.name,
            "unit_name": p.participant.registered_user.unit_name.name,
            "district_name": p.participant.registered_user.unit_name.district.name,
            "chest_number": p.chest_number,
            "score": score.total_points if score else None,
            "grade": score.grade if score else None,
            "awarded_mark": score.awarded_mark if score else None,
        })
    
    return {
        "chest_number": chest_number,
        "individual_participations": individual_scores,
        "group_participations": group_scores,
    }


@router.get("/results", response_model=dict)
async def get_top_results(db: AsyncSession = Depends(get_async_db)):
    """
    Get top 3 results for each event (individual and group).
    """
    # Get all individual events
    stmt = select(IndividualEvent)
    result = await db.execute(stmt)
    individual_events = list(result.scalars().all())
    
    individual_results = {}
    
    for event in individual_events:
        # Get top 3 scores for this event
        stmt = select(IndividualEventScoreCard).join(
            IndividualEventParticipation,
            IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
        ).where(
            IndividualEventParticipation.individual_event_id == event.id
        ).options(
            selectinload(IndividualEventScoreCard.participant).selectinload(
                UnitMembers.registered_user
            ).selectinload(CustomUser.unit_name).selectinload(UnitName.district),
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
                    "district_name": score.participant.registered_user.unit_name.district.name,
                    "chest_number": score.participation.chest_number,
                    "awarded_mark": score.awarded_mark,
                    "total_points": score.total_points,
                    "grade": score.grade,
                }
                for idx, score in enumerate(top_scores)
            ]
    
    # Get all group events
    stmt = select(GroupEvent)
    result = await db.execute(stmt)
    group_events = list(result.scalars().all())
    
    group_results = {}
    
    for event in group_events:
        # Get top 3 scores for this event
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
                    "awarded_mark": score.awarded_mark,
                    "total_points": score.total_points,
                    "grade": score.grade,
                }
                for idx, score in enumerate(top_scores)
            ]
    
    return {
        "individual_results": individual_results,
        "group_results": group_results,
    }


@router.get("/kalaprathibha", response_model=dict)
async def get_kalaprathibha_kalathilakam(db: AsyncSession = Depends(get_async_db)):
    """
    Calculate and return:
    - Kalaprathibha (Male): 2+ events with 2+ points each, sum points
    - Kalathilakam (Female): 2+ events with 2+ points each, sum points
    """
    result = await kalamela_service.calculate_kalaprathibha(db)
    
    return result


# Appeals
@router.post("/appeal/check", response_model=dict)
async def check_appeal_eligibility(
    chest_number: str,
    event_name: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Check if appeal can be submitted:
    - Verify chest number and event
    - Check 30-minute window from score publication
    - Check if appeal already exists
    """
    # Find score
    from datetime import datetime, timedelta
    
    score_time = None
    
    # Check individual scores
    stmt = select(IndividualEventScoreCard).join(
        IndividualEventParticipation,
        IndividualEventScoreCard.event_participation_id == IndividualEventParticipation.id
    ).join(
        IndividualEvent,
        IndividualEventParticipation.individual_event_id == IndividualEvent.id
    ).where(
        and_(
            IndividualEventParticipation.chest_number == chest_number,
            IndividualEvent.name == event_name
        )
    )
    result = await db.execute(stmt)
    ind_score = result.scalar_one_or_none()
    
    if ind_score:
        score_time = ind_score.added_on
    
    # Check group scores
    if not score_time:
        stmt = select(GroupEventScoreCard).where(
            and_(
                GroupEventScoreCard.chest_number == chest_number,
                GroupEventScoreCard.event_name == event_name
            )
        )
        result = await db.execute(stmt)
        grp_score = result.scalar_one_or_none()
        
        if grp_score:
            score_time = grp_score.added_on
    
    if not score_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score found for this chest number and event"
        )
    
    # Check 30-minute window
    now = datetime.utcnow()
    time_elapsed = now - score_time
    is_within_window = time_elapsed <= timedelta(minutes=30)
    
    # Check if appeal already exists
    stmt = select(Appeal).where(
        and_(
            Appeal.chest_number == chest_number,
            Appeal.event_name == event_name
        )
    )
    result = await db.execute(stmt)
    existing_appeal = result.scalar_one_or_none()
    
    if existing_appeal:
        return {
            "eligible": False,
            "reason": "Appeal already submitted for this event",
            "appeal_id": existing_appeal.id,
        }
    
    if not is_within_window:
        return {
            "eligible": False,
            "reason": "Appeal window expired (30 minutes from score publication)",
            "score_time": score_time,
            "time_elapsed_minutes": int(time_elapsed.total_seconds() / 60),
        }
    
    return {
        "eligible": True,
        "score_time": score_time,
        "time_remaining_minutes": int((timedelta(minutes=30) - time_elapsed).total_seconds() / 60),
        "appeal_fee": 1000,
    }


@router.post("/appeal/submit", response_model=AppealResponse)
async def submit_appeal(
    data: AppealCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Submit appeal with ₹1000 payment.
    Creates appeal and associated payment record.
    """
    appeal = await kalamela_service.create_appeal(db, data)
    
    return appeal


@router.get("/appeals/status", response_model=List[dict])
async def view_appeal_status(
    participant_id: Optional[int] = None,
    chest_number: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    View appeal status with replies.
    Can filter by participant_id or chest_number.
    """
    stmt = select(Appeal)
    
    if participant_id:
        stmt = stmt.where(Appeal.added_by_id == participant_id)
    elif chest_number:
        stmt = stmt.where(Appeal.chest_number == chest_number)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide participant_id or chest_number"
        )
    
    stmt = stmt.order_by(Appeal.created_on.desc())
    result = await db.execute(stmt)
    appeals = list(result.scalars().all())
    
    return [
        {
            "id": appeal.id,
            "chest_number": appeal.chest_number,
            "event_name": appeal.event_name,
            "statement": appeal.statement,
            "reply": appeal.reply,
            "status": appeal.status.value,
            "created_on": appeal.created_on,
        }
        for appeal in appeals
    ]


# Import fix
from app.auth.models import CustomUser
