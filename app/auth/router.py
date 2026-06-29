"""Authentication router with JWT token management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth import schemas as auth_schema
from app.common.schemas import Message
from app.common.security import get_current_user_sync
from app.auth.service import AuthService
from app.auth.models import CustomUser
from app.common.cache import get_cache, set_cache, TTL_MASTER_DATA

router = APIRouter()


@router.post("/login", response_model=auth_schema.LoginResponse)
def login(payload: auth_schema.UserLogin, db: Session = Depends(get_db)):
    """
    Login with username/email/phone and password.
    
    Returns access token (15 min), refresh token (7 days), user type, and redirect URL.
    Invalidates all previous sessions (single session per user).
    """
    service = AuthService(db)
    return service.login(payload)


@router.post("/refresh", response_model=auth_schema.Token)
def refresh_token(
    payload: auth_schema.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Frontend should call this automatically before access token expires.
    Returns new access token (15 min) and keeps the same refresh token.
    """
    service = AuthService(db)
    return service.refresh_access_token(payload.refresh_token)


@router.post("/logout", response_model=Message)
def logout(
    current_user: CustomUser = Depends(get_current_user_sync),
    db: Session = Depends(get_db)
):
    """
    Logout from all sessions (revoke all refresh tokens).

    Access tokens will expire naturally within 15 minutes.
    Requires valid access token.
    """
    from app.common.cache import clear_cache
    service = AuthService(db)
    service.logout_all_sessions(current_user.id)
    clear_cache(f"_user:{current_user.id}")
    return Message(message="Logged out from all devices")


@router.post("/register-unit", response_model=auth_schema.UserRead, status_code=status.HTTP_201_CREATED)
def register_unit(payload: auth_schema.UnitRegistrationRequest, db: Session = Depends(get_db)):
    """
    Register a new unit user.
    
    Creates user account with UNIT user type and initializes registration data.
    """
    service = AuthService(db)
    return service.register_unit(payload)


@router.get("/districts", response_model=list[auth_schema.ClergyDistrictItem])
def list_districts(db: Session = Depends(get_db)):
    """Get clergy districts with at least one unregistered unit."""
    cache_key = "auth:districts"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    service = AuthService(db)
    result = service.get_districts()
    set_cache(cache_key, result, TTL_MASTER_DATA)
    return result


@router.get("/registration-username-preview", response_model=auth_schema.UsernamePreviewResponse)
def preview_registration_username(
    clergy_district_id: int,
    db: Session = Depends(get_db),
):
    """Preview the registration username before account creation."""
    service = AuthService(db)
    return service.preview_registration_username(clergy_district_id)


@router.get("/unit-names", response_model=list[auth_schema.UnitName])
def list_unit_names(district_id: int | None = None, db: Session = Depends(get_db)):
    """
    Get unit names available for registration.

    Optionally filter by district ID. Excludes already registered units.
    """
    cache_key = f"auth:unit_names:{district_id or 'all'}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    service = AuthService(db)
    result = service.get_unit_names(district_id)
    set_cache(cache_key, result, TTL_MASTER_DATA)
    return result


@router.get("/me", response_model=auth_schema.UserRead)
def me(current_user: CustomUser = Depends(get_current_user_sync)):
    """
    Get current authenticated user information.
    
    Requires valid access token.
    """
    return auth_schema.UserRead.model_validate(current_user)


@router.post("/forgot-password/request", response_model=Message)
def forgot_password_request(data: auth_schema.PasswordResetRequest):
    """
    Request password reset (placeholder).
    
    In a full implementation, this would generate a signed token and email it.
    """
    return Message(message="Password reset link would be sent if this were wired to email.")


@router.post("/forgot-password/confirm", response_model=Message)
def forgot_password_confirm(_: auth_schema.PasswordResetConfirm):
    """
    Confirm password reset (placeholder).
    
    In a full implementation, this would validate the token and update the password.
    """
    return Message(message="Password reset not implemented in this sample.")
