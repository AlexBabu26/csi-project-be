from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import CustomUser, UnitMembers, UserType
from app.kalamela.models import IndividualEventParticipation, GroupEventParticipation, KalamelaPayments
from app.common.exporter import write_rows_to_xlsx


class AdminService:
    def __init__(self, session: Session):
        self.session = session

    def dashboard_counts(self) -> dict:
        users = self.session.execute(select(func.count()).select_from(CustomUser)).scalar_one()
        units = self.session.execute(
            select(func.count()).select_from(CustomUser).where(CustomUser.user_type == UserType.UNIT)
        ).scalar_one()
        members = self.session.execute(select(func.count()).select_from(UnitMembers)).scalar_one()
        indiv = self.session.execute(select(func.count()).select_from(IndividualEventParticipation)).scalar_one()
        group = self.session.execute(select(func.count()).select_from(GroupEventParticipation)).scalar_one()
        payments = self.session.execute(select(func.count()).select_from(KalamelaPayments)).scalar_one()
        return {
            "users": users,
            "units": units,
            "members": members,
            "individual_participations": indiv,
            "group_participations": group,
            "payments": payments,
        }

    def export_users(self) -> str:
        headers = ["id", "email", "username", "user_type", "phone"]
        rows = self.session.execute(
            select(CustomUser.id, CustomUser.email, CustomUser.username, CustomUser.user_type, CustomUser.phone_number)
        ).all()
        path = write_rows_to_xlsx(headers, rows, "users.xlsx")
        return str(path)

