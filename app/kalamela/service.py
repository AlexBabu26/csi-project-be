from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.auth.models import CustomUser, UnitMembers, UserType
from app.kalamela.models import (
    Appeal,
    AppealPayments,
    AppealStatus,
    GroupEvent,
    GroupEventParticipation,
    GroupEventScoreCard,
    IndividualEvent,
    IndividualEventParticipation,
    IndividualEventScoreCard,
    KalamelaExcludeMembers,
    KalamelaPayments,
    PaymentStatus,
    SeniorityCategory,
)
from app.kalamela import schemas as kala_schema
from app.common.storage import save_upload_file


INDIVIDUAL_FEE = 50
GROUP_FEE = 100
APPEAL_FEE = 1000


class KalamelaService:
    def __init__(self, session: Session):
        self.session = session

    # --- helpers ---
    def _district_id(self, user: CustomUser) -> int:
        if not user.clergy_district_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User missing district assignment")
        return user.clergy_district_id

    def _unit_id(self, user: CustomUser) -> int:
        if not user.unit_name_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User missing unit assignment")
        return user.unit_name_id

    def _generate_individual_chest(
        self, event_id: int, district_id: int, seniority: Optional[SeniorityCategory]
    ) -> str:
        prefix = "J" if seniority == SeniorityCategory.JUNIOR else "S" if seniority == SeniorityCategory.SENIOR else "I"
        count = (
            self.session.execute(
                select(func.count()).select_from(IndividualEventParticipation).where(
                    and_(
                        IndividualEventParticipation.individual_event_id == event_id,
                        IndividualEventParticipation.chest_number.like(f"{prefix}{event_id:03d}-{district_id:02d}-%"),
                    )
                )
            ).scalar_one()
            or 0
        )
        return f"{prefix}{event_id:03d}-{district_id:02d}-{count + 1:03d}"

    def _generate_group_chest(self, event: GroupEvent, district_id: int) -> str:
        prefix = "".join([part[0].upper() for part in event.name.split()[:2]]) or "G"
        count = (
            self.session.execute(
                select(func.count()).select_from(GroupEventParticipation).where(
                    and_(
                        GroupEventParticipation.group_event_id == event.id,
                        GroupEventParticipation.chest_number.like(f"{prefix}{event.id:03d}-{district_id:02d}-%"),
                    )
                )
            ).scalar_one()
            or 0
        )
        return f"{prefix}{event.id:03d}-{district_id:02d}-{count + 1:03d}"

    # Events
    def create_individual_event(self, payload: kala_schema.IndividualEventCreate) -> IndividualEvent:
        event = IndividualEvent(name=payload.name, category=payload.category, description=payload.description)
        self.session.add(event)
        self.session.commit()
        return event

    def create_group_event(self, payload: kala_schema.GroupEventCreate) -> GroupEvent:
        event = GroupEvent(
            name=payload.name,
            description=payload.description,
            max_allowed_limit=payload.max_allowed_limit,
            min_allowed_limit=payload.min_allowed_limit,
            per_unit_allowed_limit=payload.per_unit_allowed_limit,
        )
        self.session.add(event)
        self.session.commit()
        return event

    # Participation
    def _ensure_not_excluded(self, participant_id: int):
        excluded = self.session.execute(
            select(KalamelaExcludeMembers).where(KalamelaExcludeMembers.members_id == participant_id)
        ).scalar_one_or_none()
        if excluded:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Participant excluded")

    def _count_individual_events(self, participant_id: int) -> int:
        return (
            self.session.execute(
                select(func.count()).select_from(IndividualEventParticipation).where(
                    IndividualEventParticipation.participant_id == participant_id
                )
            )
            .scalar_one()
        )

    def add_individual_participation(
        self, added_by: CustomUser, payload: kala_schema.IndividualParticipationCreate
    ) -> IndividualEventParticipation:
        member = self.session.get(UnitMembers, payload.participant_id)
        event = self.session.get(IndividualEvent, payload.individual_event_id)
        if not member or not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant or event not found")
        self._ensure_not_excluded(member.id)
        if self._count_individual_events(member.id) >= 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Participant reached max events")
        district_id = self._district_id(added_by)
        # limit: max 2 participants per district per event per seniority
        district_users = select(CustomUser.id).where(CustomUser.clergy_district_id == district_id).scalar_subquery()
        district_count = (
            self.session.execute(
                select(func.count()).select_from(IndividualEventParticipation).where(
                    and_(
                        IndividualEventParticipation.individual_event_id == event.id,
                        IndividualEventParticipation.seniority_category == payload.seniority_category,
                        IndividualEventParticipation.added_by_id.in_(district_users),
                    )
                )
            ).scalar_one()
            or 0
        )
        if district_count >= 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="District quota reached")

        chest = self._generate_individual_chest(event.id, district_id, payload.seniority_category)
        participation = IndividualEventParticipation(
            individual_event_id=event.id,
            participant_id=member.id,
            added_by_id=added_by.id,
            chest_number=chest,
            seniority_category=payload.seniority_category,
        )
        self.session.add(participation)
        self.session.commit()
        return participation

    def add_group_participation(
        self, added_by: CustomUser, payload: kala_schema.GroupParticipationCreate
    ) -> GroupEventParticipation:
        member = self.session.get(UnitMembers, payload.participant_id)
        event = self.session.get(GroupEvent, payload.group_event_id)
        if not member or not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant or event not found")
        self._ensure_not_excluded(member.id)
        district_id = self._district_id(added_by)
        unit_id = self._unit_id(added_by)

        # prevent duplicate member in same event
        duplicate = self.session.execute(
            select(GroupEventParticipation).where(
                and_(
                    GroupEventParticipation.group_event_id == event.id,
                    GroupEventParticipation.participant_id == member.id,
                )
            )
        ).scalar_one_or_none()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member already registered for event")

        # limit: at most 2 teams per district per event
        district_users = select(CustomUser.id).where(CustomUser.clergy_district_id == district_id).scalar_subquery()
        district_count = (
            self.session.execute(
                select(func.count()).select_from(GroupEventParticipation).where(
                    and_(
                        GroupEventParticipation.group_event_id == event.id,
                        GroupEventParticipation.added_by_id.in_(district_users),
                    )
                )
            ).scalar_one()
            or 0
        )
        if district_count >= event.max_allowed_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="District quota reached for event")

        # per-unit allowed limit
        unit_users = select(CustomUser.id).where(CustomUser.unit_name_id == unit_id).scalar_subquery()
        unit_count = (
            self.session.execute(
                select(func.count()).select_from(GroupEventParticipation).where(
                    and_(
                        GroupEventParticipation.group_event_id == event.id,
                        GroupEventParticipation.added_by_id.in_(unit_users),
                    )
                )
            ).scalar_one()
            or 0
        )
        if unit_count >= event.per_unit_allowed_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit quota reached for event")

        chest = self._generate_group_chest(event, district_id)
        participation = GroupEventParticipation(
            group_event_id=event.id, participant_id=member.id, chest_number=chest, added_by_id=added_by.id
        )
        self.session.add(participation)
        self.session.commit()
        return participation

    # Payments
    def create_payment(
        self, user: CustomUser, payload: kala_schema.KalamelaPaymentCreate, proof_path: Optional[str]
    ) -> KalamelaPayments:
        total = payload.individual_events_count * INDIVIDUAL_FEE + payload.group_events_count * GROUP_FEE
        payment = KalamelaPayments(
            paid_by_id=user.id,
            individual_events_count=payload.individual_events_count,
            group_events_count=payload.group_events_count,
            total_amount_to_pay=total,
            payment_proof_path=proof_path,
            payment_status=PaymentStatus.PROOF_UPLOADED if proof_path else PaymentStatus.PENDING,
        )
        self.session.add(payment)
        self.session.commit()
        return payment

    def upload_payment_proof(self, payment_id: int, file: UploadFile) -> KalamelaPayments:
        payment = self.session.get(KalamelaPayments, payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        _, dest = save_upload_file(file, subdir="kalamela/payments")
        payment.payment_proof_path = str(dest)
        payment.payment_status = PaymentStatus.PROOF_UPLOADED
        self.session.commit()
        return payment

    def set_payment_status(self, payment_id: int, status_value: PaymentStatus) -> KalamelaPayments:
        payment = self.session.get(KalamelaPayments, payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if status_value not in (PaymentStatus.PAID, PaymentStatus.DECLINED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")
        payment.payment_status = status_value
        self.session.commit()
        return payment

    # Appeals
    def submit_appeal(self, payload: kala_schema.AppealCreate) -> Appeal:
        member = self.session.get(UnitMembers, payload.participant_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
        # must be within 30 minutes of score publication
        now = datetime.utcnow()
        score_time = None
        indiv_score = (
            self.session.execute(
                select(IndividualEventScoreCard)
                .join(IndividualEventParticipation, IndividualEventParticipation.id == IndividualEventScoreCard.event_participation_id)
                .where(IndividualEventParticipation.chest_number == payload.chest_number)
                .order_by(IndividualEventScoreCard.added_on.desc())
            )
            .scalars()
            .first()
        )
        group_score = (
            self.session.execute(
                select(GroupEventScoreCard)
                .where(GroupEventScoreCard.chest_number == payload.chest_number)
                .order_by(GroupEventScoreCard.added_on.desc())
            )
            .scalars()
            .first()
        )
        if indiv_score:
            score_time = indiv_score.added_on
        elif group_score:
            score_time = group_score.added_on

        if not score_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No score found for chest number")
        if now - score_time > timedelta(minutes=30):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appeal window expired")

        appeal = Appeal(
            added_by_id=member.id,
            chest_number=payload.chest_number,
            event_name=payload.event_name,
            statement=payload.statement,
        )
        self.session.add(appeal)
        self.session.add(AppealPayments(appeal=appeal, total_amount_to_pay=APPEAL_FEE))
        self.session.commit()
        return appeal

    # Scores
    def add_individual_score(self, payload: kala_schema.ScoreCardCreate) -> IndividualEventScoreCard:
        participation = self.session.get(IndividualEventParticipation, payload.participation_id)
        if not participation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participation not found")
        if payload.awarded_mark < 0 or payload.total_points < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scores must be non-negative")
        score = IndividualEventScoreCard(
            event_participation_id=participation.id,
            participant_id=participation.participant_id,
            awarded_mark=payload.awarded_mark,
            grade=payload.grade,
            total_points=payload.total_points,
        )
        self.session.add(score)
        self.session.commit()
        return score

    def add_group_score(self, payload: kala_schema.GroupScoreCardCreate) -> GroupEventScoreCard:
        if payload.awarded_mark < 0 or payload.total_points < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scores must be non-negative")
        score = GroupEventScoreCard(
            event_name=payload.event_name,
            chest_number=payload.chest_number,
            awarded_mark=payload.awarded_mark,
            grade=payload.grade,
            total_points=payload.total_points,
        )
        self.session.add(score)
        self.session.commit()
        return score

    # Utility results
    def top_results_individual(self, limit: int = 3) -> List[IndividualEventScoreCard]:
        stmt = select(IndividualEventScoreCard).order_by(
            IndividualEventScoreCard.total_points.desc(), IndividualEventScoreCard.added_on
        ).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def top_results_group(self, limit: int = 3) -> List[GroupEventScoreCard]:
        stmt = select(GroupEventScoreCard).order_by(
            GroupEventScoreCard.total_points.desc(), GroupEventScoreCard.added_on
        ).limit(limit)
        return self.session.execute(stmt).scalars().all()

