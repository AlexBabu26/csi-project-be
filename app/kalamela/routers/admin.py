from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.kalamela import schemas as kala_schema
from app.common.security import require_role
from app.kalamela.service import KalamelaService
from app.kalamela.models import PaymentStatus

router = APIRouter(dependencies=[Depends(require_role("1"))])


@router.post("/events/individual", status_code=201)
def create_individual_event(payload: kala_schema.IndividualEventCreate, db: Session = Depends(get_db)):
    return KalamelaService(db).create_individual_event(payload)


@router.post("/events/group", status_code=201)
def create_group_event(payload: kala_schema.GroupEventCreate, db: Session = Depends(get_db)):
    return KalamelaService(db).create_group_event(payload)


@router.post("/scores/individual", status_code=201)
def add_individual_score(payload: kala_schema.ScoreCardCreate, db: Session = Depends(get_db)):
    return KalamelaService(db).add_individual_score(payload)


@router.post("/scores/group", status_code=201)
def add_group_score(payload: kala_schema.GroupScoreCardCreate, db: Session = Depends(get_db)):
    return KalamelaService(db).add_group_score(payload)


@router.post("/payments/{payment_id}/status", status_code=200)
def set_payment_status(payment_id: int, status_value: PaymentStatus, db: Session = Depends(get_db)):
    return KalamelaService(db).set_payment_status(payment_id, status_value)

