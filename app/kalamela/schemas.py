from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.kalamela.models import SeniorityCategory
from app.common.schemas import Timestamped


class IndividualEventCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class IndividualEventRead(IndividualEventCreate, Timestamped):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GroupEventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_allowed_limit: int = 2
    min_allowed_limit: int = 1
    per_unit_allowed_limit: int = 2


class GroupEventRead(GroupEventCreate, Timestamped):
    id: int

    model_config = ConfigDict(from_attributes=True)


class IndividualParticipationCreate(BaseModel):
    individual_event_id: int
    participant_id: int
    seniority_category: Optional[SeniorityCategory] = None


class GroupParticipationCreate(BaseModel):
    group_event_id: int
    participant_id: int


class KalamelaPaymentCreate(BaseModel):
    individual_events_count: int = 0
    group_events_count: int = 0


class AppealCreate(BaseModel):
    participant_id: int
    chest_number: str
    event_name: str
    statement: str


class ScoreCardCreate(BaseModel):
    participation_id: int
    awarded_mark: int
    grade: Optional[str] = None
    total_points: int = 0


class GroupScoreCardCreate(BaseModel):
    event_name: str
    chest_number: str
    awarded_mark: int
    grade: Optional[str] = None
    total_points: int = 0

