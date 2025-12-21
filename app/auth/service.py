"""Authentication service with JWT token management."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.models import (
    ClergyDistrict,
    CustomUser,
    LoginAudit,
    RefreshToken,
    UnitName,
    UnitRegistrationData,
    UserType,
)
from app.auth import schemas as auth_schema
from app.common.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)
from app.common.config import get_settings

settings = get_settings()


class AuthService:
    """Service for authentication and user management."""

    def __init__(self, session: Session):
        self.session = session

    def _create_login_audit(self, username: str, user_id: Optional[int], success: bool) -> None:
        """Create login audit log entry."""
        audit = LoginAudit(username=username, user_id=user_id, success=success)
        self.session.add(audit)

    def login(self, data: auth_schema.UserLogin) -> auth_schema.LoginResponse:
        """
        Authenticate user and return tokens with routing information.
        
        Implements single session: invalidates all existing refresh tokens on new login.
        
        Args:
            data: Login credentials (includes optional portal context for routing)
        
        Returns:
            LoginResponse with access token, refresh token, user type, and redirect URL
        
        Raises:
            HTTPException: If credentials are invalid
        """
        # 1. Authenticate user
        query = select(CustomUser).where(
            or_(
                CustomUser.username == data.username,
                CustomUser.email == data.username,
                CustomUser.phone_number == data.username,
            )
        )
        user = self.session.execute(query).scalar_one_or_none()
        
        if not user or not verify_password(data.password, user.hashed_password) or not user.is_active:
            self._create_login_audit(data.username, user.id if user else None, False)
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # 2. SINGLE SESSION: Revoke all existing refresh tokens for this user
        self.session.query(RefreshToken).filter(
            RefreshToken.user_id == user.id
        ).update({"revoked": True})
        
        # 3. Create access token (15 min)
        access_token = create_access_token(
            str(user.id),
            extra={"role": user.user_type.value}
        )
        
        # 4. Create refresh token (7 days) and store in DB
        refresh_token_str = create_refresh_token(str(user.id))
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
        self.session.add(refresh_token)
        
        # 5. Create login audit
        self._create_login_audit(data.username, user.id, True)
        self.session.commit()
        
        # 6. Determine redirect URL based on user_type AND portal context
        redirect_url = self._get_redirect_url(user.user_type, data.portal)
        
        return auth_schema.LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user_type=user.user_type.value,
            redirect_url=redirect_url,
        )

    def _get_redirect_url(self, user_type: UserType, portal: Optional[str] = None) -> str:
        """
        Determine redirect URL based on user type and portal context.
        
        For DISTRICT_OFFICIAL users, the portal parameter determines whether
        they are redirected to Kalamela or Conference home page.
        
        Args:
            user_type: The user's type (ADMIN, UNIT, DISTRICT_OFFICIAL)
            portal: Optional portal context ('kalamela', 'conference', or None)
        
        Returns:
            Appropriate redirect URL
        """
        # Default redirect map
        default_redirects = {
            UserType.ADMIN: "/admin/dashboard",
            UserType.UNIT: "/units/dashboard",
            UserType.DISTRICT_OFFICIAL: "/conference/official/home",  # Default for district officials
        }
        
        # Portal-specific redirects for DISTRICT_OFFICIAL
        if user_type == UserType.DISTRICT_OFFICIAL and portal:
            portal_redirects = {
                "kalamela": "/kalamela/official/home",
                "conference": "/conference/official/home",
            }
            return portal_redirects.get(portal.lower(), default_redirects[user_type])
        
        return default_redirects.get(user_type, "/")

    def refresh_access_token(self, refresh_token_str: str) -> auth_schema.Token:
        """
        Create new access token using refresh token.
        
        Args:
            refresh_token_str: Refresh token string
        
        Returns:
            Token with new access token and same refresh token
        
        Raises:
            HTTPException: If refresh token is invalid, revoked, or expired
        """
        # 1. Decode refresh token
        payload = decode_refresh_token(refresh_token_str)
        
        # 2. Validate refresh token exists in DB and is not revoked
        refresh_token = self.session.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # 3. Get user
        user = self.session.get(CustomUser, refresh_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # 4. Create new access token
        access_token = create_access_token(
            str(user.id),
            extra={"role": user.user_type.value}
        )
        
        return auth_schema.Token(
            access_token=access_token,
            refresh_token=refresh_token_str,  # Keep same refresh token
        )

    def logout_all_sessions(self, user_id: int) -> None:
        """
        Revoke all refresh tokens for a user (logout from all devices).
        
        Args:
            user_id: User ID to logout
        """
        self.session.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).update({"revoked": True})
        self.session.commit()

    def register_unit(self, payload: auth_schema.UnitRegistrationRequest) -> auth_schema.UserRead:
        """
        Register a new unit user.
        
        Args:
            payload: Registration data
        
        Returns:
            Created user
        
        Raises:
            HTTPException: If user already exists
        """
        existing = self.session.execute(
            select(CustomUser).where(
                or_(
                    CustomUser.email == payload.email,
                    CustomUser.username == payload.email,
                    CustomUser.phone_number == payload.phone_number,
                )
            )
        ).scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )

        user = CustomUser(
            email=payload.email,
            username=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
            user_type=UserType.UNIT,
            unit_name_id=payload.unit_name_id,
            clergy_district_id=payload.clergy_district_id,
            hashed_password=get_password_hash(payload.password),
        )
        self.session.add(user)
        self.session.flush()
        
        self.session.add(
            UnitRegistrationData(
                registered_user_id=user.id,
                status="Registration Started"
            )
        )
        self.session.commit()
        
        return auth_schema.UserRead.model_validate(user)

    def get_unit_names(self, district_id: Optional[int] = None) -> List[auth_schema.UnitName]:
        """
        Get list of unit names, optionally filtered by district.
        
        Args:
            district_id: Optional district ID to filter by
        
        Returns:
            List of unit names
        """
        stmt = select(UnitName)
        if district_id:
            stmt = stmt.where(UnitName.clergy_district_id == district_id)
        
        rows = self.session.execute(stmt.order_by(UnitName.name)).scalars().all()
        return [auth_schema.UnitName.model_validate(row) for row in rows]

    def create_clergy_district(self, name: str) -> ClergyDistrict:
        """
        Create a new clergy district.
        
        Args:
            name: District name
        
        Returns:
            Created district
        """
        district = ClergyDistrict(name=name)
        self.session.add(district)
        self.session.commit()
        return district
