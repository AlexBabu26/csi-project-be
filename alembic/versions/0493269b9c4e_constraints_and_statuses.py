"""constraints_and_statuses"""

revision = '0493269b9c4e'
down_revision = '6480ae3b3a12'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    op.alter_column(
        "appeal",
        "status",
        existing_type=sa.VARCHAR(length=64),
        type_=sa.Enum("PENDING", "APPROVED", "REJECTED", name="appealstatus"),
        existing_nullable=False,
    )
    op.alter_column(
        "conference_payment",
        "status",
        existing_type=sa.VARCHAR(length=64),
        type_=sa.Enum("PENDING", "PROOF_UPLOADED", "PAID", "DECLINED", name="paymentstatus"),
        existing_nullable=False,
    )
    op.create_unique_constraint('uq_group_event_chest_number', 'group_event_participation', ['group_event_id', 'chest_number'])
    op.create_unique_constraint('uq_group_event_per_participant', 'group_event_participation', ['group_event_id', 'participant_id'])
    op.create_unique_constraint('uq_ind_event_chest_number', 'individual_event_participation', ['individual_event_id', 'chest_number'])
    op.alter_column(
        "kalamela_payments",
        "payment_status",
        existing_type=sa.VARCHAR(length=64),
        type_=sa.Enum("PENDING", "PROOF_UPLOADED", "PAID", "DECLINED", name="paymentstatus"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "kalamela_payments",
        "payment_status",
        existing_type=sa.Enum("PENDING", "PROOF_UPLOADED", "PAID", "DECLINED", name="paymentstatus"),
        type_=sa.VARCHAR(length=64),
        existing_nullable=False,
    )
    op.drop_constraint('uq_ind_event_chest_number', 'individual_event_participation', type_='unique')
    op.drop_constraint('uq_group_event_per_participant', 'group_event_participation', type_='unique')
    op.drop_constraint('uq_group_event_chest_number', 'group_event_participation', type_='unique')
    op.alter_column(
        "conference_payment",
        "status",
        existing_type=sa.Enum("PENDING", "PROOF_UPLOADED", "PAID", "DECLINED", name="paymentstatus"),
        type_=sa.VARCHAR(length=64),
        existing_nullable=False,
    )
    op.alter_column(
        "appeal",
        "status",
        existing_type=sa.Enum("PENDING", "APPROVED", "REJECTED", name="appealstatus"),
        type_=sa.VARCHAR(length=64),
        existing_nullable=False,
    )

