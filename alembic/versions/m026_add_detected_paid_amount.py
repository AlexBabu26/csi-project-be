"""add detected_paid_amount to unit_registration_payment

Revision ID: m026
Revises: m025
"""

revision = "m026"
down_revision = "m025"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "unit_registration_payment",
        sa.Column("detected_paid_amount", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("unit_registration_payment", "detected_paid_amount")
