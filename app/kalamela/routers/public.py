from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.kalamela import schemas as kala_schema
from app.kalamela.service import KalamelaService

router = APIRouter()


@router.get("/results/individual")
def top_individual(db: Session = Depends(get_db)):
    service = KalamelaService(db)
    return service.top_results_individual()


@router.get("/results/group")
def top_group(db: Session = Depends(get_db)):
    service = KalamelaService(db)
    return service.top_results_group()


@router.post("/appeals", status_code=201)
def submit_appeal(payload: kala_schema.AppealCreate, db: Session = Depends(get_db)):
    service = KalamelaService(db)
    return service.submit_appeal(payload)

