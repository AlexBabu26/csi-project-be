"""Security utilities for authentication and authorization."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.config import get_settings
from app.common.db import get_db, get_async_db
from app.auth.schemas import TokenPayload

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Supports both:
    - bcrypt hashes (new FastAPI format)
    - Django's pbkdf2_sha256 hashes (migrated from Django)
    """
    if hashed_password.startswith('pbkdf2_sha256$'):
        # Django password hash format: pbkdf2_sha256$iterations$salt$hash
        return _verify_django_password(plain_password, hashed_password)
    else:
        # bcrypt format (new passwords)
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False


def _verify_django_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Django's pbkdf2_sha256 hash."""
    import hashlib
    import base64
    
    try:
        algorithm, iterations, salt, hash_b64 = hashed_password.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        
        iterations = int(iterations)
        expected_hash = base64.b64decode(hash_b64)
        
        # Compute the hash using the same parameters
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations,
            dklen=len(expected_hash)
        )
        
        # Constant-time comparison
        import hmac
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False


# def get_password_hash(password: str) -> str:
#     """Hash a password for storage."""
#     return pwd_context.hash(password)

def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(subject: str, expires_minutes: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a short-lived JWT access token.
    
    Args:
        subject: User ID as string
        expires_minutes: Optional custom expiration (defaults to 15 minutes)
        extra: Optional extra claims (e.g., role)
    
    Returns:
        Encoded JWT token string
    """
    expire_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "access"
    }
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str, expires_days: Optional[int] = None) -> str:
    """
    Create a long-lived JWT refresh token.
    
    Args:
        subject: User ID as string
        expires_days: Optional custom expiration (defaults to 7 days)
    
    Returns:
        Encoded JWT token string
    """
    expire_delta = timedelta(days=expires_days or settings.refresh_token_expire_days)
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate access token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenPayload with user info
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return TokenPayload(sub=payload.get("sub"), exp=payload.get("exp"), role=payload.get("role"))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        ) from exc


def decode_refresh_token(token: str) -> TokenPayload:
    """
    Decode and validate refresh token structure.
    
    Args:
        token: JWT refresh token string
    
    Returns:
        TokenPayload with user info
    
    Raises:
        HTTPException: If token is invalid or wrong type
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return TokenPayload(sub=payload.get("sub"), exp=payload.get("exp"))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        ) from exc


def get_current_payload(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    """
    Get token payload from access token (stateless validation).
    
    Args:
        token: JWT token from Authorization header
    
    Returns:
        TokenPayload with user info
    """
    return decode_token(token)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get current user from access token (async version).

    Validates JWT signature and expiration, then fetches user from database.
    Access tokens are stateless (no DB check for token itself).

    Args:
        token: JWT token from Authorization header
        db: Async database session

    Returns:
        CustomUser object

    Raises:
        HTTPException: If user not found or inactive
    """
    from app.auth.models import CustomUser

    payload = decode_token(token)
    user_id = int(payload.sub)

    # Fetch user from DB
    user = await db.get(CustomUser, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def get_current_user_sync(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get current user from access token (sync version).
    
    For non-async endpoints.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
    
    Returns:
        CustomUser object
    
    Raises:
        HTTPException: If user not found or inactive
    """
    from app.auth.models import CustomUser
    
    payload = decode_token(token)
    user_id = int(payload.sub)
    
    user = db.get(CustomUser, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def require_role(*roles: str):
    """
    Dependency to require specific roles.
    
    Args:
        *roles: One or more role values to allow
    
    Returns:
        Dependency function
    """
    def dependency(payload: TokenPayload = Depends(get_current_payload)) -> TokenPayload:
        if not payload.role or payload.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return payload

    return dependency
