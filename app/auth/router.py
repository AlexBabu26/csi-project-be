from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth import schemas as auth_schema
from app.common.schemas import Message
from app.common.security import get_current_payload
from app.auth.service import AuthService
from app.auth.models import CustomUser

router = APIRouter()


@router.post("/login", response_model=auth_schema.Token)
def login(payload: auth_schema.UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.login(payload)


@router.post("/register-unit", response_model=auth_schema.UserRead, status_code=status.HTTP_201_CREATED)
def register_unit(payload: auth_schema.UnitRegistrationRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register_unit(payload)


@router.get("/unit-names", response_model=list[auth_schema.UnitName])
def list_unit_names(district_id: int | None = None, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.get_unit_names(district_id)


@router.get("/me", response_model=auth_schema.UserRead)
def me(payload=Depends(get_current_payload), db: Session = Depends(get_db)):
    user = db.get(CustomUser, int(payload.sub))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return auth_schema.UserRead.model_validate(user)


@router.post("/forgot-password/request", response_model=Message)
def forgot_password_request(data: auth_schema.PasswordResetRequest):
    # In a full implementation, issue signed token and email it. Placeholder for now.
    return Message(message="Password reset link would be sent if this were wired to email.")


@router.post("/forgot-password/confirm", response_model=Message)
def forgot_password_confirm(_: auth_schema.PasswordResetConfirm):
    return Message(message="Password reset not implemented in this sample.")

