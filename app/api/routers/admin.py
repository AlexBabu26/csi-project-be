from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.common.security import require_role
from app.common.admin_service import AdminService

router = APIRouter(dependencies=[Depends(require_role("1"))])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return AdminService(db).dashboard_counts()


@router.get("/exports/users")
def export_users(db: Session = Depends(get_db)):
    path = AdminService(db).export_users()
    return FileResponse(path, filename="users.xlsx")


@router.get("/statistics/districts")
def get_all_districts_statistics(db: Session = Depends(get_db)):
    """Get participation statistics for all districts"""
    return AdminService(db).get_district_statistics()


@router.get("/statistics/districts/{district_id}")
def get_district_statistics(district_id: int, db: Session = Depends(get_db)):
    """Get participation statistics for a specific district"""
    return AdminService(db).get_district_statistics(district_id)

