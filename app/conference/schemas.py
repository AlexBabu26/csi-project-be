from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.common.schemas import Timestamped


class ConferenceCreate(BaseModel):
    title: str
    details: Optional[str] = None


class ConferenceRead(ConferenceCreate, Timestamped):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class DelegateCreate(BaseModel):
    conference_id: int
    official_user_id: int
    member_id: Optional[int] = None


class ConferencePaymentCreate(BaseModel):
    conference_id: int
    amount_to_pay: int
    payment_reference: Optional[str] = None


class ConferencePaymentRead(BaseModel):
    id: int
    conference_id: int
    amount_to_pay: int
    status: str
    proof_path: Optional[str] = None
    date: datetime

    model_config = ConfigDict(from_attributes=True)

