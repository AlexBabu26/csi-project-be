"""add approved_paid_amount to unit_registration_payment

Revision ID: m025
Revises: m024
"""

revision = "m025"
down_revision = "m024"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "unit_registration_payment",
        sa.Column("approved_paid_amount", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("unit_registration_payment", "approved_paid_amount")
