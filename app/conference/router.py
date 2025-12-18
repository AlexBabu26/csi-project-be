from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth.models import UserType, CustomUser
from app.kalamela.models import PaymentStatus
from app.conference import schemas as conf_schema
from app.common.security import get_current_user_sync, require_role
from app.conference.service import ConferenceService

router = APIRouter()


@router.get("/", response_model=list[conf_schema.ConferenceRead], dependencies=[Depends(require_role("1", "3"))])
def list_conferences(db: Session = Depends(get_db)):
    return ConferenceService(db).list_conferences()


@router.post("/", response_model=conf_schema.ConferenceRead, dependencies=[Depends(require_role("1"))])
def create_conference(payload: conf_schema.ConferenceCreate, db: Session = Depends(get_db)):
    return ConferenceService(db).create_conference(payload)


@router.post("/delegate", dependencies=[Depends(require_role("1", "3"))])
def add_delegate(payload: conf_schema.DelegateCreate, db: Session = Depends(get_db)):
    ConferenceService(db).add_delegate(payload)
    return {"status": "ok"}


@router.post("/payment", response_model=conf_schema.ConferencePaymentRead, dependencies=[Depends(require_role("1", "3"))])
def create_payment(
    payload: conf_schema.ConferencePaymentCreate,
    current_user: CustomUser = Depends(get_current_user_sync),
    db: Session = Depends(get_db),
):
    return ConferenceService(db).create_payment(current_user.id, payload, proof_path=None)


@router.post("/payment/{payment_id}/proof", response_model=conf_schema.ConferencePaymentRead, dependencies=[Depends(require_role("1", "3"))])
def upload_payment_proof(payment_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return ConferenceService(db).attach_proof(payment_id, file)


@router.post("/payment/{payment_id}/status", dependencies=[Depends(require_role("1"))], response_model=conf_schema.ConferencePaymentRead)
def update_payment_status(payment_id: int, status_value: PaymentStatus, db: Session = Depends(get_db)):
    return ConferenceService(db).set_status(payment_id, status_value)

