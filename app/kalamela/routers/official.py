from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth.models import CustomUser
from app.kalamela import schemas as kala_schema
from app.common.security import get_current_payload, require_role
from app.kalamela.service import KalamelaService

router = APIRouter(dependencies=[Depends(require_role("2", "3"))])


def _current_user(payload, db: Session) -> CustomUser:
    user = db.get(CustomUser, int(payload.sub))
    if not user:
        raise ValueError("User missing")
    return user


@router.post("/individual-participations", status_code=201)
def add_individual(
    payload: kala_schema.IndividualParticipationCreate,
    token=Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    user = _current_user(token, db)
    return KalamelaService(db).add_individual_participation(user, payload)


@router.post("/group-participations", status_code=201)
def add_group(payload: kala_schema.GroupParticipationCreate, token=Depends(get_current_payload), db: Session = Depends(get_db)):
    user = _current_user(token, db)
    return KalamelaService(db).add_group_participation(user, payload)


@router.post("/payments", status_code=201)
def create_payment(payload: kala_schema.KalamelaPaymentCreate, token=Depends(get_current_payload), db: Session = Depends(get_db)):
    user = _current_user(token, db)
    return KalamelaService(db).create_payment(user, payload, proof_path=None)


@router.post("/payments/{payment_id}/proof", status_code=200)
def upload_payment_proof(
    payment_id: int, file: UploadFile = File(...), token=Depends(get_current_payload), db: Session = Depends(get_db)
):
    _current_user(token, db)
    return KalamelaService(db).upload_payment_proof(payment_id, file)

