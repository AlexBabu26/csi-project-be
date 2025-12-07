from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.common.config import get_settings
from app.auth.schemas import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_minutes: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> str:
    expire_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return TokenPayload(sub=payload.get("sub"), exp=payload.get("exp"), role=payload.get("role"))
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc


def get_current_payload(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    return decode_token(token)


def require_role(*roles: str):
    def dependency(payload: TokenPayload = Depends(get_current_payload)) -> TokenPayload:
        if not payload.role or payload.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return payload

    return dependency

