"""constraints_and_statuses"""

revision = '0493269b9c4e'
down_revision = '6480ae3b3a12'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    # Create enum types first
    appealstatus = sa.Enum("PENDING", "APPROVED", "REJECTED", name="appealstatus")
    paymentstatus = sa.Enum("PENDING", "PROOF_UPLOADED", "PAID", "DECLINED", name="paymentstatus")
    
    appealstatus.create(op.get_bind(), checkfirst=True)
    paymentstatus.create(op.get_bind(), checkfirst=True)
    
    # Now alter columns to use the enum types
    op.alter_column(
        "appeal",
        "status",
        existing_type=sa.VARCHAR(length=64),
        type_=appealstatus,
        existing_nullable=False,
        postgresql_using="status::appealstatus"
    )
    op.alter_column(
        "conference_payment",
        "status",
        existing_type=sa.VARCHAR(length=64),
        type_=paymentstatus,
        existing_nullable=False,
        postgresql_using="status::paymentstatus"
    )
    op.create_unique_constraint('uq_group_event_chest_number', 'group_event_participation', ['group_event_id', 'chest_number'])
    op.create_unique_constraint('uq_group_event_per_participant', 'group_event_participation', ['group_event_id', 'participant_id'])
    op.create_unique_constraint('uq_ind_event_chest_number', 'individual_event_participation', ['individual_event_id', 'chest_number'])
    op.alter_column(
        "kalamela_payments",
        "payment_status",
        existing_type=sa.VARCHAR(length=64),
        type_=paymentstatus,
        existing_nullable=False,
        postgresql_using="payment_status::paymentstatus"
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
    
    # Drop enum types
    sa.Enum(name="paymentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="appealstatus").drop(op.get_bind(), checkfirst=True)

