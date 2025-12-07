from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.models import ClergyDistrict, CustomUser, LoginAudit, UnitName, UnitRegistrationData, UserType
from app.auth import schemas as auth_schema
from app.common.security import create_access_token, get_password_hash, verify_password


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def _create_login_audit(self, username: str, user_id: Optional[int], success: bool) -> None:
        audit = LoginAudit(username=username, user_id=user_id, success=success)
        self.session.add(audit)

    def login(self, data: auth_schema.UserLogin) -> auth_schema.Token:
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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        self._create_login_audit(data.username, user.id, True)
        token = create_access_token(str(user.id), extra={"role": user.user_type.value})
        return auth_schema.Token(access_token=token)

    def register_unit(self, payload: auth_schema.UnitRegistrationRequest) -> auth_schema.UserRead:
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

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
        self.session.add(UnitRegistrationData(registered_user_id=user.id, status="Registration Started"))
        self.session.commit()
        return auth_schema.UserRead.model_validate(user)

    def get_unit_names(self, district_id: Optional[int] = None) -> List[auth_schema.UnitName]:
        stmt = select(UnitName)
        if district_id:
            stmt = stmt.where(UnitName.clergy_district_id == district_id)
        rows = self.session.execute(stmt.order_by(UnitName.name)).scalars().all()
        return [auth_schema.UnitName.model_validate(row) for row in rows]

    def create_clergy_district(self, name: str) -> ClergyDistrict:
        district = ClergyDistrict(name=name)
        self.session.add(district)
        self.session.commit()
        return district

