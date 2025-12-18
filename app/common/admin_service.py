from typing import List
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import CustomUser, UnitMembers, UserType, ClergyDistrict
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

    def get_district_statistics(self, district_id: int | None = None) -> dict | List[dict]:
        """Get participation statistics by district"""
        if district_id:
            # Single district stats
            district = self.session.get(ClergyDistrict, district_id)
            if not district:
                return {}
            
            district_users = select(CustomUser.id).where(
                CustomUser.clergy_district_id == district_id
            ).scalar_subquery()
            
            units_count = self.session.execute(
                select(func.count()).select_from(CustomUser).where(
                    CustomUser.clergy_district_id == district_id,
                    CustomUser.user_type == UserType.UNIT
                )
            ).scalar_one()
            
            members_count = self.session.execute(
                select(func.count()).select_from(UnitMembers).where(
                    UnitMembers.registered_user_id.in_(district_users)
                )
            ).scalar_one()
            
            indiv_count = self.session.execute(
                select(func.count()).select_from(IndividualEventParticipation).where(
                    IndividualEventParticipation.added_by_id.in_(district_users)
                )
            ).scalar_one()
            
            group_count = self.session.execute(
                select(func.count()).select_from(GroupEventParticipation).where(
                    GroupEventParticipation.added_by_id.in_(district_users)
                )
            ).scalar_one()
            
            payments_count = self.session.execute(
                select(func.count()).select_from(KalamelaPayments).where(
                    KalamelaPayments.paid_by_id.in_(district_users)
                )
            ).scalar_one()
            
            total_payment_amount = self.session.execute(
                select(func.sum(KalamelaPayments.total_amount_to_pay)).where(
                    KalamelaPayments.paid_by_id.in_(district_users)
                )
            ).scalar_one() or 0
            
            return {
                "district_id": district_id,
                "district_name": district.name,
                "units": units_count,
                "members": members_count,
                "individual_participations": indiv_count,
                "group_participations": group_count,
                "payments": payments_count,
                "total_payment_amount": total_payment_amount
            }
        else:
            # All districts stats
            districts = self.session.execute(
                select(ClergyDistrict).order_by(ClergyDistrict.name)
            ).scalars().all()
            
            return [self.get_district_statistics(d.id) for d in districts]

