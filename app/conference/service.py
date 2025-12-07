from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import CustomUser, UserType
from app.conference.models import Conference, ConferenceDelegate, ConferencePayment
from app.kalamela.models import PaymentStatus
from app.conference import schemas as conf_schema
from app.common.storage import save_upload_file


class ConferenceService:
    def __init__(self, session: Session):
        self.session = session

    def list_conferences(self) -> List[conf_schema.ConferenceRead]:
        rows = self.session.execute(select(Conference).order_by(Conference.added_on.desc())).scalars().all()
        return [conf_schema.ConferenceRead.model_validate(row) for row in rows]

    def create_conference(self, payload: conf_schema.ConferenceCreate) -> conf_schema.ConferenceRead:
        conf = Conference(title=payload.title, details=payload.details)
        self.session.add(conf)
        self.session.commit()
        return conf_schema.ConferenceRead.model_validate(conf)

    def add_delegate(self, payload: conf_schema.DelegateCreate) -> None:
        conference = self.session.get(Conference, payload.conference_id)
        if not conference:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conference not found")
        official = self.session.get(CustomUser, payload.official_user_id)
        if not official or official.user_type not in (UserType.DISTRICT_OFFICIAL, UserType.ADMIN):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid official")
        delegate = ConferenceDelegate(
            conference_id=payload.conference_id, officials_id=payload.official_user_id, members_id=payload.member_id
        )
        self.session.add(delegate)
        self.session.commit()

    def create_payment(self, uploader_id: int, payload: conf_schema.ConferencePaymentCreate, proof_path: str | None) -> conf_schema.ConferencePaymentRead:
        if not self.session.get(Conference, payload.conference_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conference not found")
        payment = ConferencePayment(
            conference_id=payload.conference_id,
            amount_to_pay=payload.amount_to_pay,
            uploaded_by_id=uploader_id,
            proof_path=proof_path,
            status=PaymentStatus.PROOF_UPLOADED if proof_path else PaymentStatus.PENDING,
            payment_reference=payload.payment_reference,
        )
        self.session.add(payment)
        self.session.commit()
        return conf_schema.ConferencePaymentRead.model_validate(payment)

    def attach_proof(self, payment_id: int, file) -> conf_schema.ConferencePaymentRead:
        payment = self.session.get(ConferencePayment, payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        _, dest = save_upload_file(file, subdir="conference")
        payment.proof_path = str(dest)
        payment.status = PaymentStatus.PROOF_UPLOADED
        self.session.commit()
        return conf_schema.ConferencePaymentRead.model_validate(payment)

    def set_status(self, payment_id: int, status_value: PaymentStatus) -> conf_schema.ConferencePaymentRead:
        payment = self.session.get(ConferencePayment, payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if status_value not in (PaymentStatus.PAID, PaymentStatus.DECLINED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")
        payment.status = status_value
        self.session.commit()
        return conf_schema.ConferencePaymentRead.model_validate(payment)

