"""Conference public router - publicly accessible conference endpoints."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_db
from app.conference.schemas import ConferenceResponse
from app.conference import service as conference_service

router = APIRouter()


@router.get("/list", response_model=List[ConferenceResponse])
async def list_active_conferences(
    db: AsyncSession = Depends(get_db),
):
    """List all active conferences."""
    return await conference_service.get_active_conferences(db)


@router.get("/{conference_id}", response_model=ConferenceResponse)
async def get_conference(
    conference_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get conference details by ID."""
    return await conference_service.get_conference_by_id(db, conference_id)

